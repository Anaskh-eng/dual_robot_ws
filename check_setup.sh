#!/bin/bash
source ~/dual_robot_ws/setup_env.sh

echo ""
echo "========================================"
echo "  DUAL ROBOT SETUP DIAGNOSTIC"
echo "========================================"

PASS=0; FAIL=0

check() {
    local desc="$1"; local cmd="$2"
    if eval "$cmd" &>/dev/null; then
        echo "  [PASS] $desc"
        ((PASS++))
    else
        echo "  [FAIL] $desc"
        ((FAIL++))
    fi
}

check "ROS2 Humble sourced"          "[ -d /opt/ros/humble ]"
check "Workspace built"              "[ -f ~/dual_robot_ws/install/setup.bash ]"
check "Package found"                "ros2 pkg prefix dual_robot_nav"
check "xacro installed"              "python3 -c 'import xacro'"
check "CycloneDDS RMW installed"     "python3 -c 'import rclpy; import rmw_cyclonedds_cpp' 2>/dev/null || ros2 pkg list | grep -q rmw_cyclonedds"
check "Nav2 bringup installed"       "ros2 pkg prefix nav2_bringup"
check "TB3 description installed"    "ros2 pkg prefix turtlebot3_description"
check "TB3 gazebo installed"         "ros2 pkg prefix turtlebot3_gazebo"
check "URDF file exists"             "find /opt/ros/humble -name 'turtlebot3_waffle_pi.urdf' | grep -q ."
check "Map file exists"              "[ -f ~/dual_robot_ws/src/dual_robot_nav/maps/fms_layout2.yaml ]"
check "World file exists"            "[ -f ~/dual_robot_ws/src/dual_robot_nav/worlds/fms_layout2.world ]"
check "Nav2 params TB3_1 exists"     "[ -s ~/dual_robot_ws/src/dual_robot_nav/config/nav2_params_tb3_1.yaml ]"
check "Nav2 params TB3_2 exists"     "[ -s ~/dual_robot_ws/src/dual_robot_nav/config/nav2_params_tb3_2.yaml ]"
check "RViz config TB3_1 exists"     "[ -s ~/dual_robot_ws/src/dual_robot_nav/rviz/tb3_1_nav.rviz ]"
check "RViz config TB3_2 exists"     "[ -s ~/dual_robot_ws/src/dual_robot_nav/rviz/tb3_2_nav.rviz ]"
check "CycloneDDS XML exists"        "[ -s ~/dual_robot_ws/src/dual_robot_nav/config/cyclonedds.xml ]"
check "Mission controller binary"    "[ -f ~/dual_robot_ws/install/dual_robot_nav/lib/dual_robot_nav/mission_controller ]"

echo "========================================"
echo "  RESULT: $PASS passed, $FAIL failed"
echo "========================================"

# Print URDF path for manual verification
echo ""
echo "URDF file on your system:"
find /opt/ros/humble -name "turtlebot3_waffle*" -path "*/urdf/*" 2>/dev/null
