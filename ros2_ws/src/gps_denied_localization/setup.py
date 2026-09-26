from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'gps_denied_localization'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Navigation Engineer',
    maintainer_email='dev@gpsdenied.local',
    description='GPS-denied localization pipeline integrating LiDAR, IMU, Velocity sensor with 15-state ESEKF and WGS-84 telemetry',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'localization_node = gps_denied_localization.localization_node:main',
            'simulator_node = gps_denied_localization.synthetic_sensor_stream:main',
        ],
    },
)
