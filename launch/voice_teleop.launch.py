"""
Launches:
  1. TurtleBot3 in an empty Gazebo world
  2. RViz2 with a basic view (robot model + laser scan)
  3. The voice_commander node (text input by default)

Usage:
    export TURTLEBOT3_MODEL=waffle_pi
    ros2 launch voice_teleop voice_teleop.launch.py

Then type commands (straight / left / right / back / stop) in the terminal
running this launch file.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition
from launch_ros.actions import Node


def generate_launch_description():
    use_rviz_arg = DeclareLaunchArgument(
        "use_rviz",
        default_value="true",
        description="Whether to launch RViz2 alongside Gazebo",
    )

    tb3_gazebo_share = get_package_share_directory("turtlebot3_gazebo")
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(tb3_gazebo_share, "launch", "empty_world.launch.py")
        )
    )

    voice_teleop_share = get_package_share_directory("voice_teleop")
    rviz_config = os.path.join(voice_teleop_share, "rviz", "voice_teleop.rviz")

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=["-d", rviz_config],
        condition=IfCondition(LaunchConfiguration("use_rviz")),
        output="screen",
    )

    voice_commander_node = Node(
        package="voice_teleop",
        executable="voice_commander",
        name="voice_commander",
        output="screen",
        emulate_tty=True,  # keeps input() working nicely inside a launch file
    )

    return LaunchDescription(
        [
            use_rviz_arg,
            gazebo_launch,
            rviz_node,
            voice_commander_node,
        ]
    )
