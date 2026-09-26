"""
ROS 2 GPS-Denied Localization Node.

Subscribes to:
  /imu/data      (sensor_msgs/msg/Imu)
  /lidar/points  (sensor_msgs/msg/PointCloud2)
  /velocity      (geometry_msgs/msg/TwistStamped)
  /lio/pose      (nav_msgs/msg/Odometry or geometry_msgs/msg/PoseWithCovarianceStamped)

Publishes:
  /localization/telemetry  (std_msgs/msg/String containing JSON)
  TF: map/enu -> base_link -> imu_link, lidar_link
"""

import math
import time
import json
from typing import Optional, Dict, Any
import numpy as np

from .esekf_core import ESEKF15, ESEKFConfig, quat_to_euler, euler_to_quat
from .geodetic_enu import enu_to_geodetic, compute_distances, ReferencePoint
from .fastlio_adapter import FastLioAdapter
from .health_monitor import HealthMonitor
from .telemetry_publisher import TelemetryPublisher

try:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
    from sensor_msgs.msg import Imu, PointCloud2
    from geometry_msgs.msg import TwistStamped, PoseWithCovarianceStamped, TransformStamped
    from nav_msgs.msg import Odometry
    from std_msgs.msg import String
    from tf2_ros import TransformBroadcaster
    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False
    # Mock base class for non-ROS2 execution
    class Node:  # type: ignore
        def __init__(self, name: str):
            self._name = name
        def get_logger(self):
            class Logger:
                def info(self, msg): print(f"[INFO] {msg}")
                def warn(self, msg): print(f"[WARN] {msg}")
                def error(self, msg): print(f"[ERROR] {msg}")
            return Logger()


class GPSDeniedLocalizationNode(Node):
    def __init__(self):
        super().__init__('gps_denied_localization_node')

        # Load parameters or defaults
        self.device_id = "unit_001"
        self.ref_point = ReferencePoint(
            latitude=12.97160000,
            longitude=77.59460000,
            altitude=900.0,
            heading=0.0
        )

        # Core subsystems
        self.esekf = ESEKF15(ESEKFConfig())
        self.fastlio = FastLioAdapter()
        self.health = HealthMonitor()
        self.telemetry = TelemetryPublisher(
            device_id=self.device_id,
            auth_token="dev-device-token-secret",
            server_url="http://localhost:8000/api/telemetry"
        )

        # State tracking
        self.last_imu_timestamp: Optional[float] = None
        self.esekf.set_initial_state(
            p0=np.array([0.0, 0.0, 0.0]),
            heading_deg=self.ref_point.heading
        )

        if ROS2_AVAILABLE:
            self._init_ros2_interfaces()

    def _init_ros2_interfaces(self) -> None:
        qos_sensor = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        qos_reliable = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # Subscribers
        self.sub_imu = self.create_subscription(
            Imu, '/imu/data', self.handle_imu, qos_sensor
        )
        self.sub_lidar = self.create_subscription(
            PointCloud2, '/lidar/points', self.handle_lidar_points, qos_sensor
        )
        self.sub_vel = self.create_subscription(
            TwistStamped, '/velocity', self.handle_velocity, qos_sensor
        )
        self.sub_lio = self.create_subscription(
            Odometry, '/lio/pose', self.handle_lio_odometry, qos_reliable
        )

        # Publishers & TF
        self.pub_telemetry = self.create_publisher(String, '/localization/telemetry', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        # Telemetry Timer at 10Hz
        self.timer = self.create_timer(0.1, self.dispatch_telemetry)
        self.get_logger().info("GPS-Denied Localization Node initialized successfully.")

    def handle_imu(self, msg: Any) -> None:
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        if not self.health.record_imu(stamp):
            return

        if self.last_imu_timestamp is None:
            self.last_imu_timestamp = stamp
            return

        dt = stamp - self.last_imu_timestamp
        self.last_imu_timestamp = stamp

        if dt <= 0.0 or dt > 0.5:
            return

        a_meas = np.array([
            msg.linear_acceleration.x,
            msg.linear_acceleration.y,
            msg.linear_acceleration.z
        ], dtype=np.float64)

        w_meas = np.array([
            msg.angular_velocity.x,
            msg.angular_velocity.y,
            msg.angular_velocity.z
        ], dtype=np.float64)

        self.esekf.predict_imu(a_meas, w_meas, dt)
        self.health.record_ekf()

    def handle_lidar_points(self, msg: Any) -> None:
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        self.health.record_lidar(stamp)

    def handle_velocity(self, msg: Any) -> None:
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        self.health.record_velocity(stamp)

        v_meas = np.array([
            msg.twist.linear.x,
            msg.twist.linear.y,
            msg.twist.linear.z
        ], dtype=np.float64)

        self.esekf.update_velocity(v_meas, frame="body")

    def handle_lio_odometry(self, msg: Any) -> None:
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        if not self.health.record_lio(stamp):
            return

        p_raw = (msg.pose.pose.position.x, msg.pose.pose.position.y, msg.pose.pose.position.z)
        q_raw = (
            msg.pose.pose.orientation.w,
            msg.pose.pose.orientation.x,
            msg.pose.pose.orientation.y,
            msg.pose.pose.orientation.z
        )

        parsed = self.fastlio.parse_odometry_message(p_raw, q_raw)
        self.esekf.update_lio(
            parsed["position"],
            parsed["orientation"],
            parsed["covariance"]
        )

    def dispatch_telemetry(self) -> Dict[str, Any]:
        """Constructs and dispatches telemetry message."""
        now = time.time()
        east, north, up = self.esekf.p
        v_e, v_n, v_u = self.esekf.v
        roll, pitch, yaw = self.esekf.get_euler_angles()
        speed = self.esekf.get_speed()
        heading = self.esekf.get_heading_deg()
        horiz_dist, dist_3d = compute_distances(east, north, up)
        acc = self.esekf.get_position_accuracy()

        # Rigorous Geodetic WGS-84 conversion
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
            timestamp=now,
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
            health_info=health_summary
        )

        self.health.record_telemetry()
        # Publish via REST or MQTT
        self.telemetry.publish_http(payload)
        self.telemetry.publish_mqtt(payload)

        # Publish to ROS 2 topic if ROS 2 is active
        if ROS2_AVAILABLE and hasattr(self, 'pub_telemetry'):
            ros_msg = String()
            ros_msg.data = json.dumps(payload)
            self.pub_telemetry.publish(ros_msg)

        return payload


def main(args=None):
    if ROS2_AVAILABLE:
        rclpy.init(args=args)
        node = GPSDeniedLocalizationNode()
        try:
            rclpy.spin(node)
        except KeyboardInterrupt:
            pass
        finally:
            node.destroy_node()
            rclpy.shutdown()
    else:
        print("Running GPS-Denied Localization Node in Standalone Mode...")
        node = GPSDeniedLocalizationNode()
        while True:
            try:
                node.dispatch_telemetry()
                time.sleep(0.1)
            except KeyboardInterrupt:
                break


if __name__ == '__main__':
    main()
