"""
Launch File: 10_bringup.launch.py
Purpose   : Single-command launcher that orchestrates all phases in order.
            Layout 2 Gazebo -> Spawn Robots -> Navigation -> Mission Controller

Usage:
    ros2 launch dual_robot_nav 10_bringup.launch.py
    ros2 launch dual_robot_nav 10_bringup.launch.py gui:=false  # headless
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                             TimerAction)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    pkg_dir = get_package_share_directory('dual_robot_nav')

    gui_arg = DeclareLaunchArgument(
        'gui', default_value='true',
        description='Launch Gazebo GUI (gzclient).'
    )

    rviz_arg = DeclareLaunchArgument(
        'rviz', default_value='true',
        description='Launch RViz2 windows from the navigation launch.'
    )

    # ── Phase 1: Gazebo world (t=0s) ──────────────────────────────────────────
    launch_gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_dir, 'launch', '11_gazebo_world.launch.py')
        ),
        launch_arguments={'gui': LaunchConfiguration('gui')}.items()
    )

    # ── Phase 2: Spawn robots (t=5s, after Gazebo is ready) ───────────────────
    launch_spawn = TimerAction(
        period=12.0,
        actions=[IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_dir, 'launch', '12_spawn_robots.launch.py')
            )
        )]
    )

    # ── Phase 3: Navigation stacks (t=15s, after robots are fully spawned) ────
    launch_nav = TimerAction(
        period=15.0,
        actions=[IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_dir, 'launch', '13_navigation.launch.py')
            ),
            launch_arguments={'rviz': LaunchConfiguration('rviz')}.items()
        )]
    )

    # ── Phase 4: Layout 2 Mission Controller C++ node (t=70s, after both Nav2 stacks are up)
    mission_controller = TimerAction(
        period=70.0,
        actions=[Node(
            package='dual_robot_nav',
            executable='2_mission_controller',
            name='mission_controller',
            output='screen',
            parameters=[{'use_sim_time': True}]
        )]
    )

    return LaunchDescription([
        gui_arg,
        rviz_arg,
        launch_gazebo,
        launch_spawn,
        launch_nav,
        mission_controller,
    ])
