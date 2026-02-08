#!/usr/bin/env bash
# shellcheck disable=SC2029  # Client-side expansion in ssh is intentional
set -euo pipefail

echo "=== Gen400: Status ==="
echo ""

echo "--- Pueue Queue (p1 group) ---"
ssh "${RANGEBAR_CH_HOST}" "pueue status -g p1" 2>/dev/null || echo "(no pueue jobs)"

echo ""
echo "--- Result Counts ---"
for phase in 2feature 3feature 4feature; do
    FILE="/tmp/gen400_${phase}.jsonl"
    TOTAL=$(ssh "${RANGEBAR_CH_HOST}" "wc -l < ${FILE} 2>/dev/null || echo 0" | tr -d '[:space:]')
    ERRORS=$(ssh "${RANGEBAR_CH_HOST}" "grep -c '\"error\":true' ${FILE} 2>/dev/null || echo 0" | tr -d '[:space:]')
    echo "  ${phase}: ${TOTAL} results (${ERRORS} errors)"
done

echo ""
echo "--- Positive Kelly Counts ---"
for phase in 2feature 3feature 4feature; do
    FILE="/tmp/gen400_${phase}.jsonl"
    POS=$(ssh "${RANGEBAR_CH_HOST}" "jq -r 'select(.error != true and .skipped != true and .results.kelly_fraction > 0) | .config_id' ${FILE} 2>/dev/null | wc -l" | tr -d '[:space:]')
    echo "  ${phase}: ${POS} positive Kelly"
done
