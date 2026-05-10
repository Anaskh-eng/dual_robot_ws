"""
Launch File: fms_layout2_bringup.launch.py
Purpose   : Bring up FMS layout 2 with its map, robot spawn poses, and mission.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg_dir = get_package_share_directory('dual_robot_nav')

    gui_arg = DeclareLaunchArgument(
        'gui',
        default_value='true',
        description='Launch Gazebo GUI.'
    )
    rviz_arg = DeclareLaunchArgument(
        'rviz',
        default_value='true',
        description='Launch RViz2 windows.'
    )

    bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_dir, 'launch', '10_bringup.launch.py')
        ),
        launch_arguments={
            'gui': LaunchConfiguration('gui'),
            'rviz': LaunchConfiguration('rviz'),
        }.items()
    )

    return LaunchDescription([gui_arg, rviz_arg, bringup])
