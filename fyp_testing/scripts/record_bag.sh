#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FYP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
RECORD_WS="${FYP_RECORD_WS:-${DUAL_WS:-/home/anaskh007/dual_robot_ws}}"

RUN_ID="${1:-}"
shift || true

if [[ -z "${RUN_ID}" ]]; then
  RUN_ID="manual_$(date +%Y%m%d_%H%M%S)"
fi

BAG_DIR="${FYP_DIR}/results/bags/${RUN_ID}"
mkdir -p "$(dirname "${BAG_DIR}")"

set +u
source "${RECORD_WS}/install/setup.bash"
set -u

DEFAULT_TOPICS=(
  /clock
  /rosout
  /gazebo/model_states
  /model_states
  /TB3_1/odom
  /TB3_2/odom
  /TB3_1/amcl_pose
  /TB3_2/amcl_pose
  /TB3_1/plan
  /TB3_2/plan
  /TB3_1/cmd_vel
  /TB3_2/cmd_vel
)

if [[ "${FYP_RECORD_SCANS:-false}" == "true" ]]; then
  DEFAULT_TOPICS+=(
    /TB3_1/scan
    /TB3_2/scan
  )
fi

if [[ "$#" -gt 0 ]]; then
  TOPICS=("$@")
else
  TOPICS=("${DEFAULT_TOPICS[@]}")
fi

echo "[record_bag] Recording ${RUN_ID}"
echo "[record_bag] Output: ${BAG_DIR}"
exec ros2 bag record -o "${BAG_DIR}" "${TOPICS[@]}"
