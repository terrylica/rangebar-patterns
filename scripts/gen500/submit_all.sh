#!/usr/bin/env bash
# shellcheck disable=SC2029
set -euo pipefail

echo "=== Gen500: Submit All Cross-Asset 2-Feature Jobs ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_DIR="/tmp/gen500_sql"

# Upload SQL files to BigBlack
echo "--- Uploading SQL files ---"
rsync -az --info=progress2 /tmp/gen500_sql/ bigblack:${REMOTE_DIR}/

# Clean pueue before starting
echo "--- Cleaning pueue group p1 ---"
ssh bigblack "pueue clean -g p1 2>/dev/null || true"

# Submit all assets sequentially (each queues 1008 jobs)
# @500dbps altcoins
for SYMBOL in DOGEUSDT XRPUSDT LINKUSDT MATICUSDT NEARUSDT ADAUSDT AVAXUSDT LTCUSDT DOTUSDT; do
    bash "${SCRIPT_DIR}/submit.sh" "$SYMBOL" 500
done

# @250dbps majors
for SYMBOL in BTCUSDT ETHUSDT BNBUSDT; do
    bash "${SCRIPT_DIR}/submit.sh" "$SYMBOL" 250
done

echo ""
echo "=== All assets submitted ==="
echo "Total: 12 assets × 1,008 configs = 12,096 jobs"
echo "Monitor: ssh bigblack 'pueue status -g p1'"
echo "ETA: ~50 min at 4 parallel × 2s/query"
