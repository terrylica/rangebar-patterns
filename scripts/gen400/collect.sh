#!/usr/bin/env bash
set -euo pipefail

echo "=== Gen400: Collecting Results ==="
mkdir -p logs/gen400

for phase in 2feature 3feature 4feature; do
    REMOTE="/tmp/gen400_${phase}.jsonl"
    LOCAL="logs/gen400/${phase}.jsonl"
    echo "  Downloading ${phase}..."
    scp "${RANGEBAR_CH_HOST}:${REMOTE}" "${LOCAL}" 2>/dev/null || echo "  (not found: ${phase})"
done

echo ""
echo "--- Local Result Counts ---"
for phase in 2feature 3feature 4feature; do
    FILE="logs/gen400/${phase}.jsonl"
    if [ -f "$FILE" ]; then
        TOTAL=$(wc -l < "$FILE" | tr -d '[:space:]')
        ERRORS=$(grep -c '"error":true' "$FILE" 2>/dev/null || echo 0)
        echo "  ${phase}: ${TOTAL} results (${ERRORS} errors)"
    else
        echo "  ${phase}: (not collected yet)"
    fi
done
