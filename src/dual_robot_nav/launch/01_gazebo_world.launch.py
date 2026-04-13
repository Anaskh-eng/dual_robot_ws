"""
Launch File: 01_gazebo_world.launch.py
Purpose   : Start Gazebo with the custom warehouse world.
            This is the FIRST launch file to run.
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, ExecuteProcess,
                             SetEnvironmentVariable)
from launch.substitutions import LaunchConfiguration


def generate_launch_description():

    pkg_dir = get_package_share_directory('dual_robot_nav')

    # ── Arguments ──────────────────────────────────────────────────────────────
    world_file_arg = DeclareLaunchArgument(
        'world',
        default_value=os.path.join(pkg_dir, 'worlds', 'fms_layout2.world'),
        description='Full path to the custom Gazebo world file.'
    )

    use_gui_arg = DeclareLaunchArgument(
        'gui',
        default_value='true',
        description='Set to false to run Gazebo headless (gzserver only).'
    )

    # ── Environment: suppress Gazebo console spam ──────────────────────────────
    set_gz_verbosity = SetEnvironmentVariable(
        name='GAZEBO_MODEL_VERBOSITY',
        value='3'
    )

    # ── Gazebo Server ──────────────────────────────────────────────────────────
    # We use gzserver + gzclient as separate processes for better stability.
    gzserver = ExecuteProcess(
        cmd=[
            'gzserver',
            '--verbose',
            '-s', 'libgazebo_ros_init.so',      # ROS2-Gazebo bridge: /clock, params
            '-s', 'libgazebo_ros_factory.so',   # ROS2-Gazebo bridge: spawn_entity
            LaunchConfiguration('world')
        ],
        output='screen'
    )

    gzclient = ExecuteProcess(
        cmd=['gzclient'],
        output='screen',
        condition=__import__('launch.conditions', fromlist=['IfCondition'])
                  .IfCondition(LaunchConfiguration('gui'))
    )

    return LaunchDescription([
        set_gz_verbosity,
        world_file_arg,
        use_gui_arg,
        gzserver,
        gzclient,
    ])