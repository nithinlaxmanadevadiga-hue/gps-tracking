"""
Synthetic Trajectory Generator for GPS-Denied Localization Simulation.

Generates ground-truth 3D trajectories (ENU position, velocity, acceleration, orientation):
1. Figure-8 Patrol (Lissajous curve with smooth yaw changes)
2. Warehouse Perimeter (Rectangular circuit with 90-degree cornering)
3. Search & Rescue Zig-Zag (Lawnmower pattern across an area)
4. Subterranean Tunnel (Deep corridor with elevation slope and turns)
"""

import math
from typing import Tuple, Dict, Any
import numpy as np
import sys
import os

# Add ros2_ws directory to path to import geodetic_enu & esekf_core
_curr = os.path.dirname(os.path.abspath(__file__))
for candidate in [
    os.path.abspath(os.path.join(_curr, "..", "ros2_ws", "src", "gps_denied_localization")),
    os.path.abspath(os.path.join(_curr, "ros2_ws", "src", "gps_denied_localization")),
    "/app/ros2_ws/src/gps_denied_localization",
    "ros2_ws/src/gps_denied_localization"
]:
    if os.path.exists(candidate) and candidate not in sys.path:
        sys.path.insert(0, candidate)

from gps_denied_localization.esekf_core import euler_to_quat, quat_to_rot



class TrajectoryGenerator:
    def __init__(self, pattern: str = "figure8", speed_multiplier: float = 1.0):
        self.pattern = pattern
        self.speed_multiplier = speed_multiplier
        self.t = 0.0

    def step(self, dt: float) -> Dict[str, Any]:
        """
        Advance simulation time by dt (scaled by speed_multiplier)
        and return ground-truth state:
          position: (east, north, up)
          velocity: (ve, vn, vu)
          acceleration: (ae, an, au)
          orientation: quaternion [qw, qx, qy, qz]
          euler: (roll, pitch, yaw) in radians
        """
        effective_dt = dt * self.speed_multiplier
        self.t += effective_dt
        t = self.t

        if self.pattern == "warehouse":
            p, v, a, roll, pitch, yaw = self._warehouse_trajectory(t)
        elif self.pattern == "zigzag":
            p, v, a, roll, pitch, yaw = self._zigzag_trajectory(t)
        elif self.pattern == "tunnel":
            p, v, a, roll, pitch, yaw = self._tunnel_trajectory(t)
        else: # "figure8"
            p, v, a, roll, pitch, yaw = self._figure8_trajectory(t)

        q = euler_to_quat(roll, pitch, yaw)
        return {
            "time": t,
            "position": p,
            "velocity": v,
            "acceleration": a,
            "quaternion": q,
            "euler": (roll, pitch, yaw)
        }

    def _figure8_trajectory(self, t: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float, float, float]:
        # Scale: ~40m East-West, ~20m North-South, loop period ~40s
        omega = 2.0 * math.pi / 40.0
        A = 25.0
        B = 15.0

        east = A * math.sin(omega * t)
        north = B * math.sin(2.0 * omega * t)
        up = 1.5 * math.sin(0.5 * omega * t)

        ve = A * omega * math.cos(omega * t)
        vn = 2.0 * B * omega * math.cos(2.0 * omega * t)
        vu = 0.75 * omega * math.cos(0.5 * omega * t)

        ae = -A * omega * omega * math.sin(omega * t)
        an = -4.0 * B * omega * omega * math.sin(2.0 * omega * t)
        au = -0.375 * omega * omega * math.sin(0.5 * omega * t)

        yaw = math.atan2(vn, ve)
        pitch = math.atan2(vu, math.hypot(ve, vn))
        roll = 0.05 * math.sin(omega * t) # slight banking

        return (
            np.array([east, north, up], dtype=np.float64),
            np.array([ve, vn, vu], dtype=np.float64),
            np.array([ae, an, au], dtype=np.float64),
            roll, pitch, yaw
        )

    def _warehouse_trajectory(self, t: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float, float, float]:
        # 40m x 25m perimeter loop, perimeter = 130m, speed ~ 1.5 m/s, period ~ 86s
        speed = 1.5
        w = 40.0
        h = 25.0
        total_p = 2.0 * (w + h)
        loop_time = total_p / speed
        s = (t * speed) % total_p

        roll, pitch = 0.0, 0.0
        up = 0.2 * math.sin(0.1 * t)
        vu = 0.02 * math.cos(0.1 * t)

        if s < w:
            # Bottom edge: East 0 -> w, North = 0
            east = s
            north = 0.0
            ve, vn = speed, 0.0
            yaw = 0.0 # Facing East
        elif s < w + h:
            # Right edge: East = w, North 0 -> h
            east = w
            north = s - w
            ve, vn = 0.0, speed
            yaw = math.pi / 2.0 # Facing North
        elif s < 2 * w + h:
            # Top edge: East w -> 0, North = h
            east = w - (s - (w + h))
            north = h
            ve, vn = -speed, 0.0
            yaw = math.pi # Facing West
        else:
            # Left edge: East = 0, North h -> 0
            east = 0.0
            north = h - (s - (2 * w + h))
            ve, vn = 0.0, -speed
            yaw = -math.pi / 2.0 # Facing South

        return (
            np.array([east, north, up], dtype=np.float64),
            np.array([ve, vn, vu], dtype=np.float64),
            np.array([0.0, 0.0, 0.0], dtype=np.float64),
            roll, pitch, yaw
        )

    def _zigzag_trajectory(self, t: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float, float, float]:
        # Lawnmower pattern
        speed = 1.2
        cycle = (t * 0.1) % 4.0
        lane = math.floor(t / 15.0) % 5
        east = 20.0 * math.sin(0.4 * t)
        north = lane * 8.0 + 2.0 * (t % 15.0) / 15.0 * 8.0
        up = 0.5 * math.sin(0.2 * t)

        ve = 8.0 * math.cos(0.4 * t)
        vn = 0.5
        vu = 0.1 * math.cos(0.2 * t)
        yaw = math.atan2(vn, ve)
        return (
            np.array([east, north, up], dtype=np.float64),
            np.array([ve, vn, vu], dtype=np.float64),
            np.array([0.0, 0.0, 0.0], dtype=np.float64),
            0.0, 0.0, yaw
        )

    def _tunnel_trajectory(self, t: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float, float, float]:
        # Linear descent into underground tunnel
        speed = 1.0
        dist = (t * speed) % 150.0
        # Curve with progressive descent
        east = dist * 0.8 + 5.0 * math.sin(dist * 0.05)
        north = dist * 0.5 + 4.0 * math.cos(dist * 0.05)
        up = -0.15 * dist # 15% downward slope

        ve = 0.8 * speed
        vn = 0.5 * speed
        vu = -0.15 * speed
        yaw = math.atan2(vn, ve)
        pitch = math.atan2(vu, math.hypot(ve, vn))
        return (
            np.array([east, north, up], dtype=np.float64),
            np.array([ve, vn, vu], dtype=np.float64),
            np.array([0.0, 0.0, 0.0], dtype=np.float64),
            0.0, pitch, yaw
        )

    def reset(self) -> None:
        self.t = 0.0
