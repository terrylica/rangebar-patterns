#!/usr/bin/env bash
# shellcheck disable=SC2029
set -euo pipefail

echo "=== Gen500: Cross-Asset Sweep Status ==="
echo ""

# Pueue status
echo "--- Pueue Group p1 ---"
ssh bigblack "pueue status -g p1 2>/dev/null | tail -5" || echo "  (pueue not running)"
echo ""

# Per-asset result counts
echo "--- Results Per Asset ---"
printf "  %-12s %6s %6s %6s\n" "Asset" "Done" "Errors" "Expected"
echo "  -----------------------------------------------"

TOTAL_DONE=0
TOTAL_ERR=0

for SYMBOL in DOGEUSDT XRPUSDT LINKUSDT MATICUSDT NEARUSDT ADAUSDT AVAXUSDT LTCUSDT DOTUSDT; do
    LOG="/tmp/gen500_${SYMBOL}_500.jsonl"
    DONE=$(ssh -n bigblack "wc -l < ${LOG} 2>/dev/null || echo 0" | tr -d '[:space:]')
    ERRS=$(ssh -n bigblack "grep -c '\"error\":true' ${LOG} 2>/dev/null || echo 0" | tr -d '[:space:]')
    printf "  %-12s %6s %6s %6s\n" "${SYMBOL}@500" "$DONE" "$ERRS" "1008"
    TOTAL_DONE=$((TOTAL_DONE + DONE))
    TOTAL_ERR=$((TOTAL_ERR + ERRS))
done

for SYMBOL in BTCUSDT ETHUSDT BNBUSDT; do
    LOG="/tmp/gen500_${SYMBOL}_250.jsonl"
    DONE=$(ssh -n bigblack "wc -l < ${LOG} 2>/dev/null || echo 0" | tr -d '[:space:]')
    ERRS=$(ssh -n bigblack "grep -c '\"error\":true' ${LOG} 2>/dev/null || echo 0" | tr -d '[:space:]')
    printf "  %-12s %6s %6s %6s\n" "${SYMBOL}@250" "$DONE" "$ERRS" "1008"
    TOTAL_DONE=$((TOTAL_DONE + DONE))
    TOTAL_ERR=$((TOTAL_ERR + ERRS))
done

echo "  -----------------------------------------------"
printf "  %-12s %6s %6s %6s\n" "TOTAL" "$TOTAL_DONE" "$TOTAL_ERR" "12096"
