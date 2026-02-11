#!/usr/bin/env bash
# shellcheck disable=SC2029  # Client-side expansion in ssh is intentional
set -euo pipefail

# Usage: submit.sh <PATTERN_ID> <SYMBOL> <THRESHOLD>
# Example: submit.sh 2down SOLUSDT 750
# Submits all SQL files for one pattern/asset/threshold combo to pueue on remote ClickHouse.

PATTERN_ID="${1:?Usage: submit.sh <PATTERN_ID> <SYMBOL> <THRESHOLD>}"
SYMBOL="${2:?}"
THRESHOLD="${3:?}"

echo "=== Gen600: Submit ${PATTERN_ID} ${SYMBOL}@${THRESHOLD} ==="

REMOTE_DIR="/tmp/gen600_sql"
ASSET_DIR="${REMOTE_DIR}/${PATTERN_ID}/${SYMBOL}_${THRESHOLD}"
LOG_FILE="/tmp/gen600_${PATTERN_ID}_${SYMBOL}_${THRESHOLD}.jsonl"

# Read metadata
METADATA=$(ssh "${RANGEBAR_CH_HOST}" "cat ${REMOTE_DIR}/metadata.json")
GIT_COMMIT=$(echo "$METADATA" | python3 -c "import sys,json; print(json.load(sys.stdin)['git_commit'])")

# Count total files
TOTAL=$(ssh "${RANGEBAR_CH_HOST}" "ls ${ASSET_DIR}/*.sql 2>/dev/null | wc -l" | tr -d '[:space:]')
echo "Total configs: ${TOTAL}"

# Check for crash recovery — count lines already done (each config produces 3 lines)
DONE_LINES=$(ssh "${RANGEBAR_CH_HOST}" "wc -l < ${LOG_FILE} 2>/dev/null || echo 0" | tr -d '[:space:]')
DONE_CONFIGS=$((DONE_LINES / 3))
echo "Already completed: ${DONE_CONFIGS} configs (${DONE_LINES} lines)"

if [ "$DONE_CONFIGS" -ge "$TOTAL" ]; then
    echo "All jobs already completed for ${PATTERN_ID} ${SYMBOL}@${THRESHOLD}."
    exit 0
fi

# Create the wrapper script on remote host — parses 3-row barrier output into NDJSON
ssh "${RANGEBAR_CH_HOST}" 'cat > /tmp/gen600_run_job.sh' << 'WRAPPER'
#!/bin/bash
set -euo pipefail
SQL_FILE="$1"
LOG_FILE="$2"
SYMBOL="$3"
THRESHOLD="$4"
GIT_COMMIT="$5"

QUERY_START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
START_MS=$(($(date +%s) * 1000))

OUTPUT=$(clickhouse-client --multiquery < "$SQL_FILE" 2>&1) || {
    END_MS=$(($(date +%s) * 1000))
    DURATION_MS=$((END_MS - START_MS))
    SUBMITTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    ERROR_MSG=$(echo "$OUTPUT" | tr '"' "'" | tr '\n' ' ' | head -c 500)
    # Extract config_id from SQL filename
    BASENAME=$(basename "$SQL_FILE" .sql)
    LINE="{\"generation\":600,\"config_id\":\"${BASENAME}__error\",\"feature_config\":\"${BASENAME}\",\"base_pattern\":\"\",\"barrier_profile\":\"\",\"environment\":{\"symbol\":\"${SYMBOL}\",\"threshold_dbps\":${THRESHOLD},\"git_commit\":\"${GIT_COMMIT}\",\"quantile_method\":\"rolling_1000_signal\",\"date_cutoff_ms\":1738713600000,\"warmup_bars\":1000},\"timing\":{\"query_duration_ms\":${DURATION_MS},\"submitted_at\":\"${SUBMITTED_AT}\"},\"skipped\":false,\"error\":true,\"error_message\":\"${ERROR_MSG}\"}"
    flock "${LOG_FILE}.lock" bash -c "echo '${LINE}' >> ${LOG_FILE}"
    exit 1
}

END_MS=$(($(date +%s) * 1000))
DURATION_MS=$((END_MS - START_MS))
SUBMITTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Count data rows (excluding header)
N_DATA=$(echo "$OUTPUT" | tail -n +2 | grep -c . || true)

if [ "$N_DATA" -eq 0 ]; then
    # No output rows — pattern too sparse after filters
    BASENAME=$(basename "$SQL_FILE" .sql)
    LINE="{\"generation\":600,\"config_id\":\"${BASENAME}__skipped\",\"feature_config\":\"${BASENAME}\",\"base_pattern\":\"\",\"barrier_profile\":\"\",\"environment\":{\"symbol\":\"${SYMBOL}\",\"threshold_dbps\":${THRESHOLD},\"git_commit\":\"${GIT_COMMIT}\",\"quantile_method\":\"rolling_1000_signal\",\"date_cutoff_ms\":1738713600000,\"warmup_bars\":1000},\"signal_funnel\":{\"total_bars\":0,\"base_pattern_signals\":0,\"after_feature_filter\":0,\"signal_coverage\":0},\"timing\":{\"query_duration_ms\":${DURATION_MS},\"submitted_at\":\"${SUBMITTED_AT}\"},\"skipped\":true,\"error\":false,\"error_message\":null}"
    flock "${LOG_FILE}.lock" bash -c "echo '${LINE}' >> ${LOG_FILE}"
    exit 0
fi

# Build all 3 NDJSON lines into temp file, then atomic append
TMPOUT=$(mktemp)

echo "$OUTPUT" | tail -n +2 | while IFS=$'\t' read -r config_id base_pattern barrier_profile total_bars base_pattern_signals filtered_signals signal_coverage tp_count sl_count time_count incomplete_count win_rate profit_factor avg_win_pct avg_loss_pct expected_value_pct kelly_fraction avg_bars_held median_exit_bar signal_min_ts_ms signal_max_ts_ms total_return; do

    # Handle ClickHouse NULL/nan/inf
    for var in signal_coverage win_rate profit_factor avg_win_pct avg_loss_pct expected_value_pct kelly_fraction avg_bars_held median_exit_bar total_return; do
        eval "val=\$$var"
        case "$val" in
            \\N|nan|inf|-inf|"") eval "$var=null" ;;
        esac
    done

    # Determine barrier tp/sl/max_bars from barrier_profile
    case "$barrier_profile" in
        inverted)  tp_mult=0.25; sl_mult=0.50; max_bars=100 ;;
        symmetric) tp_mult=0.50; sl_mult=0.50; max_bars=50 ;;
        momentum)  tp_mult=0.75; sl_mult=0.25; max_bars=50 ;;
        *)         tp_mult=0; sl_mult=0; max_bars=0 ;;
    esac

    # Determine skip status
    SKIPPED="false"
    if [ "$filtered_signals" -lt 100 ] 2>/dev/null; then
        SKIPPED="true"
    fi

    echo "{\"generation\":600,\"config_id\":\"${config_id}__${barrier_profile}\",\"feature_config\":\"${config_id}\",\"base_pattern\":\"${base_pattern}\",\"barrier_profile\":\"${barrier_profile}\",\"environment\":{\"symbol\":\"${SYMBOL}\",\"threshold_dbps\":${THRESHOLD},\"git_commit\":\"${GIT_COMMIT}\",\"quantile_method\":\"rolling_1000_signal\",\"date_cutoff_ms\":1738713600000,\"warmup_bars\":1000},\"barrier\":{\"tp_mult\":${tp_mult},\"sl_mult\":${sl_mult},\"max_bars\":${max_bars}},\"signal_funnel\":{\"total_bars\":${total_bars},\"base_pattern_signals\":${base_pattern_signals},\"after_feature_filter\":${filtered_signals},\"signal_coverage\":${signal_coverage}},\"results\":{\"filtered_signals\":${filtered_signals},\"kelly_fraction\":${kelly_fraction},\"profit_factor\":${profit_factor},\"hit_rate\":${win_rate},\"avg_win\":${avg_win_pct},\"avg_loss\":${avg_loss_pct},\"total_return\":${total_return},\"tp_count\":${tp_count},\"sl_count\":${sl_count},\"time_count\":${time_count},\"incomplete_count\":${incomplete_count},\"median_exit_bar\":${median_exit_bar},\"avg_bars_held\":${avg_bars_held},\"signal_min_ts_ms\":${signal_min_ts_ms},\"signal_max_ts_ms\":${signal_max_ts_ms}},\"timing\":{\"query_duration_ms\":${DURATION_MS},\"submitted_at\":\"${SUBMITTED_AT}\"},\"skipped\":${SKIPPED},\"error\":false,\"error_message\":null}" >> "$TMPOUT"
done

# Atomic append of all lines (3 for normal, fewer if sparse)
if [ -s "$TMPOUT" ]; then
    flock "${LOG_FILE}.lock" bash -c "cat '${TMPOUT}' >> '${LOG_FILE}'"
fi
rm -f "$TMPOUT"
WRAPPER

ssh "${RANGEBAR_CH_HOST}" "chmod +x /tmp/gen600_run_job.sh"

# Ensure pueue group exists
ssh "${RANGEBAR_CH_HOST}" "pueue group add p1 2>/dev/null || true; pueue parallel 8 -g p1"

# Get already-done config IDs for crash recovery (extract feature_config from NDJSON, deduplicate)
DONE_IDS=""
if [ "$DONE_LINES" -gt 0 ]; then
    DONE_IDS=$(ssh "${RANGEBAR_CH_HOST}" "jq -r '.feature_config' ${LOG_FILE} 2>/dev/null | sort -u")
fi

# Submit jobs
SUBMITTED=0
while read -r SQL_PATH; do
    FILENAME=$(basename "$SQL_PATH" .sql)

    # Skip if already completed (crash recovery)
    if [ -n "$DONE_IDS" ] && echo "$DONE_IDS" | grep -q "^${FILENAME}$" 2>/dev/null; then
        continue
    fi

    ssh -n "${RANGEBAR_CH_HOST}" "pueue add -g p1 -- /tmp/gen600_run_job.sh '${SQL_PATH}' '${LOG_FILE}' '${SYMBOL}' '${THRESHOLD}' '${GIT_COMMIT}'"
    SUBMITTED=$((SUBMITTED + 1))
done < <(ssh -n "${RANGEBAR_CH_HOST}" "ls ${ASSET_DIR}/*.sql 2>/dev/null")

echo "Submitted ${SUBMITTED} new jobs for ${PATTERN_ID} ${SYMBOL}@${THRESHOLD}"
echo "Each produces 3 result rows (inverted/symmetric/momentum)"
echo "Monitor: ssh ${RANGEBAR_CH_HOST} 'pueue status -g p1'"
