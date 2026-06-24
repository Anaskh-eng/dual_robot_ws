#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FYP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

LAYOUTS_ARG="${1:-1,4}"
REPEATS="${2:-5}"
DURATION_SEC="${3:-300}"
VISUAL_MODE="${4:-gui}"
INFLATION_RADIUS="${FYP_CONTROLLER_INFLATION:-0.40}"

IFS=',' read -r -a LAYOUTS <<< "${LAYOUTS_ARG}"

for layout in "${LAYOUTS[@]}"; do
  case "${layout}" in
    1|2|3|4) ;;
    *) echo "Unknown layout: ${layout}. Use a comma-separated list such as 1,4."; exit 2 ;;
  esac
done

declare -A OVERLAYS
for controller in rpp dwb; do
  echo "[controller_comparison] Preparing ${controller} overlay at inflation ${INFLATION_RADIUS} m"
  output="$(python3 "${SCRIPT_DIR}/make_controller_overlay.py" \
    --controller "${controller}" \
    --inflation-radius "${INFLATION_RADIUS}")"
  echo "${output}" | tee "${FYP_DIR}/results/logs/controller_${controller}.env"
  OVERLAYS["${controller}"]="$(echo "${output}" | awk -F= '/DUAL_OVERLAY=/ {print $2}')"
done

for layout in "${LAYOUTS[@]}"; do
  for repeat in $(seq 1 "${REPEATS}"); do
    if (( repeat % 2 == 1 )); then
      CONTROLLERS=(rpp dwb)
    else
      CONTROLLERS=(dwb rpp)
    fi

    for controller in "${CONTROLLERS[@]}"; do
      echo "[controller_comparison] layout=${layout} repeat=${repeat} controller=${controller}"
      FYP_AMENT_PREFIX_PATH="${OVERLAYS[${controller}]}" \
        "${SCRIPT_DIR}/run_dual_experiment.sh" \
        "${layout}" "${repeat}" "${DURATION_SEC}" "controller_${controller}" "${VISUAL_MODE}"
    done
  done
done

python3 "${SCRIPT_DIR}/aggregate_controller_comparison.py" \
  --master "${FYP_DIR}/results/csv/navigation_metrics.csv" \
  --output-dir "${FYP_DIR}/results/csv" \
  --plots-dir "${FYP_DIR}/results/plots"

