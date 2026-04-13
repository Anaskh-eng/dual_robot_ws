"""
Launch File: 02_spawn_robots.launch.py

Root cause fix: turtlebot3_waffle_pi.urdf is actually a xacro file that
requires a 'namespace' argument. Reading it as raw text leaves ${namespace}
as a literal string, producing a malformed URDF that crashes Gazebo.

Fix: Use xacro.process_file() with the namespace mapping so all TF frames
resolve correctly: ${namespace}base_footprint -> TB3_1/base_footprint
"""

import os
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace


def get_robot_description(namespace: str) -> str:
    """
    Process the TurtleBot3 Waffle Pi xacro file with the robot's namespace.

    The 'namespace' xacro argument is prepended to all link/joint names,
    producing globally unique TF frames such as TB3_1/base_footprint.

    Args:
        namespace: Robot namespace string WITHOUT trailing slash, e.g. 'TB3_1'

    Returns:
        Processed URDF XML string ready for robot_state_publisher.
    """
    tb3_desc_pkg = get_package_share_directory('turtlebot3_description')
    xacro_file = os.path.join(tb3_desc_pkg, 'urdf', 'turtlebot3_waffle_pi.urdf')

    # The xacro variable 'namespace' is used as a prefix in all frame names.
    # We append '/' so frames become 'TB3_1/base_footprint' (ROS2 TF convention).
    doc = xacro.process_file(
        xacro_file,
        mappings={'namespace': namespace + '/'}
    )
    return doc.toxml()


def generate_launch_description():

    # ── Spawn pose arguments (overridable from CLI) ───────────────────────────
    args = [
        DeclareLaunchArgument('tb3_1_x',   default_value='-2.0'),
        DeclareLaunchArgument('tb3_1_y',   default_value='-0.5'),
        DeclareLaunchArgument('tb3_1_yaw', default_value='0.0'),
        DeclareLaunchArgument('tb3_2_x',   default_value='2.0'),
        DeclareLaunchArgument('tb3_2_y',   default_value='-0.5'),
        DeclareLaunchArgument('tb3_2_yaw', default_value='3.14159'),
    ]

    # Process xacro at launch time — namespace is now fully resolved
    robot_desc_tb3_1 = get_robot_description('TB3_1')
    robot_desc_tb3_2 = get_robot_description('TB3_2')

    # ── Robot 1 ───────────────────────────────────────────────────────────────
    robot_1_group = GroupAction([
        PushRosNamespace('TB3_1'),

        # Publishes TF: TB3_1/base_footprint, TB3_1/base_link, etc.
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{
                'robot_description': robot_desc_tb3_1,
                'use_sim_time': True,
                # frame_prefix NOT needed here — xacro already embedded
                # the namespace into every link/joint name in the URDF
            }]
        ),

        Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            name='spawn_tb3_1',
            output='screen',
            arguments=[
                '-entity',          'TB3_1',
                '-robot_namespace', 'TB3_1',
                '-topic',           '/TB3_1/robot_description',
                '-x',  LaunchConfiguration('tb3_1_x'),
                '-y',  LaunchConfiguration('tb3_1_y'),
                '-z',  '0.01',
                '-Y',  LaunchConfiguration('tb3_1_yaw'),
            ]
        ),
    ])

    # ── Robot 2 (4s delay — avoids Gazebo factory race condition) ─────────────
    robot_2_group = TimerAction(
        period=4.0,
        actions=[GroupAction([
            PushRosNamespace('TB3_2'),

            Node(
                package='robot_state_publisher',
                executable='robot_state_publisher',
                name='robot_state_publisher',
                output='screen',
                parameters=[{
                    'robot_description': robot_desc_tb3_2,
                    'use_sim_time': True,
                }]
            ),

            Node(
                package='gazebo_ros',
                executable='spawn_entity.py',
                name='spawn_tb3_2',
                output='screen',
                arguments=[
                    '-entity',          'TB3_2',
                    '-robot_namespace', 'TB3_2',
                    '-topic',           '/TB3_2/robot_description',
                    '-x',  LaunchConfiguration('tb3_2_x'),
                    '-y',  LaunchConfiguration('tb3_2_y'),
                    '-z',  '0.01',
                    '-Y',  LaunchConfiguration('tb3_2_yaw'),
                ]
            ),
        ])]
    )

    return LaunchDescription([*args, robot_1_group, robot_2_group])
