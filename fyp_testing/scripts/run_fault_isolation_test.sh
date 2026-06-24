#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FYP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DUAL_WS="${DUAL_WS:-/home/anaskh007/dual_robot_ws}"

LAYOUT="${1:-1}"
REPEAT="${2:-1}"
DURATION_SEC="${3:-240}"
TARGET_ROBOT="${4:-TB3_1}"
FAULT_TYPE="${5:-nav2}"
FAULT_DELAY_SEC="${6:-95}"
VISUAL_MODE="${7:-gui}"
SURVIVOR_ROBOT=""
KILLED_COUNT=0
TARGET_FAULT_DETECTED=false
SURVIVOR_FINISHED=false

case "${LAYOUT}" in
  1) LAUNCH_FILE="00_bringup.launch.py" ;;
  2) LAUNCH_FILE="10_bringup.launch.py" ;;
  3) LAUNCH_FILE="20_bringup.launch.py" ;;
  4) LAUNCH_FILE="30_bringup.launch.py" ;;
  *) echo "Unknown layout: ${LAYOUT}. Use 1, 2, 3, or 4."; exit 2 ;;
esac

case "${TARGET_ROBOT}" in
  TB3_1|TB3_2) ;;
  *) echo "Unknown target robot: ${TARGET_ROBOT}. Use TB3_1 or TB3_2."; exit 2 ;;
esac

if [[ "${TARGET_ROBOT}" == "TB3_1" ]]; then
  SURVIVOR_ROBOT="TB3_2"
else
  SURVIVOR_ROBOT="TB3_1"
fi

GUI="false"
RVIZ="false"
case "${VISUAL_MODE}" in
  visual|true|1|yes)
    GUI="true"
    RVIZ="true"
    ;;
  gui|gazebo)
    GUI="true"
    ;;
  rviz)
    RVIZ="true"
    ;;
  headless|false|0|no)
    ;;
  *)
    echo "Unknown visual mode: ${VISUAL_MODE}. Use visual, gui, rviz, or headless."
    exit 2
    ;;
esac

RUN_ID="fault_layout${LAYOUT}_r${REPEAT}_${TARGET_ROBOT}_${FAULT_TYPE}_$(date +%Y%m%d_%H%M%S)"
LOG_DIR="${FYP_DIR}/results/logs/${RUN_ID}"
mkdir -p "${LOG_DIR}"

set +u
source "${DUAL_WS}/install/setup.bash"
set -u

stop_process() {
  local pid="${1:-}"
  local label="${2:-process}"
  local grace="${3:-15}"

  if [[ -z "${pid}" ]] || ! kill -0 "${pid}" 2>/dev/null; then
    return 0
  fi

  echo "[fault_test] Stopping ${label} (pid ${pid})"
  kill -INT "-${pid}" 2>/dev/null || kill -INT "${pid}" 2>/dev/null || true

  for _ in $(seq 1 "${grace}"); do
    if ! kill -0 "${pid}" 2>/dev/null; then
      wait "${pid}" 2>/dev/null || true
      return 0
    fi
    sleep 1
  done

  echo "[fault_test] ${label} did not stop; sending SIGTERM"
  kill -TERM "-${pid}" 2>/dev/null || kill -TERM "${pid}" 2>/dev/null || true
  sleep 2
}

cleanup() {
  trap - INT TERM
  stop_process "${LAUNCH_PID:-}" "dual launch" 12
  stop_process "${BAG_PID:-}" "rosbag recorder" 12
}

fault_patterns() {
  case "${FAULT_TYPE}" in
    nav2)
      printf '%s\n' \
        "nav2_bt_navigator/bt_navigator .*__ns:=/${TARGET_ROBOT}" \
        "nav2_controller/controller_server .*__ns:=/${TARGET_ROBOT}" \
        "nav2_planner/planner_server .*__ns:=/${TARGET_ROBOT}"
      ;;
    localization)
      printf '%s\n' \
        "nav2_amcl/amcl .*__ns:=/${TARGET_ROBOT}" \
        "nav2_map_server/map_server .*__ns:=/${TARGET_ROBOT}"
      ;;
    controller)
      printf '%s\n' "nav2_controller/controller_server .*__ns:=/${TARGET_ROBOT}"
      ;;
    *)
      echo "Unknown fault type: ${FAULT_TYPE}. Use nav2, localization, or controller." >&2
      return 2
      ;;
  esac
}

inject_fault() {
  echo "[fault_test] Injecting ${FAULT_TYPE} fault into ${TARGET_ROBOT}"
  KILLED_COUNT=0
  while IFS= read -r pattern; do
    while IFS= read -r pid; do
      [[ -z "${pid}" ]] && continue
      echo "[fault_test] Killing pid ${pid}: ${pattern}"
      kill -TERM "${pid}" 2>/dev/null || true
      KILLED_COUNT=$((KILLED_COUNT + 1))
    done < <(pgrep -f "${pattern}" || true)
  done < <(fault_patterns)

  if [[ "${KILLED_COUNT}" -eq 0 ]]; then
    echo "[fault_test] WARNING: no matching process found for ${TARGET_ROBOT}/${FAULT_TYPE}"
  else
    TARGET_FAULT_DETECTED=true
    echo "[fault_test] Detected fault injection: killed ${KILLED_COUNT} ${TARGET_ROBOT} process(es)"
  fi
}

capture_frames() {
  local label="${1:-post_fault}"
  local frame_dir="${LOG_DIR}/frames_${label}"
  mkdir -p "${frame_dir}"

  echo "[fault_test] Capturing TF frame graph (${label})"
  (
    cd "${frame_dir}"
    timeout 12s ros2 run tf2_tools view_frames > view_frames.log 2>&1 || true
  )

  local latest_pdf
  latest_pdf="$(find "${frame_dir}" -maxdepth 1 -type f -name 'frames*.pdf' | sort | tail -1 || true)"
  if [[ -n "${latest_pdf}" ]]; then
    cp "${latest_pdf}" "${LOG_DIR}/${RUN_ID}_${label}_frames.pdf"
    echo "[fault_test] Frame graph: ${LOG_DIR}/${RUN_ID}_${label}_frames.pdf"
  else
    echo "[fault_test] WARNING: TF frame graph PDF was not generated. Check ${frame_dir}/view_frames.log"
  fi
}

capture_topic_isolation() {
  local out="${LOG_DIR}/${RUN_ID}_post_fault_topic_isolation.txt"
  echo "[fault_test] Capturing post-fault topic/subscriber isolation: ${out}"
  {
    echo "== Post-fault topic list =="
    ros2 topic list | sort | grep -E '^/TB3_[12]/' || true
    echo
    echo "== cmd_vel publisher/subscriber details =="
    for topic in /TB3_1/cmd_vel /TB3_2/cmd_vel /TB3_1/odom /TB3_2/odom /TB3_1/amcl_pose /TB3_2/amcl_pose; do
      echo "--- ${topic}"
      ros2 topic info -v "${topic}" || true
      echo
    done
  } > "${out}" 2>&1
}

log_state_summary() {
  {
    echo "run_id,layout,repeat,target_robot,survivor_robot,fault_type,fault_delay_s,killed_processes,target_fault_detected,survivor_finished"
    echo "${RUN_ID},${LAYOUT},${REPEAT},${TARGET_ROBOT},${SURVIVOR_ROBOT},${FAULT_TYPE},${FAULT_DELAY_SEC},${KILLED_COUNT},${TARGET_FAULT_DETECTED},${SURVIVOR_FINISHED}"
  } > "${FYP_DIR}/results/csv/${RUN_ID}_fault_events.csv"
}

trap 'echo "[fault_test] Interrupted; cleaning up"; cleanup; exit 130' INT TERM

echo "[fault_test] Run ID: ${RUN_ID}"
echo "[fault_test] Layout: ${LAYOUT}, target: ${TARGET_ROBOT}, survivor: ${SURVIVOR_ROBOT}, fault: ${FAULT_TYPE}, delay: ${FAULT_DELAY_SEC}s"
echo "[fault_test] Gazebo GUI: ${GUI}, RViz: ${RVIZ}, duration: ${DURATION_SEC}s"

setsid "${SCRIPT_DIR}/record_bag.sh" "${RUN_ID}" > "${LOG_DIR}/rosbag.log" 2>&1 &
BAG_PID=$!

setsid timeout --signal=INT "${DURATION_SEC}s" ros2 launch dual_robot_nav "${LAUNCH_FILE}" gui:="${GUI}" rviz:="${RVIZ}" > "${LOG_DIR}/launch.log" 2>&1 &
LAUNCH_PID=$!

sleep "${FAULT_DELAY_SEC}"
inject_fault > >(tee "${LOG_DIR}/fault_injection.log") 2>&1
capture_topic_isolation
capture_frames "post_fault"

while kill -0 "${LAUNCH_PID}" 2>/dev/null; do
  if [[ -f "${LOG_DIR}/launch.log" ]]; then
    if grep -Eq "process has died|CRITICAL FAILURE|ABORTED|Failed" "${LOG_DIR}/launch.log"; then
      TARGET_FAULT_DETECTED=true
    fi

    if grep -Fq "[${SURVIVOR_ROBOT}] Returned to Loading Dock." "${LOG_DIR}/launch.log"; then
      SURVIVOR_FINISHED=true
      echo "[fault_test] ${SURVIVOR_ROBOT} returned to Loading Dock after ${TARGET_ROBOT} fault."
      echo "[fault_test] Fault isolation demonstrated; stopping simulation after 5s settle time."
      sleep 5
      stop_process "${LAUNCH_PID}" "dual launch" 15
      break
    fi
  fi
  sleep 2
done

set +e
wait "${LAUNCH_PID}" 2>/dev/null
LAUNCH_RC=$?
set -e

stop_process "${BAG_PID}" "rosbag recorder" 15
trap - INT TERM
log_state_summary

if [[ ! -f "${FYP_DIR}/results/bags/${RUN_ID}/metadata.yaml" ]]; then
  echo "[fault_test] ERROR: rosbag metadata was not created."
  echo "[fault_test] Check: ${LOG_DIR}/rosbag.log"
  exit 1
fi

NOTES="fault injection: ${FAULT_TYPE} killed on ${TARGET_ROBOT}; launch rc ${LAUNCH_RC}"
python3 "${SCRIPT_DIR}/analyze_rosbag.py" \
  "${FYP_DIR}/results/bags/${RUN_ID}" \
  --mode dual \
  --layout "${LAYOUT}" \
  --repeat "${REPEAT}" \
  --inflation-radius "fault_${FAULT_TYPE}" \
  --success "unknown" \
  --notes "${NOTES}" \
  --output "${FYP_DIR}/results/csv/${RUN_ID}_metrics.csv"

python3 "${SCRIPT_DIR}/analyze_fault_isolation.py" \
  "${FYP_DIR}/results/bags/${RUN_ID}" \
  --target-robot "${TARGET_ROBOT}" \
  --fault-time-s "${FAULT_DELAY_SEC}" \
  --layout "${LAYOUT}" \
  --repeat "${REPEAT}" \
  --fault-type "${FAULT_TYPE}" \
  --output "${FYP_DIR}/results/csv/${RUN_ID}_fault_isolation.csv"

echo "[fault_test] Metrics: ${FYP_DIR}/results/csv/${RUN_ID}_metrics.csv"
echo "[fault_test] Fault summary: ${FYP_DIR}/results/csv/${RUN_ID}_fault_isolation.csv"
echo "[fault_test] Fault events: ${FYP_DIR}/results/csv/${RUN_ID}_fault_events.csv"
echo "[fault_test] Logs: ${LOG_DIR}"
echo "[fault_test] Bag: ${FYP_DIR}/results/bags/${RUN_ID}"
if [[ -f "${LOG_DIR}/${RUN_ID}_post_fault_frames.pdf" ]]; then
  echo "[fault_test] Frame graph: ${LOG_DIR}/${RUN_ID}_post_fault_frames.pdf"
fi
if [[ -f "${LOG_DIR}/${RUN_ID}_post_fault_topic_isolation.txt" ]]; then
  echo "[fault_test] Topic isolation snapshot: ${LOG_DIR}/${RUN_ID}_post_fault_topic_isolation.txt"
fi
