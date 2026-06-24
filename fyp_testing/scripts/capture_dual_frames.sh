#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FYP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DUAL_WS="${DUAL_WS:-/home/anaskh007/dual_robot_ws}"

LABEL="${1:-dual_namespaces}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="${FYP_DIR}/results/plots/${LABEL}_${STAMP}"
mkdir -p "${OUT_DIR}"

set +u
source "${DUAL_WS}/install/setup.bash"
set -u

echo "[capture_frames] Output directory: ${OUT_DIR}"

capture_frames_for() {
  local name="$1"
  shift
  local frame_dir="${OUT_DIR}/${name}"
  mkdir -p "${frame_dir}"

  echo "[capture_frames] Capturing TF frame graph: ${name}"
  (
    cd "${frame_dir}"
    timeout 15s ros2 run tf2_tools view_frames "$@" > view_frames.log 2>&1 || true
  )

  local frame_pdf
  frame_pdf="$(find "${frame_dir}" -maxdepth 1 -type f -name 'frames*.pdf' | sort | tail -1 || true)"
  if [[ -n "${frame_pdf}" ]]; then
    cp "${frame_pdf}" "${FYP_DIR}/results/plots/${LABEL}_${STAMP}_${name}_frames.pdf"
    echo "[capture_frames] ${name} frame PDF: ${FYP_DIR}/results/plots/${LABEL}_${STAMP}_${name}_frames.pdf"
  else
    echo "[capture_frames] WARNING: ${name} frame PDF was not generated. Check ${frame_dir}/view_frames.log"
  fi
}

# The dual launch remaps TF into robot namespaces. A default global /tf capture
# may be empty, so capture each namespaced TF tree explicitly.
capture_frames_for "global"
capture_frames_for "TB3_1" --ros-args -r /tf:=/TB3_1/tf -r /tf_static:=/TB3_1/tf_static
capture_frames_for "TB3_2" --ros-args -r /tf:=/TB3_2/tf -r /tf_static:=/TB3_2/tf_static

TOPIC_OUT="${FYP_DIR}/results/plots/${LABEL}_${STAMP}_topic_isolation.txt"
echo "[capture_frames] Capturing topic/node isolation snapshot..."
{
  echo "== Namespaced nodes =="
  ros2 node list | sort | grep -E '^/TB3_[12]/' || true
  echo
  echo "== Namespaced topics =="
  ros2 topic list | sort | grep -E '^/TB3_[12]/' || true
  echo
  echo "== Key publisher/subscriber details =="
  for topic in \
    /TB3_1/cmd_vel /TB3_2/cmd_vel \
    /TB3_1/odom /TB3_2/odom \
    /TB3_1/amcl_pose /TB3_2/amcl_pose \
    /TB3_1/scan /TB3_2/scan; do
    echo "--- ${topic}"
    ros2 topic info -v "${topic}" || true
    echo
  done
} > "${TOPIC_OUT}" 2>&1

echo "[capture_frames] Topic isolation text: ${TOPIC_OUT}"
echo "[capture_frames] Done."
