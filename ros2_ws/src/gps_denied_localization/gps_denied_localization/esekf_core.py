"""
15-Error-State Extended Kalman Filter (ESEKF) Core.

Nominal state (16D):
  x = [p, v, q, ba, bg]
  p:  ENU position [x, y, z] (3D)
  v:  ENU velocity [vx, vy, vz] (3D)
  q:  quaternion [qw, qx, qy, qz] (attitude body -> ENU) (4D)
  ba: accelerometer bias [bax, bay, baz] (3D)
  bg: gyroscope bias [bgx, bgy, bgz] (3D)

Error state (15D):
  dx = [dp, dv, dtheta, dba, dbg]

Continuous error-state Jacobian:
  Fc = [
    0   I       0            0    0
    0   0   -R[a]x          -R    0
    0   0   -[omega]x        0   -I
    0   0       0            0    0
    0   0       0            0    0
  ]

Discrete transition matrix:
  Phi = I + Fc * dt

Covariance propagation:
  P(k+1) = Phi * P(k) * Phi^T + Q
"""

import math
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import numpy as np


class LocalizationQuality(str, Enum):
    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    LOST = "LOST"


def skew(w: np.ndarray) -> np.ndarray:
    """Skew-symmetric matrix [w]x for 3D vector w."""
    return np.array([
        [0.0, -w[2], w[1]],
        [w[2], 0.0, -w[0]],
        [-w[1], w[0], 0.0]
    ], dtype=np.float64)


def quat_to_rot(q: np.ndarray) -> np.ndarray:
    """
    Convert unit quaternion q = [qw, qx, qy, qz] to 3x3 rotation matrix R (body to world/ENU).
    """
    qw, qx, qy, qz = q
    # Normalize
    norm = math.sqrt(qw*qw + qx*qx + qy*qy + qz*qz)
    if norm < 1e-12:
        return np.eye(3, dtype=np.float64)
    qw /= norm
    qx /= norm
    qy /= norm
    qz /= norm

    return np.array([
        [1.0 - 2.0*(qy*qy + qz*qz), 2.0*(qx*qy - qz*qw),       2.0*(qx*qz + qy*qw)],
        [2.0*(qx*qy + qz*qw),       1.0 - 2.0*(qx*qx + qz*qz), 2.0*(qy*qz - qx*qw)],
        [2.0*(qx*qz - qy*qw),       2.0*(qy*qz + qx*qw),       1.0 - 2.0*(qx*qx + qy*qy)]
    ], dtype=np.float64)


def quat_mult(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    """Hamilton product of two quaternions [qw, qx, qy, qz]."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2
    ], dtype=np.float64)


def quat_inv(q: np.ndarray) -> np.ndarray:
    """Inverse of unit quaternion [qw, qx, qy, qz]."""
    return np.array([q[0], -q[1], -q[2], -q[3]], dtype=np.float64)


def quat_to_euler(q: np.ndarray) -> Tuple[float, float, float]:
    """
    Convert quaternion to Euler angles: (roll, pitch, yaw) in radians.
    Yaw is 0 pointing East, pi/2 pointing North in ENU or standard navigation.
    """
    qw, qx, qy, qz = q
    norm = math.sqrt(qw*qw + qx*qx + qy*qy + qz*qz)
    if norm > 1e-12:
        qw /= norm
        qx /= norm
        qy /= norm
        qz /= norm

    # Roll (x-axis rotation)
    sinr_cosp = 2.0 * (qw * qx + qy * qz)
    cosr_cosp = 1.0 - 2.0 * (qx * qx + qy * qy)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    # Pitch (y-axis rotation)
    sinp = 2.0 * (qw * qy - qz * qx)
    if abs(sinp) >= 1.0:
        pitch = math.copysign(math.pi / 2.0, sinp)
    else:
        pitch = math.asin(sinp)

    # Yaw (z-axis rotation)
    siny_cosp = 2.0 * (qw * qz + qx * qy)
    cosy_cosp = 1.0 - 2.0 * (qy * qy + qz * qz)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return roll, pitch, yaw


def euler_to_quat(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """Convert Euler angles (roll, pitch, yaw) in radians to quaternion [qw, qx, qy, qz]."""
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)

    return np.array([
        cr * cp * cy + sr * sp * sy,
        sr * cp * cy - cr * sp * sy,
        cr * sp * cy + sr * cp * sy,
        cr * cp * sy - sr * sp * cy
    ], dtype=np.float64)


class ESEKFConfig:
    def __init__(
        self,
        accel_noise: float = 0.05,       # m/s^2 / sqrt(Hz)
        gyro_noise: float = 0.005,       # rad/s / sqrt(Hz)
        accel_bias_noise: float = 0.001, # m/s^3 / sqrt(Hz)
        gyro_bias_noise: float = 0.0001, # rad/s^2 / sqrt(Hz)
        lio_pos_noise: float = 0.05,     # m
        lio_rot_noise: float = 0.02,     # rad
        vel_sensor_noise: float = 0.05,  # m/s
        gravity: float = 9.80665,        # m/s^2
        max_jump_threshold: float = 5.0, # meters jump detection
        max_pos_cov_trace: float = 25.0, # covariance divergence limit
        chi2_threshold_lio: float = 22.46 # 6-DOF 99.9% chi-squared threshold
    ):
        self.accel_noise = accel_noise
        self.gyro_noise = gyro_noise
        self.accel_bias_noise = accel_bias_noise
        self.gyro_bias_noise = gyro_bias_noise
        self.lio_pos_noise = lio_pos_noise
        self.lio_rot_noise = lio_rot_noise
        self.vel_sensor_noise = vel_sensor_noise
        self.gravity = gravity
        self.max_jump_threshold = max_jump_threshold
        self.max_pos_cov_trace = max_pos_cov_trace
        self.chi2_threshold_lio = chi2_threshold_lio


class ESEKF15:
    """
    15-error-state ESEKF with 16-state nominal state.
    """

    def __init__(self, config: Optional[ESEKFConfig] = None):
        self.config = config or ESEKFConfig()

        # Nominal State (16D)
        self.p = np.zeros(3, dtype=np.float64)      # ENU Position (m)
        self.v = np.zeros(3, dtype=np.float64)      # ENU Velocity (m/s)
        self.q = np.array([1.0, 0.0, 0.0, 0.0])     # Quaternion [qw, qx, qy, qz]
        self.ba = np.zeros(3, dtype=np.float64)     # Accel bias (m/s^2)
        self.bg = np.zeros(3, dtype=np.float64)     # Gyro bias (rad/s)

        # Error State Covariance P (15x15)
        # Order: [dp(3), dv(3), dtheta(3), dba(3), dbg(3)]
        self.P = np.eye(15, dtype=np.float64) * 0.1
        self.P[0:3, 0:3] *= 0.1     # pos
        self.P[3:6, 3:6] *= 0.1     # vel
        self.P[6:9, 6:9] *= 0.01    # rot
        self.P[9:12, 9:12] *= 0.01  # ba
        self.P[12:15, 12:15] *= 0.001 # bg

        # Continuous process noise covariance Qc (12x12)
        self.Qc = np.diag([
            self.config.accel_noise**2, self.config.accel_noise**2, self.config.accel_noise**2,
            self.config.gyro_noise**2, self.config.gyro_noise**2, self.config.gyro_noise**2,
            self.config.accel_bias_noise**2, self.config.accel_bias_noise**2, self.config.accel_bias_noise**2,
            self.config.gyro_bias_noise**2, self.config.gyro_bias_noise**2, self.config.gyro_bias_noise**2,
        ])

        # Tracking metrics & diagnostics
        self.last_imu_time: Optional[float] = None
        self.last_lio_time: Optional[float] = None
        self.last_vel_time: Optional[float] = None
        self.quality = LocalizationQuality.GOOD
        self.quality_reason = "System nominal"
        self.lio_matching_healthy = True
        self.consecutive_rejections = 0
        self.total_lio_updates = 0
        self.total_vel_updates = 0

    def set_initial_state(
        self,
        p0: np.ndarray,
        v0: Optional[np.ndarray] = None,
        q0: Optional[np.ndarray] = None,
        heading_deg: Optional[float] = None
    ) -> None:
        """Initialize filter position, velocity, and orientation."""
        self.p = np.array(p0, dtype=np.float64).flatten()
        if v0 is not None:
            self.v = np.array(v0, dtype=np.float64).flatten()
        else:
            self.v = np.zeros(3, dtype=np.float64)

        if q0 is not None:
            self.q = np.array(q0, dtype=np.float64).flatten()
            self.q /= np.linalg.norm(self.q)
        elif heading_deg is not None:
            # Heading: 0 = North, 90 = East -> yaw = 90 - heading
            yaw = math.radians(90.0 - heading_deg)
            self.q = euler_to_quat(0.0, 0.0, yaw)
        else:
            self.q = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)

        self.ba = np.zeros(3, dtype=np.float64)
        self.bg = np.zeros(3, dtype=np.float64)
        self.P = np.eye(15, dtype=np.float64) * 0.05
        self.quality = LocalizationQuality.GOOD
        self.quality_reason = "Initialized"

    def predict_imu(self, a_meas: np.ndarray, w_meas: np.ndarray, dt: float) -> None:
        """
        ESEKF propagation step using IMU measurement:
          a_meas: specific force in body frame (m/s^2)
          w_meas: angular rate in body frame (rad/s)
          dt: time increment (s)
        """
        if dt <= 1e-6 or dt > 1.0:
            return  # Reject anomalous time deltas

        # 1. Unbiased inertial readings
        a_unbiased = a_meas - self.ba
        w_unbiased = w_meas - self.bg

        # Check IMU saturation / sanity
        if np.linalg.norm(a_meas) > 150.0 or np.linalg.norm(w_meas) > 35.0:
            self.quality = LocalizationQuality.DEGRADED
            self.quality_reason = "IMU saturation detected"

        # 2. Rotation matrix R (body -> ENU)
        R = quat_to_rot(self.q)

        # 3. Propagate nominal velocity and position
        g_enu = np.array([0.0, 0.0, -self.config.gravity], dtype=np.float64)
        a_enu = R @ a_unbiased + g_enu

        self.p += self.v * dt + 0.5 * a_enu * (dt * dt)
        self.v += a_enu * dt

        # 4. Propagate attitude quaternion
        angle = np.linalg.norm(w_unbiased) * dt
        if angle > 1e-12:
            axis = w_unbiased / np.linalg.norm(w_unbiased)
            half_angle = 0.5 * angle
            dq = np.array([
                math.cos(half_angle),
                axis[0] * math.sin(half_angle),
                axis[1] * math.sin(half_angle),
                axis[2] * math.sin(half_angle)
            ], dtype=np.float64)
            self.q = quat_mult(self.q, dq)
            self.q /= np.linalg.norm(self.q)

        # 5. Continuous error-state Jacobian Fc (15x15)
        # Fc = [
        #   0   I       0            0    0
        #   0   0   -R[a]x          -R    0
        #   0   0   -[omega]x        0   -I
        #   0   0       0            0    0
        #   0   0       0            0    0
        # ]
        Fc = np.zeros((15, 15), dtype=np.float64)
        Fc[0:3, 3:6] = np.eye(3)                                 # d(p_dot) / dv = I
        Fc[3:6, 6:9] = -R @ skew(a_unbiased)                     # d(v_dot) / dtheta = -R [a]x
        Fc[3:6, 9:12] = -R                                       # d(v_dot) / dba = -R
        Fc[6:9, 6:9] = -skew(w_unbiased)                         # d(theta_dot) / dtheta = -[w]x
        Fc[6:9, 12:15] = -np.eye(3)                              # d(theta_dot) / dbg = -I

        # 6. Discrete state transition matrix Phi = I + Fc * dt
        Phi = np.eye(15, dtype=np.float64) + Fc * dt

        # 7. Discrete noise mapping matrix G
        # noise vector n = [na, nw, nba, nbg]^T (12D)
        G = np.zeros((15, 12), dtype=np.float64)
        G[3:6, 0:3] = -R
        G[6:9, 3:6] = -np.eye(3)
        G[9:12, 6:9] = np.eye(3)
        G[12:15, 9:12] = np.eye(3)

        Qd = G @ self.Qc @ G.T * dt

        # 8. Covariance propagation P(k+1) = Phi * P(k) * Phi^T + Qd
        self.P = Phi @ self.P @ Phi.T + Qd
        # Symmetrize P
        self.P = 0.5 * (self.P + self.P.T)

        self._check_health()

    def update_lio(
        self,
        p_lio: np.ndarray,
        q_lio: np.ndarray,
        cov_lio: Optional[np.ndarray] = None
    ) -> bool:
        """
        Measurement update from LiDAR-Inertial Odometry (FAST-LIO2 / LIO-SAM):
          p_lio: ENU position (3,)
          q_lio: unit quaternion [qw, qx, qy, qz]
          cov_lio: optional 6x6 covariance (pos 3x3, rot 3x3)
        """
        # 1. Sudden jump detection
        pos_diff = np.linalg.norm(p_lio - self.p)
        if pos_diff > self.config.max_jump_threshold:
            self.consecutive_rejections += 1
            self.quality = LocalizationQuality.DEGRADED
            self.quality_reason = f"LIO pose jump rejected ({pos_diff:.2f} m > {self.config.max_jump_threshold} m)"
            if self.consecutive_rejections > 5:
                self.quality = LocalizationQuality.LOST
                self.quality_reason = "Multiple consecutive LIO jumps detected"
            return False

        # 2. Measurement residual
        # Position error
        r_p = p_lio - self.p

        # Attitude error: delta_theta = 2 * vec(q_lio * q_nom^-1)
        q_err = quat_mult(q_lio, quat_inv(self.q))
        if q_err[0] < 0.0:  # Enforce shortest path
            q_err = -q_err
        r_theta = 2.0 * q_err[1:4]

        # 6-DOF residual z = [r_p, r_theta]
        z = np.hstack([r_p, r_theta])

        # 3. Measurement matrix H (6x15)
        # z = H * dx + v
        H = np.zeros((6, 15), dtype=np.float64)
        H[0:3, 0:3] = np.eye(3)  # dp
        H[3:6, 6:9] = np.eye(3)  # dtheta

        # Measurement noise covariance R (6x6)
        if cov_lio is not None and cov_lio.shape == (6, 6):
            R_mat = cov_lio.copy()
        else:
            R_mat = np.diag([
                self.config.lio_pos_noise**2, self.config.lio_pos_noise**2, self.config.lio_pos_noise**2,
                self.config.lio_rot_noise**2, self.config.lio_rot_noise**2, self.config.lio_rot_noise**2
            ])

        # 4. Innovation covariance S = H P H^T + R
        S = H @ self.P @ H.T + R_mat
        S = 0.5 * (S + S.T)

        # 5. Chi-squared gating (outlier rejection after initial acquisition)
        try:
            S_inv = np.linalg.inv(S)
            nis = float(z.T @ S_inv @ z)
            if self.total_lio_updates > 0 and nis > self.config.chi2_threshold_lio:
                self.consecutive_rejections += 1
                self.quality = LocalizationQuality.DEGRADED
                self.quality_reason = f"LIO NIS gating failure (NIS={nis:.2f})"
                if self.consecutive_rejections > 10:
                    self.quality = LocalizationQuality.LOST
                    self.quality_reason = "Excessive LiDAR residual / match failure"
                return False
        except np.linalg.LinAlgError:
            return False

        # 6. Kalman gain K = P H^T S^-1
        K = self.P @ H.T @ S_inv

        # 7. Error state dx = K * z (15D)
        dx = K @ z

        # 8. Error injection into nominal state
        self.p += dx[0:3]
        self.v += dx[3:6]

        # Small-angle attitude correction
        dtheta = dx[6:9]
        angle = np.linalg.norm(dtheta)
        if angle > 1e-12:
            axis = dtheta / angle
            half_angle = 0.5 * angle
            dq = np.array([
                math.cos(half_angle),
                axis[0] * math.sin(half_angle),
                axis[1] * math.sin(half_angle),
                axis[2] * math.sin(half_angle)
            ], dtype=np.float64)
            self.q = quat_mult(dq, self.q)
            self.q /= np.linalg.norm(self.q)

        self.ba += dx[9:12]
        self.bg += dx[12:15]

        # 9. Joseph-form covariance update (guarantees positive semi-definiteness)
        I_KH = np.eye(15, dtype=np.float64) - K @ H
        self.P = I_KH @ self.P @ I_KH.T + K @ R_mat @ K.T
        self.P = 0.5 * (self.P + self.P.T)

        self.consecutive_rejections = 0
        self.total_lio_updates += 1
        self._check_health()
        return True

    def update_velocity(self, v_meas: np.ndarray, frame: str = "body") -> bool:
        """
        Velocity sensor constraint update:
          v_meas: 3D velocity vector (vx, vy, vz)
          frame: "body" or "enu"
        """
        R = quat_to_rot(self.q)

        if frame == "body":
            # v_body_pred = R^T * v_enu
            v_pred = R.T @ self.v
            r = v_meas - v_pred
            # d(R^T v) / dtheta = R^T [v]x
            H = np.zeros((3, 15), dtype=np.float64)
            H[0:3, 3:6] = R.T
            H[0:3, 6:9] = R.T @ skew(self.v)
        else:
            # ENU frame
            r = v_meas - self.v
            H = np.zeros((3, 15), dtype=np.float64)
            H[0:3, 3:6] = np.eye(3)

        R_mat = np.eye(3, dtype=np.float64) * (self.config.vel_sensor_noise**2)
        S = H @ self.P @ H.T + R_mat
        try:
            S_inv = np.linalg.inv(S)
            K = self.P @ H.T @ S_inv
            dx = K @ r

            self.p += dx[0:3]
            self.v += dx[3:6]

            dtheta = dx[6:9]
            angle = np.linalg.norm(dtheta)
            if angle > 1e-12:
                axis = dtheta / angle
                half_angle = 0.5 * angle
                dq = np.array([
                    math.cos(half_angle),
                    axis[0] * math.sin(half_angle),
                    axis[1] * math.sin(half_angle),
                    axis[2] * math.sin(half_angle)
                ], dtype=np.float64)
                self.q = quat_mult(dq, self.q)
                self.q /= np.linalg.norm(self.q)

            self.ba += dx[9:12]
            self.bg += dx[12:15]

            I_KH = np.eye(15, dtype=np.float64) - K @ H
            self.P = I_KH @ self.P @ I_KH.T + K @ R_mat @ K.T
            self.P = 0.5 * (self.P + self.P.T)

            self.total_vel_updates += 1
            return True
        except np.linalg.LinAlgError:
            return False

    def _check_health(self) -> None:
        """Evaluate filter covariance trace and quality status."""
        pos_cov_trace = float(np.trace(self.P[0:3, 0:3]))
        if pos_cov_trace > self.config.max_pos_cov_trace:
            self.quality = LocalizationQuality.LOST
            self.quality_reason = f"Position covariance divergence (trace={pos_cov_trace:.2f})"
        elif pos_cov_trace > self.config.max_pos_cov_trace * 0.4:
            if self.quality == LocalizationQuality.GOOD:
                self.quality = LocalizationQuality.DEGRADED
                self.quality_reason = f"Position covariance growing (trace={pos_cov_trace:.2f})"
        elif self.consecutive_rejections == 0:
            self.quality = LocalizationQuality.GOOD
            self.quality_reason = "Nominal tracking"

    def get_position_accuracy(self) -> float:
        """Estimated 1-sigma position standard deviation in meters."""
        pos_cov = self.P[0:3, 0:3]
        return float(math.sqrt(max(0.0, np.trace(pos_cov) / 3.0)))

    def get_speed(self) -> float:
        """Current scalar speed in m/s."""
        return float(np.linalg.norm(self.v))

    def get_heading_deg(self) -> float:
        """
        Geographic compass heading in degrees:
        0° = North, 90° = East, 180° = South, 270° = West.
        """
        _, _, yaw = quat_to_euler(self.q)
        # In ENU: yaw 0 is East (+x), yaw 90 is North (+y).
        # Compass heading: 0 North, 90 East
        heading = 90.0 - math.degrees(yaw)
        return float((heading + 360.0) % 360.0)

    def get_euler_angles(self) -> Tuple[float, float, float]:
        """Return (roll, pitch, yaw) in radians."""
        return quat_to_euler(self.q)
