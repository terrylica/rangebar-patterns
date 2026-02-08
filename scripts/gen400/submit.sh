#!/usr/bin/env bash
# shellcheck disable=SC2029  # Client-side expansion in ssh is intentional throughout
set -euo pipefail

# Usage: gen400_submit.sh <phase> <n_features> <subfolder>
# Example: gen400_submit.sh 1 2 2f

PHASE="${1:?Usage: gen400_submit.sh <phase> <n_features> <subfolder>}"
N_FEATURES="${2:?}"
SUBFOLDER="${3:?}"

echo "=== Gen400: Submit ${N_FEATURES}-Feature Jobs to Pueue ==="

REMOTE_DIR="/tmp/gen400_sql"
LOG_FILE="/tmp/gen400_${N_FEATURES}feature.jsonl"
TEMPLATE_FILE="sql/gen400_${N_FEATURES}feature_template.sql"

# Read template SHA and git commit
TEMPLATE_SHA=$(ssh "${RANGEBAR_CH_HOST}" "cat ${REMOTE_DIR}/template_shas.json" | python3 -c "import sys,json; print(json.load(sys.stdin)['${SUBFOLDER}'])")
GIT_COMMIT=$(ssh "${RANGEBAR_CH_HOST}" "cat ${REMOTE_DIR}/git_commit.txt")

# Count total files
TOTAL=$(ssh "${RANGEBAR_CH_HOST}" "ls ${REMOTE_DIR}/${SUBFOLDER}/*.sql 2>/dev/null | wc -l" | tr -d '[:space:]')
echo "Total configs: ${TOTAL}"

# Check for crash recovery
DONE=$(ssh "${RANGEBAR_CH_HOST}" "wc -l < ${LOG_FILE} 2>/dev/null || echo 0" | tr -d '[:space:]')
echo "Already completed: ${DONE}"

if [ "$DONE" -ge "$TOTAL" ]; then
    echo "All jobs already completed. Use gen400:collect to retrieve results."
    exit 0
fi

# Create the wrapper script on remote host
ssh "${RANGEBAR_CH_HOST}" 'cat > /tmp/gen400_run_job.sh' << 'WRAPPER'
#!/bin/bash
set -euo pipefail
CONFIG_ID="$1"
SQL_FILE="$2"
LOG_FILE="$3"
PHASE="$4"
N_FEATURES="$5"
TEMPLATE_FILE="$6"
TEMPLATE_SHA="$7"
GIT_COMMIT="$8"

QUERY_START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
START_S=$(date +%s)

OUTPUT=$(clickhouse-client --multiquery < "$SQL_FILE" 2>&1) || {
    END_S=$(date +%s)
    DURATION=$((END_S - START_S))
    QUERY_END=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    ERROR_MSG=$(echo "$OUTPUT" | tr '"' "'" | tr '\n' ' ' | head -c 500)
    LINE="{\"timestamp\":\"${QUERY_END}\",\"generation\":400,\"phase\":${PHASE},\"n_features\":${N_FEATURES},\"config_id\":\"${CONFIG_ID}\",\"environment\":{\"symbol\":\"SOLUSDT\",\"threshold_dbps\":500,\"clickhouse_host\":\"$(hostname)\",\"template_file\":\"${TEMPLATE_FILE}\",\"template_sha256\":\"${TEMPLATE_SHA}\",\"git_commit\":\"${GIT_COMMIT}\",\"quantile_method\":\"rolling_1000_signal\"},\"timing\":{\"query_start_utc\":\"${QUERY_START}\",\"query_end_utc\":\"${QUERY_END}\",\"query_duration_s\":${DURATION}},\"results\":null,\"raw_output\":\"\",\"skipped\":false,\"error\":true,\"error_message\":\"${ERROR_MSG}\"}"
    flock "${LOG_FILE}.lock" bash -c "echo '${LINE}' >> ${LOG_FILE}"
    exit 1
}

END_S=$(date +%s)
DURATION=$((END_S - START_S))
QUERY_END=$(date -u +%Y-%m-%dT%H:%M:%SZ)

DATA_LINE=$(echo "$OUTPUT" | tail -n 1)
RAW_OUTPUT=$(echo "$DATA_LINE" | tr '"' "'" | tr '	' '|')

FILTERED_SIGNALS=$(echo "$DATA_LINE" | cut -f2)
TP_COUNT=$(echo "$DATA_LINE" | cut -f3)
SL_COUNT=$(echo "$DATA_LINE" | cut -f4)
TIME_COUNT=$(echo "$DATA_LINE" | cut -f5)
INCOMPLETE_COUNT=$(echo "$DATA_LINE" | cut -f6)
WIN_RATE=$(echo "$DATA_LINE" | cut -f7)
PROFIT_FACTOR=$(echo "$DATA_LINE" | cut -f8)
AVG_WIN=$(echo "$DATA_LINE" | cut -f9)
AVG_LOSS=$(echo "$DATA_LINE" | cut -f10)
EV_PCT=$(echo "$DATA_LINE" | cut -f11)
AVG_BARS=$(echo "$DATA_LINE" | cut -f12)
KELLY=$(echo "$DATA_LINE" | cut -f13)

FILTERED_SIGNALS=${FILTERED_SIGNALS:-0}
TP_COUNT=${TP_COUNT:-0}
SL_COUNT=${SL_COUNT:-0}
TIME_COUNT=${TIME_COUNT:-0}
INCOMPLETE_COUNT=${INCOMPLETE_COUNT:-0}
WIN_RATE=${WIN_RATE:-null}
PROFIT_FACTOR=${PROFIT_FACTOR:-null}
AVG_WIN=${AVG_WIN:-null}
AVG_LOSS=${AVG_LOSS:-null}
EV_PCT=${EV_PCT:-null}
AVG_BARS=${AVG_BARS:-null}
KELLY=${KELLY:-null}

# Handle ClickHouse NULL output
for var in WIN_RATE PROFIT_FACTOR AVG_WIN AVG_LOSS EV_PCT AVG_BARS KELLY; do
    eval "val=\$$var"
    if [ "$val" = '\N' ] || [ -z "$val" ]; then
        eval "$var=null"
    fi
done

SKIPPED="false"
SKIP_REASON="null"
if [ "$FILTERED_SIGNALS" -lt 100 ] 2>/dev/null; then
    SKIPPED="true"
    SKIP_REASON="\"<100 signals (${FILTERED_SIGNALS})\""
fi

LINE="{\"timestamp\":\"${QUERY_END}\",\"generation\":400,\"phase\":${PHASE},\"n_features\":${N_FEATURES},\"config_id\":\"${CONFIG_ID}\",\"environment\":{\"symbol\":\"SOLUSDT\",\"threshold_dbps\":500,\"clickhouse_host\":\"$(hostname)\",\"template_file\":\"${TEMPLATE_FILE}\",\"template_sha256\":\"${TEMPLATE_SHA}\",\"git_commit\":\"${GIT_COMMIT}\",\"quantile_method\":\"rolling_1000_signal\"},\"timing\":{\"query_start_utc\":\"${QUERY_START}\",\"query_end_utc\":\"${QUERY_END}\",\"query_duration_s\":${DURATION}},\"results\":{\"filtered_signals\":${FILTERED_SIGNALS},\"tp_count\":${TP_COUNT},\"sl_count\":${SL_COUNT},\"time_count\":${TIME_COUNT},\"incomplete_count\":${INCOMPLETE_COUNT},\"win_rate\":${WIN_RATE},\"profit_factor\":${PROFIT_FACTOR},\"avg_win_pct\":${AVG_WIN},\"avg_loss_pct\":${AVG_LOSS},\"expected_value_pct\":${EV_PCT},\"avg_bars_held\":${AVG_BARS},\"kelly_fraction\":${KELLY}},\"raw_output\":\"${RAW_OUTPUT}\",\"skipped\":${SKIPPED},\"skip_reason\":${SKIP_REASON},\"error\":false,\"error_message\":null}"

flock "${LOG_FILE}.lock" bash -c "echo '${LINE}' >> ${LOG_FILE}"
WRAPPER

ssh "${RANGEBAR_CH_HOST}" "chmod +x /tmp/gen400_run_job.sh"

# Ensure pueue group exists
ssh "${RANGEBAR_CH_HOST}" "pueue group add p1 2>/dev/null || true; pueue parallel 4 -g p1"

# Get list of already-completed config IDs for crash recovery
DONE_IDS=""
if [ "$DONE" -gt 0 ]; then
    DONE_IDS=$(ssh "${RANGEBAR_CH_HOST}" "jq -r '.config_id' ${LOG_FILE} 2>/dev/null" | sort)
fi

# Submit jobs
SUBMITTED=0
while read -r SQL_PATH; do
    FILENAME=$(basename "$SQL_PATH" .sql)

    # Skip if already completed (crash recovery)
    if [ -n "$DONE_IDS" ] && echo "$DONE_IDS" | grep -q "^${FILENAME}$" 2>/dev/null; then
        continue
    fi

    ssh -n "${RANGEBAR_CH_HOST}" "pueue add -g p1 -- /tmp/gen400_run_job.sh '${FILENAME}' '${SQL_PATH}' '${LOG_FILE}' '${PHASE}' '${N_FEATURES}' '${TEMPLATE_FILE}' '${TEMPLATE_SHA}' '${GIT_COMMIT}'"
    SUBMITTED=$((SUBMITTED + 1))
done < <(ssh -n "${RANGEBAR_CH_HOST}" "ls ${REMOTE_DIR}/${SUBFOLDER}/*.sql")

echo "Submitted ${SUBMITTED} new jobs to pueue group p1"
echo "Monitor: ssh ${RANGEBAR_CH_HOST} 'pueue status -g p1'"
