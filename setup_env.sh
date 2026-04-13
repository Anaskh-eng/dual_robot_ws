#!/bin/bash
# ==============================================================
# Dual Robot Navigation — Environment Configuration
# Source this file before every terminal session:
#   source ~/dual_robot_ws/setup_env.sh
# ==============================================================

source /opt/ros/humble/setup.bash

# Only source the workspace install if it exists (i.e. after first build)
INSTALL_SETUP=~/dual_robot_ws/install/setup.bash
if [ -f "$INSTALL_SETUP" ]; then
  source "$INSTALL_SETUP"
else
  echo "[WARN] Workspace not built yet. Run colcon build first."
fi

export TURTLEBOT3_MODEL=waffle_pi
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0

# CycloneDDS config — only set after the workspace is built
if [ -f "$INSTALL_SETUP" ]; then
  export CYCLONEDDS_URI=file://$(ros2 pkg prefix dual_robot_nav)/share/dual_robot_nav/config/cyclonedds.xml
fi

echo "[ENV] Dual robot environment configured."
echo "      RMW: $RMW_IMPLEMENTATION | DOMAIN: $ROS_DOMAIN_ID | MODEL: $TURTLEBOT3_MODEL"
