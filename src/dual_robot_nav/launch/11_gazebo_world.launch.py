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
    tb3_gazebo_dir = get_package_share_directory('turtlebot3_gazebo')

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
    disable_gz_model_database = SetEnvironmentVariable(
        name='GAZEBO_MODEL_DATABASE_URI',
        value=''
    )
    set_gz_model_path = SetEnvironmentVariable(
        name='GAZEBO_MODEL_PATH',
        value=os.path.join(tb3_gazebo_dir, 'models') + ':' +
              os.environ.get('GAZEBO_MODEL_PATH', '')
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
        disable_gz_model_database,
        set_gz_model_path,
        world_file_arg,
        use_gui_arg,
        gzserver,
        gzclient,
    ])
