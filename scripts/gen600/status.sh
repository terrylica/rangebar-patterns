#!/usr/bin/env bash
# shellcheck disable=SC2029
set -euo pipefail

echo "=== Gen600: Hybrid Feature Sweep Status ==="
echo ""

# Pueue status
echo "--- Pueue Group p1 ---"
ssh "${RANGEBAR_CH_HOST}" "pueue status -g p1 2>/dev/null | tail -5" || echo "  (pueue not running)"
echo ""

# 22 pattern IDs
PATTERNS=(
    2down 3down dud udd 2down_ng hvd vwap_l wl2d wl1d exh_l exh_l_ng
    2up_s 3up_s udu_s duu_s 2up_ng_s hvu_s vwap_s wl2u_s wl1u_s exh_s exh_s_ng
)

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

# Expected per unit: 1368 configs x 3 barriers = 4104 lines
# (342 pairs x 4 combos = 1368 configs per pattern/asset/threshold)
EXPECTED_LINES_PER_UNIT=4104

echo "--- Results Per Pattern/Asset ---"
printf "  %-14s %-14s %8s %8s %8s\n" "Pattern" "Asset" "Lines" "Errors" "Expected"
echo "  -----------------------------------------------------------"

TOTAL_LINES=0
TOTAL_ERRS=0
TOTAL_EXPECTED=0

for PATTERN in "${PATTERNS[@]}"; do
    for asset_entry in "${ASSETS[@]}"; do
        IFS='|' read -r SYMBOL THRESHOLD <<< "$asset_entry"
        LOG="/tmp/gen600_${PATTERN}_${SYMBOL}_${THRESHOLD}.jsonl"
        LINES=$(ssh -n "${RANGEBAR_CH_HOST}" "wc -l < ${LOG} 2>/dev/null || echo 0" | tr -d '[:space:]')
        ERRS=$(ssh -n "${RANGEBAR_CH_HOST}" "grep -c '\"error\":true' ${LOG} 2>/dev/null || echo 0" | tr -d '[:space:]')

        # Only print non-zero rows to keep output manageable
        if [ "$LINES" -gt 0 ]; then
            printf "  %-14s %-14s %8s %8s %8s\n" "$PATTERN" "${SYMBOL}@${THRESHOLD}" "$LINES" "$ERRS" "$EXPECTED_LINES_PER_UNIT"
        fi

        TOTAL_LINES=$((TOTAL_LINES + LINES))
        TOTAL_ERRS=$((TOTAL_ERRS + ERRS))
        TOTAL_EXPECTED=$((TOTAL_EXPECTED + EXPECTED_LINES_PER_UNIT))
    done
done

echo "  -----------------------------------------------------------"
printf "  %-14s %-14s %8s %8s %8s\n" "TOTAL" "" "$TOTAL_LINES" "$TOTAL_ERRS" "$TOTAL_EXPECTED"
echo ""

PCT=0
if [ "$TOTAL_EXPECTED" -gt 0 ]; then
    PCT=$((TOTAL_LINES * 100 / TOTAL_EXPECTED))
fi
echo "  Progress: ${PCT}% (${TOTAL_LINES}/${TOTAL_EXPECTED} lines)"
echo "  Errors: ${TOTAL_ERRS}"
