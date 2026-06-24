#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FYP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DUAL_WS="${DUAL_WS:-/home/anaskh007/dual_robot_ws}"
BAG_PID=""
LAUNCH_PID=""

stop_process() {
  local pid="${1:-}"
  local label="${2:-process}"
  local grace="${3:-20}"

  if [[ -z "${pid}" ]] || ! kill -0 "${pid}" 2>/dev/null; then
    return 0
  fi

  echo "[run_dual] Stopping ${label} (pid ${pid})"
  kill -INT "-${pid}" 2>/dev/null || kill -INT "${pid}" 2>/dev/null || true

  for _ in $(seq 1 "${grace}"); do
    if ! kill -0 "${pid}" 2>/dev/null; then
      wait "${pid}" 2>/dev/null || true
      return 0
    fi
    sleep 1
  done

  echo "[run_dual] ${label} did not stop after SIGINT; sending SIGTERM"
  kill -TERM "-${pid}" 2>/dev/null || kill -TERM "${pid}" 2>/dev/null || true
  sleep 3

  if kill -0 "${pid}" 2>/dev/null; then
    echo "[run_dual] ${label} still running; sending SIGKILL"
    kill -KILL "-${pid}" 2>/dev/null || kill -KILL "${pid}" 2>/dev/null || true
  fi
  wait "${pid}" 2>/dev/null || true
}

cleanup_children() {
  trap - INT TERM
  stop_process "${LAUNCH_PID}" "nav2/gazebo launch" 12
  stop_process "${BAG_PID}" "rosbag recorder" 12
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
  1) LAUNCH_FILE="00_bringup.launch.py" ;;
  2) LAUNCH_FILE="10_bringup.launch.py" ;;
  3) LAUNCH_FILE="20_bringup.launch.py" ;;
  4) LAUNCH_FILE="30_bringup.launch.py" ;;
  *) echo "Unknown layout: ${LAYOUT}. Use 1, 2, 3, or 4."; exit 2 ;;
esac

RUN_ID="dual_layout${LAYOUT}_r${REPEAT}_infl${INFLATION_RADIUS}_$(date +%Y%m%d_%H%M%S)"
LOG_DIR="${FYP_DIR}/results/logs/${RUN_ID}"
mkdir -p "${LOG_DIR}"

set +u
source "${DUAL_WS}/install/setup.bash"
set -u

if [[ -n "${FYP_AMENT_PREFIX_PATH:-}" ]]; then
  export AMENT_PREFIX_PATH="${FYP_AMENT_PREFIX_PATH}:${AMENT_PREFIX_PATH:-}"
fi

GUI="${FYP_GUI:-false}"
RVIZ="${FYP_RVIZ:-false}"
case "${VISUAL_MODE}" in
  visual|true|1|yes)
    GUI="true"
    RVIZ="true"
    ;;
  gui|gazebo)
    GUI="true"
    RVIZ="false"
    ;;
  rviz)
    GUI="false"
    RVIZ="true"
    ;;
  headless|false|0|no)
    ;;
  *)
    echo "Unknown visual mode: ${VISUAL_MODE}. Use visual, gui, rviz, or headless."
    exit 2
    ;;
esac

echo "[run_dual] Run ID: ${RUN_ID}"
echo "[run_dual] Launch: dual_robot_nav ${LAUNCH_FILE}"
echo "[run_dual] Duration: ${DURATION_SEC}s"
echo "[run_dual] Gazebo GUI: ${GUI}, RViz: ${RVIZ}"

trap 'echo "[run_dual] Interrupted; cleaning up child processes"; cleanup_children; exit 130' INT TERM

setsid "${SCRIPT_DIR}/record_bag.sh" "${RUN_ID}" > "${LOG_DIR}/rosbag.log" 2>&1 &
BAG_PID=$!

setsid timeout --signal=INT "${DURATION_SEC}s" ros2 launch dual_robot_nav "${LAUNCH_FILE}" gui:="${GUI}" rviz:="${RVIZ}" > "${LOG_DIR}/launch.log" 2>&1 &
LAUNCH_PID=$!
MISSION_STOPPED=false

while kill -0 "${LAUNCH_PID}" 2>/dev/null; do
  if [[ "${FYP_STOP_ON_MISSION_COMPLETE:-true}" == "true" ]] && \
     [[ -f "${LOG_DIR}/launch.log" ]] && \
     [[ "$(grep -Ec "Returned to Loading Dock" "${LOG_DIR}/launch.log" || true)" -ge 2 ]]; then
    echo "[run_dual] Both robots returned to Loading Dock; stopping launch after 5s settle time"
    sleep 5
    stop_process "${LAUNCH_PID}" "nav2/gazebo launch" 20
    MISSION_STOPPED=true
    break
  fi
  sleep 2
done

set +e
wait "${LAUNCH_PID}" 2>/dev/null
LAUNCH_RC=$?
set -e

stop_process "${BAG_PID}" "rosbag recorder" 20
BAG_PID=""
LAUNCH_PID=""
trap - INT TERM

if [[ ! -f "${FYP_DIR}/results/bags/${RUN_ID}/metadata.yaml" ]]; then
  echo "[run_dual] ERROR: rosbag metadata was not created."
  echo "[run_dual] Check: ${LOG_DIR}/rosbag.log"
  exit 1
fi

if [[ "${LAUNCH_RC}" -ne 0 && "${LAUNCH_RC}" -ne 124 && "${LAUNCH_RC}" -ne 130 ]]; then
  if [[ "${MISSION_STOPPED}" != "true" ]]; then
    echo "[run_dual] ERROR: launch failed with code ${LAUNCH_RC} before the timed experiment completed."
    echo "[run_dual] Check: ${LOG_DIR}/launch.log"
    exit 1
  fi
fi

NOTES=""
SUCCESS="unknown"
if [[ "${MISSION_STOPPED}" == "true" ]]; then
  NOTES="both robots returned to Loading Dock; launch stopped early"
elif [[ "${LAUNCH_RC}" -eq 124 || "${LAUNCH_RC}" -eq 130 ]]; then
  NOTES="launch stopped by timeout after ${DURATION_SEC}s"
else
  NOTES="launch exited with code ${LAUNCH_RC}"
fi

if grep -Eiq "Failed|ABORTED|CANCELED" "${LOG_DIR}/launch.log"; then
  SUCCESS="false"
elif [[ "$(grep -Ec "Returned to Loading Dock" "${LOG_DIR}/launch.log" || true)" -ge 2 ]]; then
  SUCCESS="true"
fi

python3 "${SCRIPT_DIR}/analyze_rosbag.py" \
  "${FYP_DIR}/results/bags/${RUN_ID}" \
  --mode dual \
  --layout "${LAYOUT}" \
  --repeat "${REPEAT}" \
  --inflation-radius "${INFLATION_RADIUS}" \
  --success "${SUCCESS}" \
  --notes "${NOTES}" \
  --output "${FYP_DIR}/results/csv/${RUN_ID}_metrics.csv"

echo "[run_dual] Metrics: ${FYP_DIR}/results/csv/${RUN_ID}_metrics.csv"
echo "[run_dual] Logs: ${LOG_DIR}"
