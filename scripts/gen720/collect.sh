#!/usr/bin/env bash
# shellcheck disable=SC2029  # Client-side expansion in ssh is intentional
set -euo pipefail

# Gen720: Collect TSV results from BigBlack.
#
# Downloads /tmp/gen720_tsv/*.tsv → results/eval/gen720/raw/
# Validates: no empty files, row counts logged.
#
# Usage: collect.sh [FORMATION]
#   collect.sh           # Collect ALL TSVs
#   collect.sh 2down     # Collect only 2down_*.tsv files
#
# GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/28

echo "=== Gen720: Collect WFO Barrier Results ==="

FILTER_FMT="${1:-}"
LOCAL_DIR="results/eval/gen720/raw"
REMOTE_DIR="/tmp/gen720_tsv"

CH_HOST="${RANGEBAR_CH_HOST:?Set RANGEBAR_CH_HOST}"

mkdir -p "$LOCAL_DIR"

# List available TSVs on remote
REMOTE_LIST=$(mktemp)
trap 'rm -f "$REMOTE_LIST"' EXIT
ssh -n "$CH_HOST" "ls ${REMOTE_DIR}/*.tsv 2>/dev/null | xargs -I{} basename {}" > "$REMOTE_LIST" 2>/dev/null || true

AVAILABLE=$(wc -l < "$REMOTE_LIST" | tr -d ' ')
echo "Available TSVs on BigBlack: ${AVAILABLE}"

if [ "$AVAILABLE" -eq 0 ]; then
    echo "No TSV files found at ${CH_HOST}:${REMOTE_DIR}/"
    exit 0
fi

# Apply formation filter
if [ -n "$FILTER_FMT" ]; then
    FILTERED=$(mktemp)
    trap 'rm -f "$REMOTE_LIST" "$FILTERED"' EXIT
    grep "^${FILTER_FMT}_" "$REMOTE_LIST" > "$FILTERED" || true
    mv "$FILTERED" "$REMOTE_LIST"
    AVAILABLE=$(wc -l < "$REMOTE_LIST" | tr -d ' ')
    echo "After filter '${FILTER_FMT}': ${AVAILABLE} TSVs"
fi

# Download via rsync (efficient for large file sets)
echo "--- Downloading TSVs ---"
if [ -n "$FILTER_FMT" ]; then
    # Selective download: build include list
    INCLUDE_FILE=$(mktemp)
    trap 'rm -f "$REMOTE_LIST" "$INCLUDE_FILE"' EXIT
    while IFS= read -r TSV_NAME; do
        echo "$TSV_NAME" >> "$INCLUDE_FILE"
    done < "$REMOTE_LIST"
    rsync -az --files-from="$INCLUDE_FILE" "${CH_HOST}:${REMOTE_DIR}/" "$LOCAL_DIR/"
else
    # Full download
    rsync -az --include='*.tsv' --exclude='*' "${CH_HOST}:${REMOTE_DIR}/" "$LOCAL_DIR/"
fi

# Validate downloaded files
echo "--- Validating TSVs ---"
TOTAL=0
EMPTY=0
TOTAL_ROWS=0

for TSV_FILE in "$LOCAL_DIR"/*.tsv; do
    [ -f "$TSV_FILE" ] || continue
    TOTAL=$((TOTAL + 1))
    BASENAME=$(basename "$TSV_FILE")

    # Check for empty files
    if [ ! -s "$TSV_FILE" ]; then
        echo "  WARNING: Empty file: ${BASENAME}"
        EMPTY=$((EMPTY + 1))
        continue
    fi

    # Count data rows (subtract 1 for header)
    LINE_COUNT=$(wc -l < "$TSV_FILE" | tr -d ' ')
    DATA_ROWS=$((LINE_COUNT - 1))
    TOTAL_ROWS=$((TOTAL_ROWS + DATA_ROWS))
done

echo ""
echo "=== Collection Summary ==="
echo "  Downloaded: ${TOTAL} TSV files"
echo "  Empty:      ${EMPTY}"
echo "  Total rows: ${TOTAL_ROWS}"
echo "  Location:   ${LOCAL_DIR}/"

if [ "$EMPTY" -gt 0 ]; then
    echo ""
    echo "WARNING: ${EMPTY} empty file(s) detected. Check BigBlack logs for errors."
fi
