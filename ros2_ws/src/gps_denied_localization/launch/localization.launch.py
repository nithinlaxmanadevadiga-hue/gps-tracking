import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('gps_denied_localization')
    params_file = os.path.join(pkg_share, 'config', 'params.yaml')
    calib_file = os.path.join(pkg_share, 'config', 'calibration.yaml')

    # Static Transform Publisher for map -> base_link -> imu_link / lidar_link
    tf_base_to_imu = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='base_to_imu_tf',
        arguments=['0', '0', '0', '0', '0', '0', 'base_link', 'imu_link']
    )

    tf_base_to_lidar = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='base_to_lidar_tf',
        arguments=['0.05', '0.0', '0.12', '0', '0', '0', 'base_link', 'lidar_link']
    )

    localization_node = Node(
        package='gps_denied_localization',
        executable='localization_node',
        name='gps_denied_localization_node',
        output='screen',
        parameters=[params_file, calib_file]
    )

    return LaunchDescription([
        tf_base_to_imu,
        tf_base_to_lidar,
        localization_node,
    ])
