#!/usr/bin/env bash
# shellcheck disable=SC2029
set -euo pipefail

echo "=== Gen510: Submit Barrier Grid Jobs ==="

REMOTE_DIR="/tmp/gen510_sql"
LOG_FILE="/tmp/gen510_barrier_grid.jsonl"

# Upload SQL files
echo "--- Uploading SQL files ---"
rsync -az /tmp/gen510_sql/ "${RANGEBAR_CH_HOST}:${REMOTE_DIR}/"

# Read metadata
METADATA=$(ssh "${RANGEBAR_CH_HOST}" "cat ${REMOTE_DIR}/metadata.json")
TEMPLATE_SHA=$(echo "$METADATA" | python3 -c "import sys,json; print(json.load(sys.stdin)['template_sha'])")
GIT_COMMIT=$(echo "$METADATA" | python3 -c "import sys,json; print(json.load(sys.stdin)['git_commit'])")
TEMPLATE_FILE=$(echo "$METADATA" | python3 -c "import sys,json; print(json.load(sys.stdin)['template_file'])")

# Create wrapper script — parses 36-row barrier grid output
ssh "${RANGEBAR_CH_HOST}" 'cat > /tmp/gen510_run_job.sh' << 'WRAPPER'
#!/bin/bash
set -euo pipefail
CONFIG_ID="$1"
SQL_FILE="$2"
LOG_FILE="$3"
TEMPLATE_FILE="$4"
TEMPLATE_SHA="$5"
GIT_COMMIT="$6"

QUERY_START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
START_S=$(date +%s)

OUTPUT=$(clickhouse-client --multiquery < "$SQL_FILE" 2>&1) || {
    END_S=$(date +%s)
    DURATION=$((END_S - START_S))
    QUERY_END=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    ERROR_MSG=$(echo "$OUTPUT" | tr '"' "'" | tr '\n' ' ' | head -c 500)
    LINE="{\"timestamp\":\"${QUERY_END}\",\"generation\":510,\"config_id\":\"${CONFIG_ID}\",\"environment\":{\"symbol\":\"SOLUSDT\",\"threshold_dbps\":500,\"clickhouse_host\":\"$(hostname)\",\"template_file\":\"${TEMPLATE_FILE}\",\"template_sha256\":\"${TEMPLATE_SHA}\",\"git_commit\":\"${GIT_COMMIT}\",\"quantile_method\":\"rolling_1000_signal\"},\"timing\":{\"query_start_utc\":\"${QUERY_START}\",\"query_end_utc\":\"${QUERY_END}\",\"query_duration_s\":${DURATION}},\"results\":null,\"error\":true,\"error_message\":\"${ERROR_MSG}\"}"
    flock "${LOG_FILE}.lock" bash -c "echo '${LINE}' >> ${LOG_FILE}"
    exit 1
}

END_S=$(date +%s)
DURATION=$((END_S - START_S))
QUERY_END=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Parse each data row (skip header line)
echo "$OUTPUT" | tail -n +2 | while IFS=$'\t' read -r cfg tp_mult sl_mult max_bars tp_pct sl_pct rr_ratio filtered_signals tp_count sl_count time_count incomplete_count win_rate profit_factor avg_win avg_loss ev_pct avg_bars kelly; do
    # Handle ClickHouse NULL/nan
    for var in win_rate profit_factor avg_win avg_loss ev_pct avg_bars kelly; do
        eval "val=\$$var"
        case "$val" in
            \\N|nan|inf|-inf|"") eval "$var=null" ;;
        esac
    done

    BARRIER_ID="tp${tp_mult}_sl${sl_mult}_mb${max_bars}"
    LINE="{\"timestamp\":\"${QUERY_END}\",\"generation\":510,\"config_id\":\"${CONFIG_ID}__${BARRIER_ID}\",\"feature_config\":\"${CONFIG_ID}\",\"barrier_config\":\"${BARRIER_ID}\",\"environment\":{\"symbol\":\"SOLUSDT\",\"threshold_dbps\":500,\"clickhouse_host\":\"$(hostname)\",\"template_file\":\"${TEMPLATE_FILE}\",\"template_sha256\":\"${TEMPLATE_SHA}\",\"git_commit\":\"${GIT_COMMIT}\",\"quantile_method\":\"rolling_1000_signal\"},\"timing\":{\"query_start_utc\":\"${QUERY_START}\",\"query_end_utc\":\"${QUERY_END}\",\"query_duration_s\":${DURATION}},\"barrier\":{\"tp_mult\":${tp_mult},\"sl_mult\":${sl_mult},\"max_bars\":${max_bars},\"tp_pct\":${tp_pct},\"sl_pct\":${sl_pct},\"rr_ratio\":${rr_ratio}},\"results\":{\"filtered_signals\":${filtered_signals},\"tp_count\":${tp_count},\"sl_count\":${sl_count},\"time_count\":${time_count},\"incomplete_count\":${incomplete_count},\"win_rate\":${win_rate},\"profit_factor\":${profit_factor},\"avg_win_pct\":${avg_win},\"avg_loss_pct\":${avg_loss},\"expected_value_pct\":${ev_pct},\"avg_bars_held\":${avg_bars},\"kelly_fraction\":${kelly}},\"error\":false}"
    flock "${LOG_FILE}.lock" bash -c "echo '${LINE}' >> ${LOG_FILE}"
done
WRAPPER

ssh "${RANGEBAR_CH_HOST}" "chmod +x /tmp/gen510_run_job.sh"

# Ensure pueue group exists
ssh "${RANGEBAR_CH_HOST}" "pueue group add p1 2>/dev/null || true; pueue parallel 4 -g p1"

# Submit all SQL files
SUBMITTED=0
while read -r SQL_PATH; do
    FILENAME=$(basename "$SQL_PATH" .sql)
    ssh -n "${RANGEBAR_CH_HOST}" "pueue add -g p1 -- /tmp/gen510_run_job.sh '${FILENAME}' '${SQL_PATH}' '${LOG_FILE}' '${TEMPLATE_FILE}' '${TEMPLATE_SHA}' '${GIT_COMMIT}'"
    SUBMITTED=$((SUBMITTED + 1))
done < <(ssh -n "${RANGEBAR_CH_HOST}" "ls ${REMOTE_DIR}/*.sql")

echo "Submitted ${SUBMITTED} jobs (each produces 36 barrier combos)"
echo "Expected: $((SUBMITTED * 36)) total result rows"
echo "Monitor: ssh ${RANGEBAR_CH_HOST} 'pueue status -g p1'"
