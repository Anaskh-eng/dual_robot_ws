import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import GroupAction, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node, PushRosNamespace


def _nav2_group(namespace, params_file, map_yaml, rviz_config):

    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    return GroupAction([
        PushRosNamespace(namespace),

        Node(
            package='nav2_map_server',
            executable='map_server',
            name='map_server',
            output='screen',
            parameters=[{
                'use_sim_time': True,
                'yaml_filename': map_yaml,
                'frame_id': 'map',
            }]
        ),

        Node(
            package='nav2_amcl',
            executable='amcl',
            name='amcl',
            output='screen',
            parameters=[params_file, {'use_sim_time': True}]
        ),

        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_localization',
            output='screen',
            parameters=[{
                'use_sim_time': True,
                'autostart': True,
                'node_names': ['map_server', 'amcl'],
            }]
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(nav2_bringup_dir, 'launch', 'navigation_launch.py')
            ),
            launch_arguments={
                'use_sim_time': 'true',
                'params_file': params_file,
                'namespace': namespace,
                'use_namespace': 'True',
                'autostart': 'True',
                'map_subscribe_transient_local': 'True',
            }.items()
        ),

        # RViz2 — one window per robot
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config],
            parameters=[{'use_sim_time': True}]
        ),
    ])


def generate_launch_description():

    pkg_dir = get_package_share_directory('dual_robot_nav')

    map_yaml     = os.path.join(pkg_dir, 'maps',   'fms_layout2.yaml')
    params_tb3_1 = os.path.join(pkg_dir, 'config', 'nav2_params_tb3_1.yaml')
    params_tb3_2 = os.path.join(pkg_dir, 'config', 'nav2_params_tb3_2.yaml')
    rviz_tb3_1   = os.path.join(pkg_dir, 'rviz',   'tb3_1_nav.rviz')
    rviz_tb3_2   = os.path.join(pkg_dir, 'rviz',   'tb3_2_nav.rviz')

    nav_tb3_1 = _nav2_group('TB3_1', params_tb3_1, map_yaml, rviz_tb3_1)
    nav_tb3_2 = TimerAction(
        period=5.0,
        actions=[_nav2_group('TB3_2', params_tb3_2, map_yaml, rviz_tb3_2)]
    )

    return LaunchDescription([nav_tb3_1, nav_tb3_2])
