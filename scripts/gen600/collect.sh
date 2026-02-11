#!/usr/bin/env bash
# shellcheck disable=SC2029
set -euo pipefail

echo "=== Gen600: Collect Sweep Results ==="

mkdir -p logs/gen600

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

TOTAL_LINES=0
COLLECTED=0

for PATTERN in "${PATTERNS[@]}"; do
    for asset_entry in "${ASSETS[@]}"; do
        IFS='|' read -r SYMBOL THRESHOLD <<< "$asset_entry"
        LOG="/tmp/gen600_${PATTERN}_${SYMBOL}_${THRESHOLD}.jsonl"
        LOCAL="logs/gen600/${PATTERN}_${SYMBOL}_${THRESHOLD}.jsonl"

        echo -n "  ${PATTERN} ${SYMBOL}@${THRESHOLD}: "
        scp "${RANGEBAR_CH_HOST}:${LOG}" "$LOCAL" 2>/dev/null && {
            LINES=$(wc -l < "$LOCAL" | tr -d ' ')
            echo "${LINES} lines"
            TOTAL_LINES=$((TOTAL_LINES + LINES))
            COLLECTED=$((COLLECTED + 1))
        } || echo "not found"
    done
done

echo ""
echo "Collected: ${COLLECTED}/220 units, ${TOTAL_LINES} total lines"
echo ""

echo "--- Post-processing: fix nan/NULL ---"
for f in logs/gen600/*.jsonl; do
    [ -f "$f" ] || continue
    sed -i '' 's/:nan,/:null,/g; s/:nan}/:null}/g; s/\\N/NULL/g; s/:inf,/:null,/g; s/:-inf,/:null,/g; s/:inf}/:null}/g; s/:-inf}/:null}/g' "$f"
done

echo "--- Validating JSONL ---"
python3 -c "
import json, glob, sys
ok = 0
bad = 0
for f in sorted(glob.glob('logs/gen600/*.jsonl')):
    for i, line in enumerate(open(f), 1):
        try:
            json.loads(line)
            ok += 1
        except:
            bad += 1
            print(f'  PARSE ERROR: {f}:{i}', file=sys.stderr)
print(f'  Valid: {ok}, Errors: {bad}')
if bad > 0:
    sys.exit(1)
"

echo ""
echo "--- Size check for brotli ---"
for f in logs/gen600/*.jsonl; do
    SIZE=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null || echo 0)
    if [ "$SIZE" -gt 1048576 ]; then
        echo "  ${f}: $(( SIZE / 1024 ))KB — eligible for brotli"
    fi
done
