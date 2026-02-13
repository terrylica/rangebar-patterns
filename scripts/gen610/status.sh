#!/usr/bin/env bash
# shellcheck disable=SC2029
set -euo pipefail

echo "=== Gen610: Barrier Grid Sweep Status ==="
echo ""

# Pueue status
echo "--- Pueue Group p1 ---"
ssh "${RANGEBAR_CH_HOST}" "pueue status -g p1 2>/dev/null | tail -5" || echo "  (pueue not running)"
echo ""

# 5 assets x 2 thresholds
ASSETS=(
    "BTCUSDT|750"
    "BTCUSDT|1000"
    "ETHUSDT|750"
    "ETHUSDT|1000"
    "SOLUSDT|750"
    "SOLUSDT|1000"
    "BNBUSDT|750"
    "BNBUSDT|1000"
    "XRPUSDT|750"
    "XRPUSDT|1000"
)

# Expected per asset: 20 configs x 24 barriers = 480 lines
# (some configs may produce skipped lines instead of 1 per barrier)
EXPECTED_LINES_PER_ASSET=480

echo "--- Results Per Asset ---"
printf "  %-14s %8s %8s %8s\n" "Asset" "Lines" "Errors" "Expected"
echo "  -----------------------------------------------"

TOTAL_LINES=0
TOTAL_ERRS=0
TOTAL_EXPECTED=0

for asset_entry in "${ASSETS[@]}"; do
    IFS='|' read -r SYMBOL THRESHOLD <<< "$asset_entry"
    LOG="/tmp/gen610_${SYMBOL}_${THRESHOLD}.jsonl"
    LINES=$(ssh -n "${RANGEBAR_CH_HOST}" "wc -l < ${LOG} 2>/dev/null || echo 0" | tr -d '[:space:]')
    ERRS=$(ssh -n "${RANGEBAR_CH_HOST}" "grep -c '\"error\":true' ${LOG} 2>/dev/null || echo 0" | tr -d '[:space:]')

    if [ "$LINES" -gt 0 ]; then
        printf "  %-14s %8s %8s %8s\n" "${SYMBOL}@${THRESHOLD}" "$LINES" "$ERRS" "$EXPECTED_LINES_PER_ASSET"
    fi

    TOTAL_LINES=$((TOTAL_LINES + LINES))
    TOTAL_ERRS=$((TOTAL_ERRS + ERRS))
    TOTAL_EXPECTED=$((TOTAL_EXPECTED + EXPECTED_LINES_PER_ASSET))
done

echo "  -----------------------------------------------"
printf "  %-14s %8s %8s %8s\n" "TOTAL" "$TOTAL_LINES" "$TOTAL_ERRS" "$TOTAL_EXPECTED"
echo ""

PCT=0
if [ "$TOTAL_EXPECTED" -gt 0 ]; then
    PCT=$((TOTAL_LINES * 100 / TOTAL_EXPECTED))
fi
echo "  Progress: ${PCT}% (${TOTAL_LINES}/${TOTAL_EXPECTED} lines)"
echo "  Errors: ${TOTAL_ERRS}"
