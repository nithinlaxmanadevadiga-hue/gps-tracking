"""
Synthetic Sensor Stream and ESEKF Simulator Engine.

Generates realistic noisy IMU, LiDAR odometry, and Velocity sensor measurements
from ground truth, runs the 15-state ESEKF filter, geodetic conversion, and streams
telemetry to the ground station.
"""

import math
import time
import asyncio
import threading
from typing import Dict, Any, Optional
import numpy as np
import sys
import os

_curr = os.path.dirname(os.path.abspath(__file__))
for candidate in [
    os.path.abspath(os.path.join(_curr, "..", "ros2_ws", "src", "gps_denied_localization")),
    os.path.abspath(os.path.join(_curr, "ros2_ws", "src", "gps_denied_localization")),
    "/app/ros2_ws/src/gps_denied_localization",
    "ros2_ws/src/gps_denied_localization"
]:
    if os.path.exists(candidate) and candidate not in sys.path:
        sys.path.insert(0, candidate)

from gps_denied_localization.esekf_core import ESEKF15, ESEKFConfig, quat_to_rot, quat_to_euler
from gps_denied_localization.geodetic_enu import enu_to_geodetic, compute_distances, ReferencePoint
from gps_denied_localization.health_monitor import HealthMonitor
from gps_denied_localization.telemetry_publisher import TelemetryPublisher
from trajectory_generator import TrajectoryGenerator



class SimulatorEngine:
    def __init__(
        self,
        device_id: str = "unit_001",
        ref_lat: float = 12.97160000,
        ref_lon: float = 77.59460000,
        ref_alt: float = 900.0,
        ref_heading: float = 0.0,
        backend_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        on_telemetry: Optional[Any] = None
    ):
        self.device_id = device_id
        self.ref_point = ReferencePoint(
            latitude=ref_lat,
            longitude=ref_lon,
            altitude=ref_alt,
            heading=ref_heading
        )

        port = os.getenv("PORT", "8000")
        resolved_backend_url = backend_url or f"http://127.0.0.1:{port}/api/telemetry"
        resolved_auth_token = auth_token or os.getenv("DEFAULT_DEVICE_TOKEN", "dev-device-token-secret")
        self.on_telemetry = on_telemetry

        self.trajectory_gen = TrajectoryGenerator(pattern="figure8", speed_multiplier=1.0)
        self.esekf = ESEKF15(ESEKFConfig())
        self.health = HealthMonitor()
        self.telemetry = TelemetryPublisher(
            device_id=device_id,
            auth_token=resolved_auth_token,
            server_url=resolved_backend_url
        )

        # Simulation runtime controls
        self.is_running = False
        self.is_paused = False
        self.speed_multiplier = 1.0
        self.pattern = "figure8"

        # Fault injection toggles
        self.fault_lidar_degraded = False
        self.fault_comms_loss = False
        self.gps_unavailable = True  # Always True per spec

        # Loop thread
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Reset filter
        self.reset()

    def reset(self) -> None:
        self.trajectory_gen.reset()
        self.trajectory_gen.pattern = self.pattern
        self.trajectory_gen.speed_multiplier = self.speed_multiplier
        self.esekf = ESEKF15(ESEKFConfig())
        self.esekf.set_initial_state(
            p0=np.array([0.0, 0.0, 0.0]),
            heading_deg=self.ref_point.heading
        )
        self.health = HealthMonitor()

    def update_reference(self, lat: float, lon: float, alt: float, heading: float = 0.0) -> None:
        self.ref_point = ReferencePoint(
            latitude=lat,
            longitude=lon,
            altitude=alt,
            heading=heading
        )
        self.reset()

    def set_controls(
        self,
        running: Optional[bool] = None,
        paused: Optional[bool] = None,
        speed: Optional[float] = None,
        pattern: Optional[str] = None,
        lidar_degraded: Optional[bool] = None,
        comms_loss: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Update simulation runtime controls."""
        if running is not None:
            if running and not self.is_running:
                self.start()
            elif not running and self.is_running:
                self.stop()

        if paused is not None:
            self.is_paused = paused

        if speed is not None:
            self.speed_multiplier = max(0.1, min(10.0, speed))
            self.trajectory_gen.speed_multiplier = self.speed_multiplier

        if pattern is not None and pattern in ["figure8", "warehouse", "zigzag", "tunnel"]:
            self.pattern = pattern
            self.trajectory_gen.pattern = pattern
            self.reset()

        if lidar_degraded is not None:
            self.fault_lidar_degraded = lidar_degraded

        if comms_loss is not None:
            self.fault_comms_loss = comms_loss

        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "speed_multiplier": self.speed_multiplier,
            "pattern": self.pattern,
            "fault_lidar_degraded": self.fault_lidar_degraded,
            "fault_comms_loss": self.fault_comms_loss,
            "gps_unavailable": self.gps_unavailable,
            "reference": {
                "latitude": self.ref_point.latitude,
                "longitude": self.ref_point.longitude,
                "altitude": self.ref_point.altitude,
                "heading": self.ref_point.heading
            }
        }

    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self.is_paused = False
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.is_running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _run_loop(self) -> None:
        """Main simulation loop: IMU at 50Hz, LiDAR/Vel/Telemetry at 10Hz."""
        dt_imu = 0.02 # 50 Hz
        lio_interval = 5 # Every 5 IMU steps = 10 Hz
        step_count = 0

        # True sensor noise levels
        accel_noise_std = 0.04
        gyro_noise_std = 0.003
        lio_pos_noise_std = 0.03
        lio_rot_noise_std = 0.01
        vel_noise_std = 0.03

        while not self._stop_event.is_set():
            t_start = time.time()

            if not self.is_paused:
                # 1. Generate ground truth state
                gt = self.trajectory_gen.step(dt_imu)
                p_gt = gt["position"]
                v_gt = gt["velocity"]
                a_gt = gt["acceleration"]
                q_gt = gt["quaternion"]
                r_gt = quat_to_rot(q_gt)

                # 2. Synthesize IMU specific force and angular rate
                # a_body = R^T * (a_enu - g_enu) + noise
                g_enu = np.array([0.0, 0.0, -9.80665], dtype=np.float64)
                a_body_true = r_gt.T @ (a_gt - g_enu)
                a_meas = a_body_true + np.random.normal(0, accel_noise_std, 3)

                # Compute approximate angular velocity from Euler changes
                w_meas = np.random.normal(0, gyro_noise_std, 3)
                # If yaw rate is present:
                _, _, yaw = gt["euler"]
                w_meas[2] += (v_gt[0]*a_gt[1] - v_gt[1]*a_gt[0]) / max(0.1, np.linalg.norm(v_gt)**2)

                now_sim = time.time()
                self.health.record_imu(now_sim)
                self.esekf.predict_imu(a_meas, w_meas, dt_imu)
                self.health.record_ekf()

                # 3. Decimated updates: LiDAR LIO & Velocity constraint at 10Hz
                step_count += 1
                if step_count >= lio_interval:
                    step_count = 0

                    # Simulate LiDAR degradation if toggled
                    if self.fault_lidar_degraded:
                        noise_scale = 10.0
                        feature_count = 15 # low features
                        residual = 0.18    # high residual
                    else:
                        noise_scale = 1.0
                        feature_count = 180
                        residual = 0.015

                    p_lio = p_gt + np.random.normal(0, lio_pos_noise_std * noise_scale, 3)
                    q_lio = q_gt.copy() # Small orientation noise
                    rot_noise = np.random.normal(0, lio_rot_noise_std * noise_scale, 3)
                    # Small perturbation
                    dq = np.array([1.0, 0.5 * rot_noise[0], 0.5 * rot_noise[1], 0.5 * rot_noise[2]])
                    dq /= np.linalg.norm(dq)
                    from gps_denied_localization.esekf_core import quat_mult
                    q_lio = quat_mult(dq, q_lio)
                    q_lio /= np.linalg.norm(q_lio)

                    self.health.record_lidar(now_sim)
                    self.health.record_lio(now_sim)
                    self.esekf.update_lio(p_lio, q_lio)

                    # Velocity sensor update
                    v_meas = r_gt.T @ v_gt + np.random.normal(0, vel_noise_std, 3)
                    self.health.record_velocity(now_sim)
                    self.esekf.update_velocity(v_meas, frame="body")

                    # 4. Dispatch Telemetry
                    if not self.fault_comms_loss:
                        self._dispatch_sim_telemetry(now_sim)

            # Accurate rate control
            elapsed = time.time() - t_start
            sleep_time = max(0.001, dt_imu - elapsed)
            time.sleep(sleep_time)

    def _dispatch_sim_telemetry(self, timestamp: float) -> Optional[Dict[str, Any]]:
        east, north, up = self.esekf.p
        v_e, v_n, v_u = self.esekf.v
        roll, pitch, yaw = self.esekf.get_euler_angles()
        speed = self.esekf.get_speed()
        heading = self.esekf.get_heading_deg()
        horiz_dist, dist_3d = compute_distances(east, north, up)
        acc = self.esekf.get_position_accuracy()

        # Rigorous Geodetic WGS-84
        cur_lat, cur_lon, cur_alt = enu_to_geodetic(
            east, north, up,
            self.ref_point.latitude,
            self.ref_point.longitude,
            self.ref_point.altitude
        )

        health_summary = self.health.get_status_summary(
            self.esekf.quality.value,
            self.esekf.quality_reason
        )

        payload = self.telemetry.build_telemetry_message(
            device_id=self.device_id,
            timestamp=timestamp,
            ref_lat=self.ref_point.latitude,
            ref_lon=self.ref_point.longitude,
            ref_alt=self.ref_point.altitude,
            east=east,
            north=north,
            up=up,
            cur_lat=cur_lat,
            cur_lon=cur_lon,
            cur_alt=cur_alt,
            vel_e=v_e,
            vel_n=v_n,
            vel_u=v_u,
            roll=roll,
            pitch=pitch,
            yaw=yaw,
            speed=speed,
            heading=heading,
            horiz_dist=horiz_dist,
            dist_3d=dist_3d,
            accuracy=acc,
            quality=health_summary["overall_quality"],
            reason=health_summary["overall_reason"],
            health_info=health_summary,
            is_simulation=True
        )

        self.health.record_telemetry()
        self.telemetry.publish_http(payload)
        self.telemetry.publish_mqtt(payload)
        if self.on_telemetry:
            try:
                self.on_telemetry(payload)
            except Exception:
                pass
        return payload
