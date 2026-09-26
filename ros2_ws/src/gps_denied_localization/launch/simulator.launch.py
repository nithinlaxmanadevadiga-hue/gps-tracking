import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('gps_denied_localization')
    params_file = os.path.join(pkg_share, 'config', 'params.yaml')

    sim_node = Node(
        package='gps_denied_localization',
        executable='simulator_node',
        name='gps_denied_simulator_node',
        output='screen',
        parameters=[params_file]
    )

    return LaunchDescription([
        sim_node,
    ])
