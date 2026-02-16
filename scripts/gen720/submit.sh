#!/usr/bin/env bash
# shellcheck disable=SC2029  # Client-side expansion in ssh is intentional
set -euo pipefail

# Gen720: Submit walk-forward barrier optimization queries to BigBlack pueue.
#
# Each SQL query outputs raw per-trade TSV via FORMAT TabSeparatedWithNames.
# One query per (formation × symbol × threshold) combo.
#
# Usage: submit.sh [FORMATION] [SYMBOL] [THRESHOLD]
#   submit.sh                  # Submit ALL 675 combos
#   submit.sh 2down            # Submit all 2down combos (45 = 15 sym × 3 thr)
#   submit.sh 2down SOLUSDT    # Submit 2down SOLUSDT at all thresholds (3)
#   submit.sh 2down SOLUSDT 500 # Submit single combo
#
# GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/28

echo "=== Gen720: Submit WFO Barrier Queries ==="

FILTER_FMT="${1:-}"
FILTER_SYM="${2:-}"
FILTER_THR="${3:-}"

LOCAL_SQL_DIR="/tmp/gen720_sql"
REMOTE_SQL_DIR="/tmp/gen720_sql"
REMOTE_TSV_DIR="/tmp/gen720_tsv"

CH_HOST="${RANGEBAR_CH_HOST:?Set RANGEBAR_CH_HOST}"

if [ ! -d "$LOCAL_SQL_DIR" ]; then
    echo "ERROR: SQL directory not found: ${LOCAL_SQL_DIR}"
    echo "  Run: mise run gen720:generate"
    exit 1
fi

# Build file list with optional filters
FILE_LIST=$(mktemp)
trap 'rm -f "$FILE_LIST"' EXIT

for SQL_FILE in "$LOCAL_SQL_DIR"/*.sql; do
    [ -f "$SQL_FILE" ] || continue
    BASENAME=$(basename "$SQL_FILE" .sql)

    # Parse formation_SYMBOL_THRESHOLD from filename
    # Handle formation names with underscores (e.g., 2up_ng_s_rev_SOLUSDT_500)
    # Strategy: extract threshold (last field) and symbol (second-to-last), rest is formation
    THR="${BASENAME##*_}"
    REST="${BASENAME%_*}"
    SYM="${REST##*_}"
    SUFFIX="_${SYM}"
    FMT="${REST%"$SUFFIX"}"

    # Validate parsed symbol looks like a trading pair
    case "$SYM" in
        *USDT) ;;
        *) continue ;;  # Skip non-matching files (e.g., metadata.json)
    esac

    # Apply filters
    if [ -n "$FILTER_FMT" ] && [ "$FMT" != "$FILTER_FMT" ]; then continue; fi
    if [ -n "$FILTER_SYM" ] && [ "$SYM" != "$FILTER_SYM" ]; then continue; fi
    if [ -n "$FILTER_THR" ] && [ "$THR" != "$FILTER_THR" ]; then continue; fi

    echo "$BASENAME" >> "$FILE_LIST"
done

TOTAL=$(wc -l < "$FILE_LIST" | tr -d ' ')
echo "Queries to submit: ${TOTAL}"

if [ "$TOTAL" -eq 0 ]; then
    echo "No matching queries. Check filters: FMT=${FILTER_FMT:-all} SYM=${FILTER_SYM:-all} THR=${FILTER_THR:-all}"
    exit 0
fi

# Upload SQL files
echo "--- Uploading SQL files ---"
ssh "$CH_HOST" "mkdir -p ${REMOTE_SQL_DIR} ${REMOTE_TSV_DIR}"
rsync -az "${LOCAL_SQL_DIR}/" "${CH_HOST}:${REMOTE_SQL_DIR}/"
echo "  Uploaded to ${CH_HOST}:${REMOTE_SQL_DIR}/"

# Create wrapper script on remote — runs clickhouse-client, saves TSV output
ssh "$CH_HOST" 'cat > /tmp/gen720_run_query.sh' << 'WRAPPER'
#!/bin/bash
SQL_FILE="$1"
TSV_DIR="$2"

BASENAME=$(basename "$SQL_FILE" .sql)
TSV_FILE="${TSV_DIR}/${BASENAME}.tsv"

# Skip if already completed
if [ -f "$TSV_FILE" ] && [ -s "$TSV_FILE" ]; then
    exit 0
fi

OUTPUT=$(clickhouse-client --max_threads=8 --multiquery < "$SQL_FILE" 2>/tmp/gen720_err_${BASENAME}.log)
CH_EXIT=$?

if [ "$CH_EXIT" -ne 0 ]; then
    echo "ERROR: ${BASENAME} (exit ${CH_EXIT})" >&2
    exit 1
fi

echo "$OUTPUT" > "$TSV_FILE"
exit 0
WRAPPER

ssh "$CH_HOST" "chmod +x /tmp/gen720_run_query.sh"

# Ensure pueue group
ssh "$CH_HOST" "\$HOME/.local/bin/pueue group add p1 2>/dev/null || true; \$HOME/.local/bin/pueue parallel 4 -g p1"
ssh "$CH_HOST" "\$HOME/.local/bin/pueue clean -g p1 2>/dev/null || true"

# Check for already-completed TSVs (crash recovery)
DONE_FILE=$(mktemp)
trap 'rm -f "$FILE_LIST" "$DONE_FILE"' EXIT
ssh -n "$CH_HOST" "ls ${REMOTE_TSV_DIR}/*.tsv 2>/dev/null | xargs -I{} basename {} .tsv" > "$DONE_FILE" 2>/dev/null || true
DONE_COUNT=$(wc -l < "$DONE_FILE" | tr -d ' ')
echo "Already completed: ${DONE_COUNT} TSVs"

# Build commands, skipping done
CMD_FILE=$(mktemp)
trap 'rm -f "$FILE_LIST" "$DONE_FILE" "$CMD_FILE"' EXIT

SKIP=0
while IFS= read -r BASENAME; do
    if grep -qx "$BASENAME" "$DONE_FILE" 2>/dev/null; then
        SKIP=$((SKIP + 1))
        continue
    fi
    echo "\$HOME/.local/bin/pueue add -g p1 --label '${BASENAME}' -- /tmp/gen720_run_query.sh '${REMOTE_SQL_DIR}/${BASENAME}.sql' '${REMOTE_TSV_DIR}'" >> "$CMD_FILE"
done < "$FILE_LIST"

TO_SUBMIT=$(wc -l < "$CMD_FILE" | tr -d ' ')
echo "Skipped (already done): ${SKIP}"
echo "Submitting: ${TO_SUBMIT} jobs"

if [ "$TO_SUBMIT" -gt 0 ]; then
    # Upload command file and execute via xargs for parallel submission
    scp "$CMD_FILE" "${CH_HOST}:/tmp/gen720_commands.txt"
    ssh "$CH_HOST" "cat /tmp/gen720_commands.txt | xargs -P16 -I{} bash -c '{}' 2>/dev/null"
    echo "  Submitted ${TO_SUBMIT} jobs to pueue group p1"
fi

echo ""
echo "Monitor: ssh ${CH_HOST} '~/.local/bin/pueue status -g p1'"
echo "Collect: mise run gen720:collect"
