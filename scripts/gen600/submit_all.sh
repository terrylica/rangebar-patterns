#!/usr/bin/env bash
# shellcheck disable=SC2029
set -euo pipefail

echo "=== Gen600: Submit All 220 Units (22 patterns x 10 asset/threshold combos) ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_DIR="/tmp/gen600_sql"

# Upload all SQL files to remote host (one rsync for everything)
echo "--- Uploading SQL files ---"
rsync -az --info=progress2 /tmp/gen600_sql/ "${RANGEBAR_CH_HOST}:${REMOTE_DIR}/"

# Clean pueue before starting
echo "--- Cleaning pueue group p1 ---"
ssh "${RANGEBAR_CH_HOST}" "pueue clean -g p1 2>/dev/null || true"

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

TOTAL_UNITS=$((${#PATTERNS[@]} * ${#ASSETS[@]}))
UNIT=0

for PATTERN in "${PATTERNS[@]}"; do
    for asset_entry in "${ASSETS[@]}"; do
        IFS='|' read -r SYMBOL THRESHOLD <<< "$asset_entry"
        UNIT=$((UNIT + 1))
        echo "[${UNIT}/${TOTAL_UNITS}] ${PATTERN} ${SYMBOL}@${THRESHOLD}"
        bash "${SCRIPT_DIR}/submit.sh" "$PATTERN" "$SYMBOL" "$THRESHOLD"
    done
done

echo ""
echo "=== All ${TOTAL_UNITS} units submitted ==="
echo "  22 patterns x 10 combos = 220 units"
echo "  30,096 configs per combo x 10 combos = 300,960 total jobs"
echo "  Each job produces 3 result rows = 902,880 expected result rows"
echo "  Monitor: ssh ${RANGEBAR_CH_HOST} 'pueue status -g p1'"
echo "  ETA: ~21 hours at 8 parallel x 2s/query"
