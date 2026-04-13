"""
Launch File: 02_spawn_robots.launch.py

Fix: turtlebot3_waffle_pi.urdf in Humble's turtlebot3_gazebo is plain URDF
(no xacro namespace argument). TF frame uniqueness is achieved via:
  - frame_prefix in robot_state_publisher  → prefixes all TF frames
  - Gazebo robot_namespace                 → prefixes all Gazebo topics
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, GroupAction,
                             TimerAction, RegisterEventHandler, LogInfo)
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace


def get_urdf_path() -> str:
    """Find and return the TB3 Waffle Pi URDF path with validation."""
    pkg = get_package_share_directory('turtlebot3_gazebo')
    urdf = os.path.join(pkg, 'urdf', 'turtlebot3_waffle_pi.urdf')
    if not os.path.isfile(urdf):
        available = os.listdir(os.path.join(pkg, 'urdf'))
        raise FileNotFoundError(
            f"URDF not found. Available in {pkg}/urdf/: {available}"
        )
    print(f"[SPAWN] Using URDF: {urdf}")
    return urdf


def get_robot_description() -> str:
    """Read plain URDF as string — no xacro processing needed."""
    with open(get_urdf_path(), 'r') as f:
        return f.read()


def generate_launch_description():

    args = [
        DeclareLaunchArgument('tb3_1_x',   default_value='-2.0'),
        DeclareLaunchArgument('tb3_1_y',   default_value='-0.5'),
        DeclareLaunchArgument('tb3_1_yaw', default_value='0.0'),
        DeclareLaunchArgument('tb3_2_x',   default_value='2.0'),
        DeclareLaunchArgument('tb3_2_y',   default_value='-0.5'),
        DeclareLaunchArgument('tb3_2_yaw', default_value='3.14159'),
    ]

    # Read URDF once — same base description for both robots.
    # TF uniqueness comes from frame_prefix in robot_state_publisher.
    robot_desc = get_robot_description()

    # ── Robot 1 ───────────────────────────────────────────────────────────────
    rsp_tb3_1 = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        namespace='TB3_1',
        output='screen',
        parameters=[{
            'robot_description': robot_desc,
            'use_sim_time': True,
            # This prefixes ALL TF frames: base_link → TB3_1/base_link
            'frame_prefix': 'TB3_1/',
        }]
    )

    spawn_tb3_1 = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        name='spawn_tb3_1',
        namespace='TB3_1',
        output='screen',
        arguments=[
            '-entity',          'TB3_1',
            '-robot_namespace', 'TB3_1',
            '-topic',           '/TB3_1/robot_description',
            '-x',  LaunchConfiguration('tb3_1_x'),
            '-y',  LaunchConfiguration('tb3_1_y'),
            '-z',  '0.01',
            '-Y',  LaunchConfiguration('tb3_1_yaw'),
            '-timeout', '30',
        ]
    )

    # ── Robot 2 — launched after Robot 1 spawn exits cleanly ──────────────────
    rsp_tb3_2 = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        namespace='TB3_2',
        output='screen',
        parameters=[{
            'robot_description': robot_desc,
            'use_sim_time': True,
            'frame_prefix': 'TB3_2/',
        }]
    )

    spawn_tb3_2 = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        name='spawn_tb3_2',
        namespace='TB3_2',
        output='screen',
        arguments=[
            '-entity',          'TB3_2',
            '-robot_namespace', 'TB3_2',
            '-topic',           '/TB3_2/robot_description',
            '-x',  LaunchConfiguration('tb3_2_x'),
            '-y',  LaunchConfiguration('tb3_2_y'),
            '-z',  '0.01',
            '-Y',  LaunchConfiguration('tb3_2_yaw'),
            '-timeout', '30',
        ]
    )

    spawn_tb3_2_trigger = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_tb3_1,
            on_exit=[
                LogInfo(msg='[SPAWN] TB3_1 done. Spawning TB3_2...'),
                rsp_tb3_2,
                spawn_tb3_2,
            ]
        )
    )

    return LaunchDescription([*args, rsp_tb3_1, spawn_tb3_1, spawn_tb3_2_trigger])
