#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FYP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

MODE="${1:-dual}"
LAYOUT="${2:-1}"
REPEATS="${3:-5}"
DURATION_SEC="${4:-420}"
VISUAL_MODE="${5:-${FYP_VISUAL:-headless}}"

if [[ "${MODE}" != "dual" && "${MODE}" != "single" ]]; then
  echo "Usage: $0 <dual|single> [layout] [repeats] [duration_sec] [visual|headless]"
  exit 2
fi

if [[ -n "${FYP_RADII:-}" ]]; then
  read -r -a RADII <<< "${FYP_RADII}"
else
  RADII=(0.55 0.40 0.30 0.25 0.20)
fi

for radius in "${RADII[@]}"; do
  echo "[inflation_sweep] Preparing radius ${radius}"
  PARAM_OUTPUT="$(python3 "${SCRIPT_DIR}/make_inflation_params.py" --mode "${MODE}" --radius "${radius}")"
  echo "${PARAM_OUTPUT}" | tee "${FYP_DIR}/results/logs/inflation_${MODE}_${radius}.env"

  for repeat in $(seq 1 "${REPEATS}"); do
    echo "[inflation_sweep] ${MODE} layout=${LAYOUT} repeat=${repeat} radius=${radius}"
    if [[ "${MODE}" == "dual" ]]; then
      OVERLAY="$(echo "${PARAM_OUTPUT}" | awk -F= '/DUAL_OVERLAY=/ {print $2}')"
      FYP_AMENT_PREFIX_PATH="${OVERLAY}" "${SCRIPT_DIR}/run_dual_experiment.sh" "${LAYOUT}" "${repeat}" "${DURATION_SEC}" "${radius}" "${VISUAL_MODE}"
    else
      PARAMS="$(echo "${PARAM_OUTPUT}" | awk -F= '/SINGLE_PARAMS=/ {print $2}')"
      FYP_SINGLE_PARAMS_FILE="${PARAMS}" "${SCRIPT_DIR}/run_single_experiment.sh" "${LAYOUT}" "${repeat}" "${DURATION_SEC}" "${radius}" "${VISUAL_MODE}"
    fi
  done
done

python3 "${SCRIPT_DIR}/aggregate_results.py" \
  --csv-dir "${FYP_DIR}/results/csv" \
  --output-dir "${FYP_DIR}/results/csv"
