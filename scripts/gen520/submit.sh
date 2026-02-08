#!/usr/bin/env bash
# shellcheck disable=SC2029
set -euo pipefail

# Usage: gen520_submit.sh <THRESHOLD>
# Example: gen520_submit.sh 250

THRESHOLD="${1:?Usage: gen520_submit.sh <THRESHOLD>}"

echo "=== Gen520: Submit SOLUSDT@${THRESHOLD} 2-Feature Jobs ==="

REMOTE_DIR="/tmp/gen520_sql"
ASSET_DIR="${REMOTE_DIR}/SOLUSDT_${THRESHOLD}"
LOG_FILE="/tmp/gen520_SOLUSDT_${THRESHOLD}.jsonl"

# Read metadata
METADATA=$(ssh "${RANGEBAR_CH_HOST}" "cat ${REMOTE_DIR}/metadata.json")
TEMPLATE_SHA=$(echo "$METADATA" | python3 -c "import sys,json; print(json.load(sys.stdin)['template_sha'])")
GIT_COMMIT=$(echo "$METADATA" | python3 -c "import sys,json; print(json.load(sys.stdin)['git_commit'])")
TEMPLATE_FILE=$(echo "$METADATA" | python3 -c "import sys,json; print(json.load(sys.stdin)['template_file'])")

TOTAL=$(ssh "${RANGEBAR_CH_HOST}" "ls ${ASSET_DIR}/*.sql 2>/dev/null | wc -l" | tr -d '[:space:]')
echo "Total configs: ${TOTAL}"

DONE=$(ssh "${RANGEBAR_CH_HOST}" "wc -l < ${LOG_FILE} 2>/dev/null || echo 0" | tr -d '[:space:]')
echo "Already completed: ${DONE}"

if [ "$DONE" -ge "$TOTAL" ]; then
    echo "All jobs already completed for SOLUSDT@${THRESHOLD}."
    exit 0
fi

# Reuse Gen500 wrapper (same NDJSON schema, just different generation number)
ssh "${RANGEBAR_CH_HOST}" 'cat > /tmp/gen520_run_job.sh' << 'WRAPPER'
#!/bin/bash
set -euo pipefail
CONFIG_ID="$1"
SQL_FILE="$2"
LOG_FILE="$3"
SYMBOL="$4"
THRESHOLD="$5"
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
    LINE="{\"timestamp\":\"${QUERY_END}\",\"generation\":520,\"config_id\":\"${CONFIG_ID}\",\"environment\":{\"symbol\":\"${SYMBOL}\",\"threshold_dbps\":${THRESHOLD},\"clickhouse_host\":\"$(hostname)\",\"template_file\":\"${TEMPLATE_FILE}\",\"template_sha256\":\"${TEMPLATE_SHA}\",\"git_commit\":\"${GIT_COMMIT}\",\"quantile_method\":\"rolling_1000_signal\"},\"timing\":{\"query_start_utc\":\"${QUERY_START}\",\"query_end_utc\":\"${QUERY_END}\",\"query_duration_s\":${DURATION}},\"results\":null,\"skipped\":false,\"error\":true,\"error_message\":\"${ERROR_MSG}\"}"
    flock "${LOG_FILE}.lock" bash -c "echo '${LINE}' >> ${LOG_FILE}"
    exit 1
}

END_S=$(date +%s)
DURATION=$((END_S - START_S))
QUERY_END=$(date -u +%Y-%m-%dT%H:%M:%SZ)

DATA_LINE=$(echo "$OUTPUT" | tail -n 1)

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

for var in WIN_RATE PROFIT_FACTOR AVG_WIN AVG_LOSS EV_PCT AVG_BARS KELLY; do
    eval "val=\$$var"
    if [ "$val" = '\N' ] || [ -z "$val" ]; then eval "$var=null"; fi
    if [ "$val" = "nan" ] || [ "$val" = "inf" ] || [ "$val" = "-inf" ]; then eval "$var=null"; fi
done

SKIPPED="false"
SKIP_REASON="null"
if [ "$FILTERED_SIGNALS" -lt 100 ] 2>/dev/null; then
    SKIPPED="true"
    SKIP_REASON="\"<100 signals (${FILTERED_SIGNALS})\""
fi

LINE="{\"timestamp\":\"${QUERY_END}\",\"generation\":520,\"config_id\":\"${CONFIG_ID}\",\"environment\":{\"symbol\":\"${SYMBOL}\",\"threshold_dbps\":${THRESHOLD},\"clickhouse_host\":\"$(hostname)\",\"template_file\":\"${TEMPLATE_FILE}\",\"template_sha256\":\"${TEMPLATE_SHA}\",\"git_commit\":\"${GIT_COMMIT}\",\"quantile_method\":\"rolling_1000_signal\"},\"timing\":{\"query_start_utc\":\"${QUERY_START}\",\"query_end_utc\":\"${QUERY_END}\",\"query_duration_s\":${DURATION}},\"results\":{\"filtered_signals\":${FILTERED_SIGNALS},\"tp_count\":${TP_COUNT},\"sl_count\":${SL_COUNT},\"time_count\":${TIME_COUNT},\"incomplete_count\":${INCOMPLETE_COUNT},\"win_rate\":${WIN_RATE},\"profit_factor\":${PROFIT_FACTOR},\"avg_win_pct\":${AVG_WIN},\"avg_loss_pct\":${AVG_LOSS},\"expected_value_pct\":${EV_PCT},\"avg_bars_held\":${AVG_BARS},\"kelly_fraction\":${KELLY}},\"skipped\":${SKIPPED},\"skip_reason\":${SKIP_REASON},\"error\":false,\"error_message\":null}"

flock "${LOG_FILE}.lock" bash -c "echo '${LINE}' >> ${LOG_FILE}"
WRAPPER

ssh "${RANGEBAR_CH_HOST}" "chmod +x /tmp/gen520_run_job.sh"
ssh "${RANGEBAR_CH_HOST}" "pueue group add p1 2>/dev/null || true; pueue parallel 4 -g p1"

DONE_IDS=""
if [ "$DONE" -gt 0 ]; then
    DONE_IDS=$(ssh "${RANGEBAR_CH_HOST}" "jq -r '.config_id' ${LOG_FILE} 2>/dev/null" | sort)
fi

SUBMITTED=0
while read -r SQL_PATH; do
    FILENAME=$(basename "$SQL_PATH" .sql)
    if [ -n "$DONE_IDS" ] && echo "$DONE_IDS" | grep -q "^${FILENAME}$" 2>/dev/null; then
        continue
    fi
    ssh -n "${RANGEBAR_CH_HOST}" "pueue add -g p1 -- /tmp/gen520_run_job.sh '${FILENAME}' '${SQL_PATH}' '${LOG_FILE}' 'SOLUSDT' '${THRESHOLD}' '${TEMPLATE_FILE}' '${TEMPLATE_SHA}' '${GIT_COMMIT}'"
    SUBMITTED=$((SUBMITTED + 1))
done < <(ssh -n "${RANGEBAR_CH_HOST}" "ls ${ASSET_DIR}/*.sql")

echo "Submitted ${SUBMITTED} jobs for SOLUSDT@${THRESHOLD}"
echo "Monitor: ssh ${RANGEBAR_CH_HOST} 'pueue status -g p1'"
