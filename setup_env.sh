#!/bin/bash
# ==============================================================
# Dual Robot Navigation — Environment Configuration
# Source this in EVERY terminal before running any launch file:
#   source ~/dual_robot_ws/setup_env.sh
# ==============================================================

# ── Detect actual workspace root from this script's location ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$SCRIPT_DIR"

echo "[ENV] Workspace root: $WS_ROOT"

# ── ROS2 base ─────────────────────────────────────────────────
source /opt/ros/humble/setup.bash

# ── Workspace install — only after first colcon build ─────────
INSTALL_SETUP="$WS_ROOT/install/setup.bash"
if [ -f "$INSTALL_SETUP" ]; then
    source "$INSTALL_SETUP"
    echo "[ENV] Workspace sourced: $INSTALL_SETUP"
else
    echo "[WARN] Workspace not built yet. Run:"
    echo "       cd $WS_ROOT && colcon build --symlink-install"
fi

# ── TurtleBot3 ────────────────────────────────────────────────
export TURTLEBOT3_MODEL=waffle_pi

# Gazebo resolves TurtleBot3 mesh URIs such as model://turtlebot3_common
# through GAZEBO_MODEL_PATH.
TB3_GAZEBO_MODELS="/opt/ros/humble/share/turtlebot3_gazebo/models"
case ":${GAZEBO_MODEL_PATH:-}:" in
    *":$TB3_GAZEBO_MODELS:"*) ;;
    *) export GAZEBO_MODEL_PATH="$TB3_GAZEBO_MODELS:${GAZEBO_MODEL_PATH:-}" ;;
esac

# ── DDS ───────────────────────────────────────────────────────
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0

# ── CycloneDDS config (only if workspace is built) ────────────
if [ -f "$INSTALL_SETUP" ]; then
    CYCLONE_XML="$(ros2 pkg prefix dual_robot_nav 2>/dev/null)/share/dual_robot_nav/config/cyclonedds.xml"
    if [ -f "$CYCLONE_XML" ]; then
        export CYCLONEDDS_URI="file://$CYCLONE_XML"
        echo "[ENV] CycloneDDS config: $CYCLONE_XML"
    else
        echo "[WARN] cyclonedds.xml not found at expected path: $CYCLONE_XML"
    fi
fi

echo "[ENV] Gazebo models: $TB3_GAZEBO_MODELS"
echo "[ENV] RMW=$RMW_IMPLEMENTATION | DOMAIN=$ROS_DOMAIN_ID | MODEL=$TURTLEBOT3_MODEL"
