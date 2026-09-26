"""
Sensor and Pipeline Health Monitor.

Tracks real-time update frequencies (Hz), age of telemetry, out-of-order timestamps,
and classifies system health into GOOD, DEGRADED, and LOST states.
"""

import time
from typing import Dict, Any, Optional


class FrequencyTracker:
    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        self.timestamps: list[float] = []

    def tick(self, now: Optional[float] = None) -> None:
        t = now if now is not None else time.time()
        self.timestamps.append(t)
        if len(self.timestamps) > self.window_size:
            self.timestamps.pop(0)

    @property
    def hz(self) -> float:
        if len(self.timestamps) < 2:
            return 0.0
        dt = self.timestamps[-1] - self.timestamps[0]
        if dt <= 1e-6:
            return 0.0
        return float((len(self.timestamps) - 1) / dt)


class HealthMonitor:
    def __init__(
        self,
        imu_timeout: float = 0.5,
        lidar_timeout: float = 1.0,
        lio_timeout: float = 1.0,
        vel_timeout: float = 1.0
    ):
        self.imu_timeout = imu_timeout
        self.lidar_timeout = lidar_timeout
        self.lio_timeout = lio_timeout
        self.vel_timeout = vel_timeout

        # Frequency trackers
        self.imu_fps = FrequencyTracker(window_size=50)
        self.lidar_fps = FrequencyTracker(window_size=20)
        self.lio_fps = FrequencyTracker(window_size=20)
        self.vel_fps = FrequencyTracker(window_size=20)
        self.ekf_fps = FrequencyTracker(window_size=50)
        self.telemetry_fps = FrequencyTracker(window_size=20)

        # Last timestamps (monotonic / system time)
        self.last_imu_time = 0.0
        self.last_lidar_time = 0.0
        self.last_lio_time = 0.0
        self.last_vel_time = 0.0
        self.last_ekf_time = 0.0
        self.last_telemetry_time = 0.0

        # Sequence numbers for out-of-order rejection
        self.last_imu_seq = -1
        self.last_lio_seq = -1

        # Error / warning flags
        self.warnings: list[str] = []
        self.faults: list[str] = []

    def record_imu(self, timestamp: float, seq: int = -1) -> bool:
        """Returns True if message is valid, False if stale/out-of-order."""
        if seq >= 0 and seq <= self.last_imu_seq:
            self.warnings.append(f"Rejected out-of-order IMU seq {seq} <= {self.last_imu_seq}")
            return False
        if self.last_imu_time > 0 and timestamp < self.last_imu_time:
            self.warnings.append("Rejected retrograde IMU timestamp")
            return False

        self.last_imu_time = time.time()
        self.imu_fps.tick(self.last_imu_time)
        if seq >= 0:
            self.last_imu_seq = seq
        return True

    def record_lidar(self, timestamp: float) -> None:
        self.last_lidar_time = time.time()
        self.lidar_fps.tick(self.last_lidar_time)

    def record_lio(self, timestamp: float, seq: int = -1) -> bool:
        if seq >= 0 and seq <= self.last_lio_seq:
            self.warnings.append(f"Rejected out-of-order LIO seq {seq} <= {self.last_lio_seq}")
            return False
        if self.last_lio_time > 0 and timestamp < self.last_lio_time:
            self.warnings.append("Rejected retrograde LIO timestamp")
            return False

        self.last_lio_time = time.time()
        self.lio_fps.tick(self.last_lio_time)
        if seq >= 0:
            self.last_lio_seq = seq
        return True

    def record_velocity(self, timestamp: float) -> None:
        self.last_vel_time = time.time()
        self.vel_fps.tick(self.last_vel_time)

    def record_ekf(self) -> None:
        self.last_ekf_time = time.time()
        self.ekf_fps.tick(self.last_ekf_time)

    def record_telemetry(self) -> None:
        self.last_telemetry_time = time.time()
        self.telemetry_fps.tick(self.last_telemetry_time)

    def get_status_summary(self, ekf_quality: str, ekf_reason: str) -> Dict[str, Any]:
        """Aggregate full health state for dashboard telemetry."""
        now = time.time()

        # Check timeouts
        imu_alive = (now - self.last_imu_time) <= self.imu_timeout if self.last_imu_time > 0 else False
        lidar_alive = (now - self.last_lidar_time) <= self.lidar_timeout if self.last_lidar_time > 0 else False
        lio_alive = (now - self.last_lio_time) <= self.lio_timeout if self.last_lio_time > 0 else False
        vel_alive = (now - self.last_vel_time) <= self.vel_timeout if self.last_vel_time > 0 else False

        imu_status = "ONLINE" if imu_alive else "OFFLINE"
        lidar_status = "ONLINE" if lidar_alive else "OFFLINE"
        velocity_status = "ONLINE" if vel_alive else "OFFLINE"

        if lio_alive:
            lio_status = "TRACKING" if ekf_quality == "GOOD" else "DEGRADED"
        else:
            lio_status = "LOST"

        if not imu_alive or not lio_alive:
            ekf_status = "FAILED" if (not imu_alive and not lio_alive) else "WARNING"
            overall_quality = "LOST" if not imu_alive else "DEGRADED"
            overall_reason = "Sensor communication timeout"
        else:
            ekf_status = "RUNNING" if ekf_quality == "GOOD" else "WARNING"
            overall_quality = ekf_quality
            overall_reason = ekf_reason

        return {
            "overall_quality": overall_quality,
            "overall_reason": overall_reason,
            "subsystems": {
                "lidar": lidar_status,
                "imu": imu_status,
                "velocity": velocity_status,
                "lio": lio_status,
                "ekf": ekf_status,
                "telemetry": "CONNECTED" if (now - self.last_telemetry_time) < 3.0 else "DISCONNECTED",
                "gps": "NOT USED",  # Conforms strictly to section 17 & 20
            },
            "frequencies_hz": {
                "imu_hz": round(self.imu_fps.hz, 1),
                "lidar_hz": round(self.lidar_fps.hz, 1),
                "lio_hz": round(self.lio_fps.hz, 1),
                "ekf_hz": round(self.ekf_fps.hz, 1),
                "telemetry_hz": round(self.telemetry_fps.hz, 1),
            },
            "last_update_age_ms": round((now - self.last_ekf_time) * 1000.0, 1) if self.last_ekf_time > 0 else -1.0
        }
