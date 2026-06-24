#!/usr/bin/env bash
set -euo pipefail

DUAL_WS="${DUAL_WS:-/home/anaskh007/dual_robot_ws}"
set +u
source "${DUAL_WS}/install/setup.bash"
set -u

echo "== Namespaced topics =="
ros2 topic list | sort | grep -E '^/TB3_[12]/' || true

echo
echo "== Required topic presence =="
for topic in \
  /TB3_1/cmd_vel /TB3_2/cmd_vel \
  /TB3_1/odom /TB3_2/odom \
  /TB3_1/scan /TB3_2/scan \
  /TB3_1/amcl_pose /TB3_2/amcl_pose; do
  if ros2 topic list | grep -qx "${topic}"; then
    echo "OK   ${topic}"
  else
    echo "MISS ${topic}"
  fi
done

echo
echo "== Publisher/subscriber details =="
for topic in /TB3_1/cmd_vel /TB3_2/cmd_vel /TB3_1/odom /TB3_2/odom; do
  echo "--- ${topic}"
  ros2 topic info -v "${topic}" || true
done

echo
echo "== Topic frequencies =="
for topic in /TB3_1/scan /TB3_2/scan /TB3_1/odom /TB3_2/odom /TB3_1/cmd_vel /TB3_2/cmd_vel; do
  echo "--- ${topic}"
  timeout 8s ros2 topic hz "${topic}" || true
done

echo
echo "Interpretation:"
echo "- /TB3_1/cmd_vel and /TB3_2/cmd_vel should have separate Nav2 publishers."
echo "- Odom and scan should be published by the matching namespaced Gazebo plugin."
echo "- Missing or shared publishers indicate namespace leakage or a launch problem."
