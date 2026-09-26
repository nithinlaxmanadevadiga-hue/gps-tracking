import math
import pytest
import numpy as np
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ros2_ws", "src", "gps_denied_localization")))
from gps_denied_localization.esekf_core import (
    ESEKF15,
    ESEKFConfig,
    LocalizationQuality,
    skew,
    quat_to_rot,
    euler_to_quat,
    quat_to_euler
)


def test_skew_matrix():
    v = np.array([1.0, 2.0, 3.0])
    s = skew(v)
    assert np.allclose(s, -s.T)
    # Check [v]x * w = v x w
    w = np.array([4.0, 5.0, 6.0])
    cross_expected = np.cross(v, w)
    assert np.allclose(s @ w, cross_expected)


def test_quat_euler_conversions():
    roll_in, pitch_in, yaw_in = 0.1, -0.05, 1.25
    q = euler_to_quat(roll_in, pitch_in, yaw_in)
    roll_out, pitch_out, yaw_out = quat_to_euler(q)

    assert abs(roll_in - roll_out) < 1e-6
    assert abs(pitch_in - pitch_out) < 1e-6
    assert abs(yaw_in - yaw_out) < 1e-6


def test_esekf_imu_prediction_stationary():
    # When stationary, body accelerometer measures upward specific force +9.80665
    ekf = ESEKF15()
    ekf.set_initial_state(p0=np.array([0.0, 0.0, 0.0]))

    a_meas = np.array([0.0, 0.0, 9.80665])
    w_meas = np.array([0.0, 0.0, 0.0])

    dt = 0.02
    for _ in range(50): # 1 second
        ekf.predict_imu(a_meas, w_meas, dt)

    # Position and velocity should remain near zero
    assert np.linalg.norm(ekf.p) < 0.01
    assert np.linalg.norm(ekf.v) < 0.01
    assert ekf.quality == LocalizationQuality.GOOD


def test_esekf_lio_measurement_update():
    ekf = ESEKF15()
    ekf.set_initial_state(p0=np.array([0.0, 0.0, 0.0]))

    # Feed LIO measurement at (1.0, 2.0, 0.5)
    p_lio = np.array([1.0, 2.0, 0.5])
    q_lio = np.array([1.0, 0.0, 0.0, 0.0])

    initial_cov = np.trace(ekf.P[0:3, 0:3])
    success = ekf.update_lio(p_lio, q_lio)
    assert success is True

    # Covariance should reduce after measurement
    final_cov = np.trace(ekf.P[0:3, 0:3])
    assert final_cov < initial_cov

    # Position should shift towards measurement
    assert np.linalg.norm(ekf.p - p_lio) < 0.5


def test_esekf_velocity_constraint():
    ekf = ESEKF15()
    ekf.set_initial_state(p0=np.array([0.0, 0.0, 0.0]))
    ekf.v = np.array([2.0, 0.0, 0.0])

    # Speed sensor reads 0 m/s
    success = ekf.update_velocity(np.array([0.0, 0.0, 0.0]), frame="enu")
    assert success is True
    # Velocity should be reduced
    assert ekf.v[0] < 2.0


def test_esekf_jump_rejection_and_degradation():
    cfg = ESEKFConfig(max_jump_threshold=5.0)
    ekf = ESEKF15(cfg)
    ekf.set_initial_state(p0=np.array([0.0, 0.0, 0.0]))

    # Massive anomalous jump of 25 meters
    p_bad = np.array([25.0, 0.0, 0.0])
    q_lio = np.array([1.0, 0.0, 0.0, 0.0])

    success = ekf.update_lio(p_bad, q_lio)
    assert success is False
    assert ekf.quality in [LocalizationQuality.DEGRADED, LocalizationQuality.LOST]
    # Filter state must not adopt the jumped position
    assert ekf.p[0] < 5.0
