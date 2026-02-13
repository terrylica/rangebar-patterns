#!/usr/bin/env bash
# shellcheck disable=SC2029
set -euo pipefail

echo "=== Gen610: Collect Barrier Grid Results ==="

mkdir -p logs/gen610

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

for asset_entry in "${ASSETS[@]}"; do
    IFS='|' read -r SYMBOL THRESHOLD <<< "$asset_entry"
    LOG="/tmp/gen610_${SYMBOL}_${THRESHOLD}.jsonl"
    LOCAL="logs/gen610/${SYMBOL}_${THRESHOLD}.jsonl"

    echo -n "  ${SYMBOL}@${THRESHOLD}: "
    scp "${RANGEBAR_CH_HOST}:${LOG}" "$LOCAL" 2>/dev/null && {
        LINES=$(wc -l < "$LOCAL" | tr -d ' ')
        echo "${LINES} lines"
        TOTAL_LINES=$((TOTAL_LINES + LINES))
        COLLECTED=$((COLLECTED + 1))
    } || echo "not found"
done

echo ""
echo "Collected: ${COLLECTED}/10 units, ${TOTAL_LINES} total lines"
echo ""

echo "--- Post-processing: fix nan/NULL ---"
for f in logs/gen610/*.jsonl; do
    [ -f "$f" ] || continue
    sed -i '' 's/:nan,/:null,/g; s/:nan}/:null}/g; s/\\N/NULL/g; s/:inf,/:null,/g; s/:-inf,/:null,/g; s/:inf}/:null}/g; s/:-inf}/:null}/g' "$f"
done

echo "--- Validating JSONL ---"
python3 -c "
import json, glob, sys
ok = 0
bad = 0
for f in sorted(glob.glob('logs/gen610/*.jsonl')):
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
for f in logs/gen610/*.jsonl; do
    SIZE=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null || echo 0)
    if [ "$SIZE" -gt 1048576 ]; then
        echo "  ${f}: $(( SIZE / 1024 ))KB — eligible for brotli"
    fi
done
