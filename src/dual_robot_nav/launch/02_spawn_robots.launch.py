"""
Launch File: 02_spawn_robots.launch.py

Spawns two TurtleBot3 Waffle Pi robots into Gazebo.

The URDF is still used by robot_state_publisher for TF and RViz, but Gazebo
must spawn from the TurtleBot3 SDF model because that file contains the ROS
plugins for cmd_vel, odom, scan, and joint_states.
"""

import os
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler, LogInfo
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


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


def get_sdf_path() -> str:
    """Find and return the TB3 Waffle Pi SDF path with validation."""
    pkg = get_package_share_directory('turtlebot3_gazebo')
    sdf = os.path.join(pkg, 'models', 'turtlebot3_waffle_pi', 'model.sdf')
    if not os.path.isfile(sdf):
        raise FileNotFoundError(f"SDF not found: {sdf}")
    print(f"[SPAWN] Using Gazebo SDF: {sdf}")
    return sdf


def make_robot_sdf(namespace: str, source_sdf: str) -> str:
    """Create a namespaced copy of the TurtleBot3 SDF for Gazebo plugins."""
    output_dir = '/tmp/dual_robot_nav_sdf'
    os.makedirs(output_dir, exist_ok=True)

    output_sdf = os.path.join(output_dir, f'{namespace}.sdf')
    tree = ET.parse(source_sdf)
    root = tree.getroot()

    for odom_frame_tag in root.iter('odometry_frame'):
        odom_frame_tag.text = f'{namespace}/odom'

    for base_frame_tag in root.iter('robot_base_frame'):
        base_frame_tag.text = f'{namespace}/base_footprint'

    for scan_frame_tag in root.iter('frame_name'):
        scan_frame_tag.text = f'{namespace}/base_scan'

    for ros_tag in root.iter('ros'):
        existing = {
            remapping.text.strip()
            for remapping in ros_tag.findall('remapping')
            if remapping.text
        }
        for remap in ('/tf:=tf', '/tf_static:=tf_static'):
            if remap not in existing:
                remapping_tag = ET.SubElement(ros_tag, 'remapping')
                remapping_tag.text = remap

    # spawn_entity.py reads the file into a Python string before parsing it with
    # lxml, which rejects Unicode strings that contain an XML declaration.
    tree.write(output_sdf, encoding='unicode', xml_declaration=False)
    print(f"[SPAWN] Generated namespaced SDF for {namespace}: {output_sdf}")
    return output_sdf


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

    sdf_path = get_sdf_path()
    tb3_1_sdf = make_robot_sdf('TB3_1', sdf_path)
    tb3_2_sdf = make_robot_sdf('TB3_2', sdf_path)
    tf_remappings = [('/tf', 'tf'), ('/tf_static', 'tf_static')]

    # ── Robot 1 ───────────────────────────────────────────────────────────────
    rsp_tb3_1 = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        namespace='TB3_1',
        output='screen',
        remappings=tf_remappings,
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
            '-file',            tb3_1_sdf,
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
        remappings=tf_remappings,
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
            '-file',            tb3_2_sdf,
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
