#!/usr/bin/env bash
# shellcheck disable=SC2029  # Client-side expansion in ssh is intentional
set -euo pipefail

# Gen610: Submit barrier grid jobs to BigBlack pueue.
# Copied from: scripts/gen600/submit.sh (two-tier: pueue per unit + xargs per query)
#
# Usage: submit.sh <SYMBOL> <THRESHOLD>
# Example: submit.sh SOLUSDT 750

SYMBOL="${1:?Usage: submit.sh <SYMBOL> <THRESHOLD>}"
THRESHOLD="${2:?}"

echo "=== Gen610: Submit Barrier Grid ${SYMBOL}@${THRESHOLD} ==="

REMOTE_DIR="/tmp/gen610_sql"
ASSET_DIR="${REMOTE_DIR}/${SYMBOL}_${THRESHOLD}"
LOG_FILE="/tmp/gen610_${SYMBOL}_${THRESHOLD}.jsonl"

CH_HOST="${RANGEBAR_CH_HOST:?Set RANGEBAR_CH_HOST}"

# Upload SQL files
echo "--- Uploading SQL files ---"
ssh "${CH_HOST}" "mkdir -p ${ASSET_DIR}"
rsync -az "/tmp/gen610_sql/${SYMBOL}_${THRESHOLD}/" "${CH_HOST}:${ASSET_DIR}/"
rsync -az "/tmp/gen610_sql/metadata.json" "${CH_HOST}:${REMOTE_DIR}/metadata.json"

# Read metadata
METADATA=$(ssh "${CH_HOST}" "cat ${REMOTE_DIR}/metadata.json")
GIT_COMMIT=$(echo "$METADATA" | python3 -c "import sys,json; print(json.load(sys.stdin)['git_commit'])")

# Count total files
TOTAL=$(ssh "${CH_HOST}" "find ${ASSET_DIR} -name '*.sql' | wc -l" | tr -d '[:space:]')
echo "Total configs: ${TOTAL}"

# Check for crash recovery
DONE_LINES=$(ssh "${CH_HOST}" "wc -l < ${LOG_FILE} 2>/dev/null || echo 0" | tr -d '[:space:]')
echo "Already completed: ${DONE_LINES} lines"

# Create wrapper script on remote — parses single-row barrier output into NDJSON
ssh "${CH_HOST}" 'cat > /tmp/gen610_run_job.sh' << 'WRAPPER'
#!/bin/bash
set -euo pipefail
SQL_FILE="$1"
LOG_FILE="$2"
SYMBOL="$3"
THRESHOLD="$4"
GIT_COMMIT="$5"

START_MS=$(($(date +%s) * 1000))

OUTPUT=$(clickhouse-client --multiquery < "$SQL_FILE" 2>&1) || {
    END_MS=$(($(date +%s) * 1000))
    DURATION_MS=$((END_MS - START_MS))
    SUBMITTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    ERROR_MSG=$(echo "$OUTPUT" | tr '"' "'" | tr '\n' ' ' | head -c 500)
    BASENAME=$(basename "$SQL_FILE" .sql)
    LINE="{\"generation\":610,\"config_id\":\"${BASENAME}__error\",\"feature_config\":\"${BASENAME}\",\"base_pattern\":\"2down\",\"barrier_id\":\"\",\"environment\":{\"symbol\":\"${SYMBOL}\",\"threshold_dbps\":${THRESHOLD},\"git_commit\":\"${GIT_COMMIT}\",\"quantile_method\":\"rolling_1000_signal\",\"date_cutoff_ms\":1738713600000,\"warmup_bars\":1000},\"timing\":{\"query_duration_ms\":${DURATION_MS},\"submitted_at\":\"${SUBMITTED_AT}\"},\"skipped\":false,\"error\":true,\"error_message\":\"${ERROR_MSG}\"}"
    flock "${LOG_FILE}.lock" bash -c "echo '${LINE}' >> ${LOG_FILE}"
    exit 1
}

END_MS=$(($(date +%s) * 1000))
DURATION_MS=$((END_MS - START_MS))
SUBMITTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Count data rows (excluding header)
N_DATA=$(echo "$OUTPUT" | tail -n +2 | grep -c . || true)

if [ "$N_DATA" -eq 0 ]; then
    BASENAME=$(basename "$SQL_FILE" .sql)
    LINE="{\"generation\":610,\"config_id\":\"${BASENAME}__skipped\",\"feature_config\":\"${BASENAME}\",\"base_pattern\":\"2down\",\"barrier_id\":\"\",\"environment\":{\"symbol\":\"${SYMBOL}\",\"threshold_dbps\":${THRESHOLD},\"git_commit\":\"${GIT_COMMIT}\",\"quantile_method\":\"rolling_1000_signal\",\"date_cutoff_ms\":1738713600000,\"warmup_bars\":1000},\"signal_funnel\":{\"total_bars\":0,\"base_pattern_signals\":0,\"after_feature_filter\":0,\"signal_coverage\":0},\"timing\":{\"query_duration_ms\":${DURATION_MS},\"submitted_at\":\"${SUBMITTED_AT}\"},\"skipped\":true,\"error\":false,\"error_message\":null}"
    flock "${LOG_FILE}.lock" bash -c "echo '${LINE}' >> ${LOG_FILE}"
    exit 0
fi

# Parse single result row
echo "$OUTPUT" | tail -n +2 | while IFS=$'\t' read -r config_id base_pattern barrier_id tp_mult sl_mult max_bars total_bars base_pattern_signals filtered_signals signal_coverage tp_count sl_count time_count incomplete_count win_rate profit_factor avg_win_pct avg_loss_pct expected_value_pct kelly_fraction avg_bars_held median_exit_bar signal_min_ts_ms signal_max_ts_ms total_return; do

    # Handle ClickHouse NULL/nan/inf
    for var in signal_coverage win_rate profit_factor avg_win_pct avg_loss_pct expected_value_pct kelly_fraction avg_bars_held median_exit_bar total_return; do
        eval "val=\$$var"
        case "$val" in
            \\N|nan|inf|-inf|"") eval "$var=null" ;;
        esac
    done

    LINE="{\"generation\":610,\"config_id\":\"${config_id}__${barrier_id}\",\"feature_config\":\"${config_id}\",\"base_pattern\":\"${base_pattern}\",\"barrier_id\":\"${barrier_id}\",\"environment\":{\"symbol\":\"${SYMBOL}\",\"threshold_dbps\":${THRESHOLD},\"git_commit\":\"${GIT_COMMIT}\",\"quantile_method\":\"rolling_1000_signal\",\"date_cutoff_ms\":1738713600000,\"warmup_bars\":1000},\"barrier\":{\"tp_mult\":${tp_mult},\"sl_mult\":${sl_mult},\"max_bars\":${max_bars}},\"signal_funnel\":{\"total_bars\":${total_bars},\"base_pattern_signals\":${base_pattern_signals},\"after_feature_filter\":${filtered_signals},\"signal_coverage\":${signal_coverage}},\"results\":{\"filtered_signals\":${filtered_signals},\"kelly_fraction\":${kelly_fraction},\"profit_factor\":${profit_factor},\"hit_rate\":${win_rate},\"avg_win\":${avg_win_pct},\"avg_loss\":${avg_loss_pct},\"total_return\":${total_return},\"tp_count\":${tp_count},\"sl_count\":${sl_count},\"time_count\":${time_count},\"incomplete_count\":${incomplete_count},\"median_exit_bar\":${median_exit_bar},\"avg_bars_held\":${avg_bars_held},\"signal_min_ts_ms\":${signal_min_ts_ms},\"signal_max_ts_ms\":${signal_max_ts_ms}},\"timing\":{\"query_duration_ms\":${DURATION_MS},\"submitted_at\":\"${SUBMITTED_AT}\"},\"skipped\":false,\"error\":false,\"error_message\":null}"
    flock "${LOG_FILE}.lock" bash -c "echo '${LINE}' >> ${LOG_FILE}"
done
WRAPPER

ssh "${CH_HOST}" "chmod +x /tmp/gen610_run_job.sh"

# Ensure pueue group exists with 16 parallel slots
ssh "${CH_HOST}" "\$HOME/.local/bin/pueue group add p1 2>/dev/null || true; \$HOME/.local/bin/pueue parallel 16 -g p1"

# Clean pueue state before bulk submission
ssh "${CH_HOST}" "\$HOME/.local/bin/pueue clean -g p1 2>/dev/null || true"

# Build skip-done set if crash recovery
SKIP_FILE="/tmp/gen610_done_${SYMBOL}_${THRESHOLD}.txt"
if [ "$DONE_LINES" -gt 0 ]; then
    ssh "${CH_HOST}" "python3 -c \"
import json
seen = set()
for line in open('${LOG_FILE}'):
    try:
        d = json.loads(line)
        fc = d.get('feature_config','')
        bi = d.get('barrier_id','')
        if fc and bi: seen.add(fc + '__' + bi)
    except: pass
for s in sorted(seen): print(s)
\" > ${SKIP_FILE}"
    SKIP_COUNT=$(ssh "${CH_HOST}" "wc -l < ${SKIP_FILE}" | tr -d '[:space:]')
    echo "Skip-done set: ${SKIP_COUNT} configs"
else
    ssh "${CH_HOST}" "touch ${SKIP_FILE}"
fi

# Submit via xargs -P16 for parallel submission (two-tier pattern)
echo "--- Submitting jobs ---"
ssh "${CH_HOST}" "
find ${ASSET_DIR} -name '*.sql' | while read -r SQL_PATH; do
    BASENAME=\$(basename \"\$SQL_PATH\" .sql)
    if grep -qx \"\$BASENAME\" ${SKIP_FILE} 2>/dev/null; then
        continue
    fi
    echo \"\\\$HOME/.local/bin/pueue add -g p1 -- /tmp/gen610_run_job.sh '\${SQL_PATH}' '${LOG_FILE}' '${SYMBOL}' '${THRESHOLD}' '${GIT_COMMIT}'\"
done > /tmp/gen610_commands_${SYMBOL}_${THRESHOLD}.txt
"

CMD_COUNT=$(ssh "${CH_HOST}" "wc -l < /tmp/gen610_commands_${SYMBOL}_${THRESHOLD}.txt" | tr -d '[:space:]')
echo "Commands to submit: ${CMD_COUNT}"

if [ "$CMD_COUNT" -gt 0 ]; then
    ssh "${CH_HOST}" "cat /tmp/gen610_commands_${SYMBOL}_${THRESHOLD}.txt | xargs -P16 -I{} bash -c '{}' 2>/dev/null"
    echo "Submitted ${CMD_COUNT} jobs for ${SYMBOL}@${THRESHOLD}"
else
    echo "All jobs already completed."
fi

echo "Monitor: ssh ${CH_HOST} '~/.local/bin/pueue status -g p1'"
