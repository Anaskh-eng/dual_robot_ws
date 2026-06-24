#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FYP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SINGLE_WS="${SINGLE_WS:-/home/anaskh007/Anasros2_ws}"

stop_process() {
  local pid="${1:-}"
  local label="${2:-process}"
  local grace="${3:-15}"

  if [[ -z "${pid}" ]] || ! kill -0 "${pid}" 2>/dev/null; then
    return 0
  fi

  echo "[run_single] Stopping ${label} (pid ${pid})"
  kill -INT "-${pid}" 2>/dev/null || kill -INT "${pid}" 2>/dev/null || true

  for _ in $(seq 1 "${grace}"); do
    if ! kill -0 "${pid}" 2>/dev/null; then
      wait "${pid}" 2>/dev/null || true
      return 0
    fi
    sleep 1
  done

  echo "[run_single] ${label} did not stop after SIGINT; sending SIGTERM"
  kill -TERM "-${pid}" 2>/dev/null || kill -TERM "${pid}" 2>/dev/null || true
  sleep 3

  if kill -0 "${pid}" 2>/dev/null; then
    echo "[run_single] ${label} still running; sending SIGKILL"
    kill -KILL "-${pid}" 2>/dev/null || kill -KILL "${pid}" 2>/dev/null || true
  fi
  wait "${pid}" 2>/dev/null || true
}

stop_stale_single_gazebo() {
  local stale_pids
  stale_pids="$(pgrep -f 'single_robot_nav/share/single_robot_nav/worlds/.*\\.world' || true)"
  if [[ -z "${stale_pids}" ]]; then
    return 0
  fi

  echo "[run_single] Found stale single_robot_nav Gazebo process(es): ${stale_pids}"
  echo "[run_single] Stopping them before starting a new experiment."
  for pid in ${stale_pids}; do
    stop_process "${pid}" "stale single Gazebo" 8
  done
}

LAYOUT="${1:-}"
REPEAT="${2:-1}"
DURATION_SEC="${3:-420}"
INFLATION_RADIUS="${4:-default}"
VISUAL_MODE="${5:-${FYP_VISUAL:-false}}"

if [[ -z "${LAYOUT}" ]]; then
  echo "Usage: $0 <layout:1|2|3|4> [repeat] [duration_sec] [inflation_radius_label] [visual|headless]"
  exit 2
fi

case "${LAYOUT}" in
  1) WORLD_LAUNCH="fms_complete.launch.py"; MISSION_EXE="single_robot_nav"; INITIAL_X="-1.0"; INITIAL_Y="-3.5"; INITIAL_YAW="1.57" ;;
  2) WORLD_LAUNCH="fms2_complete.launch.py"; MISSION_EXE="single_robot_nav_fms2"; INITIAL_X="-3.5"; INITIAL_Y="1.0"; INITIAL_YAW="0.0" ;;
  3) WORLD_LAUNCH="fms3_complete.launch.py"; MISSION_EXE="single_robot_nav_fms3"; INITIAL_X="-1.0"; INITIAL_Y="-3.0"; INITIAL_YAW="1.57" ;;
  4) WORLD_LAUNCH="fms4_complete.launch.py"; MISSION_EXE="single_robot_nav_fms4"; INITIAL_X="-3.5"; INITIAL_Y="-1.0"; INITIAL_YAW="0.0" ;;
  *) echo "Unknown layout: ${LAYOUT}. Use 1, 2, 3, or 4."; exit 2 ;;
esac

RUN_ID="single_layout${LAYOUT}_r${REPEAT}_infl${INFLATION_RADIUS}_$(date +%Y%m%d_%H%M%S)"
LOG_DIR="${FYP_DIR}/results/logs/${RUN_ID}"
mkdir -p "${LOG_DIR}"

set +u
source "${SINGLE_WS}/install/setup.bash"
set -u

MAP_FILE="${SINGLE_WS}/install/single_robot_nav/share/single_robot_nav/maps/fms_layout${LAYOUT}.yaml"
PARAMS_FILE="${SINGLE_WS}/install/single_robot_nav/share/single_robot_nav/config/nav2_params.yaml"

if [[ -n "${FYP_SINGLE_PARAMS_FILE:-}" ]]; then
  PARAMS_FILE="${FYP_SINGLE_PARAMS_FILE}"
fi

RVIZ="${FYP_RVIZ:-false}"
case "${VISUAL_MODE}" in
  visual|gui|rviz|true|1|yes)
    RVIZ="true"
    ;;
  headless|false|0|no)
    ;;
  *)
    echo "Unknown visual mode: ${VISUAL_MODE}. Use visual or headless."
    exit 2
    ;;
esac

echo "[run_single] Run ID: ${RUN_ID}"
echo "[run_single] World: ${WORLD_LAUNCH}"
echo "[run_single] Mission: ${MISSION_EXE}"
echo "[run_single] Duration: ${DURATION_SEC}s"
echo "[run_single] RViz: ${RVIZ}"
echo "[run_single] Initial pose: x=${INITIAL_X}, y=${INITIAL_Y}, yaw=${INITIAL_YAW}"

stop_stale_single_gazebo

FYP_RECORD_WS="${SINGLE_WS}" setsid "${SCRIPT_DIR}/record_bag.sh" "${RUN_ID}" /clock /rosout /gazebo/model_states /odom /amcl_pose /plan /cmd_vel /scan > "${LOG_DIR}/rosbag.log" 2>&1 &
BAG_PID=$!

setsid ros2 launch single_robot_nav "${WORLD_LAUNCH}" > "${LOG_DIR}/gazebo.log" 2>&1 &
GAZEBO_PID=$!
sleep 8

setsid ros2 launch single_robot_nav single_robot_nav2.launch.py \
  map:="${MAP_FILE}" \
  params_file:="${PARAMS_FILE}" \
  use_sim_time:=true \
  initial_x:="${INITIAL_X}" \
  initial_y:="${INITIAL_Y}" \
  initial_yaw:="${INITIAL_YAW}" > "${LOG_DIR}/nav2.log" 2>&1 &
NAV_PID=$!
sleep 18

RVIZ_PID=""
if [[ "${RVIZ}" == "true" ]]; then
  setsid ros2 run rviz2 rviz2 \
    -d "${SINGLE_WS}/install/single_robot_nav/share/single_robot_nav/rviz/nav2_default_view.rviz" > "${LOG_DIR}/rviz.log" 2>&1 &
  RVIZ_PID=$!
fi

set +e
timeout --signal=INT "${DURATION_SEC}s" ros2 run mission_planner "${MISSION_EXE}" > "${LOG_DIR}/mission.log" 2>&1
MISSION_RC=$?
set -e

if [[ -n "${RVIZ_PID}" ]]; then
  stop_process "${RVIZ_PID}" "rviz" 8
fi
stop_process "${NAV_PID}" "nav2 launch" 15
stop_process "${GAZEBO_PID}" "gazebo launch" 15
stop_process "${BAG_PID}" "rosbag recorder" 20

if [[ ! -f "${FYP_DIR}/results/bags/${RUN_ID}/metadata.yaml" ]]; then
  echo "[run_single] ERROR: rosbag metadata was not created."
  echo "[run_single] Check: ${LOG_DIR}/rosbag.log"
  exit 1
fi

SUCCESS="false"
if [[ "${MISSION_RC}" -eq 0 ]]; then
  SUCCESS="true"
fi
NOTES="mission exited with code ${MISSION_RC}"

python3 "${SCRIPT_DIR}/analyze_rosbag.py" \
  "${FYP_DIR}/results/bags/${RUN_ID}" \
  --mode single \
  --layout "${LAYOUT}" \
  --repeat "${REPEAT}" \
  --inflation-radius "${INFLATION_RADIUS}" \
  --success "${SUCCESS}" \
  --notes "${NOTES}" \
  --output "${FYP_DIR}/results/csv/${RUN_ID}_metrics.csv"

echo "[run_single] Metrics: ${FYP_DIR}/results/csv/${RUN_ID}_metrics.csv"
echo "[run_single] Logs: ${LOG_DIR}"
