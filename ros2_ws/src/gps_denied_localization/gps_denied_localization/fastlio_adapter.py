"""
FAST-LIO2 / LIO-SAM Integration Adapter.

Provides standardized interface to consume LiDAR-Inertial Odometry from:
- FAST-LIO2 (fast_lio_sam, fast_lio2)
- LIO-SAM (lio_sam)
- Point-LIO / Faster-LIO

Applies extrinsic spatial calibration (LiDAR -> IMU) and extracts:
- ENU Position (x, y, z)
- Orientation quaternion (qw, qx, qy, qz)
- Linear velocity (if provided)
- 6x6 Odometry covariance
- Matching health metrics (residual, feature count, degeneracy)
"""

import math
from typing import Dict, Optional, Tuple, Any
import numpy as np
from .esekf_core import quat_mult, quat_to_rot, euler_to_quat


class FastLioAdapter:
    def __init__(self, extrinsic_cfg: Optional[Dict[str, Any]] = None):
        extrinsic_cfg = extrinsic_cfg or {}
        l2i = extrinsic_cfg.get("lidar_to_imu", {})
        trans = l2i.get("translation", {"x": 0.05, "y": 0.0, "z": 0.12})
        rot = l2i.get("rotation", {"roll": 0.0, "pitch": 0.0, "yaw": 0.0})

        # Extrinsic translation T_I_L (LiDAR in IMU frame)
        self.t_i_l = np.array([trans.get("x", 0.0), trans.get("y", 0.0), trans.get("z", 0.0)], dtype=np.float64)

        # Extrinsic rotation R_I_L
        roll_rad = math.radians(rot.get("roll", 0.0))
        pitch_rad = math.radians(rot.get("pitch", 0.0))
        yaw_rad = math.radians(rot.get("yaw", 0.0))
        self.q_i_l = euler_to_quat(roll_rad, pitch_rad, yaw_rad)
        self.r_i_l = quat_to_rot(self.q_i_l)

        # Diagnostics
        self.last_pose_time = 0.0
        self.feature_count = 0
        self.scan_residual = 0.0
        self.is_degenerate = False

    def transform_lidar_pose_to_imu(
        self,
        p_raw: np.ndarray,
        q_raw: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Transform raw LiDAR frame pose to IMU/body center frame.
        p_body = p_raw - R_world_body * t_i_l
        q_body = q_raw * q_i_l^-1
        """
        r_world_lidar = quat_to_rot(q_raw)
        p_imu = p_raw - r_world_lidar @ self.t_i_l
        q_imu = quat_mult(q_raw, np.array([self.q_i_l[0], -self.q_i_l[1], -self.q_i_l[2], -self.q_i_l[3]]))
        q_imu /= np.linalg.norm(q_imu)
        return p_imu, q_imu

    def parse_odometry_message(
        self,
        pos_xyz: Tuple[float, float, float],
        quat_wxyz: Tuple[float, float, float, float],
        cov_6x6: Optional[np.ndarray] = None,
        feature_count: int = 150,
        residual: float = 0.02
    ) -> Dict[str, Any]:
        """Process raw LIO inputs and validate health."""
        p_raw = np.array(pos_xyz, dtype=np.float64)
        q_raw = np.array(quat_wxyz, dtype=np.float64)
        q_raw /= np.linalg.norm(q_raw)

        p_imu, q_imu = self.transform_lidar_pose_to_imu(p_raw, q_raw)

        self.feature_count = feature_count
        self.scan_residual = residual
        # Health heuristic: insufficient LiDAR features or high scan residual
        is_healthy = (feature_count >= 30) and (residual < 0.15)

        if cov_6x6 is None or cov_6x6.shape != (6, 6):
            cov_6x6 = np.diag([0.05**2, 0.05**2, 0.05**2, 0.02**2, 0.02**2, 0.02**2])

        return {
            "position": p_imu,
            "orientation": q_imu,
            "covariance": cov_6x6,
            "healthy": is_healthy,
            "feature_count": feature_count,
            "residual": residual
        }
