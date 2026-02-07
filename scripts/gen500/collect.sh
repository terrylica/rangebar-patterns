#!/usr/bin/env bash
# shellcheck disable=SC2029
set -euo pipefail

echo "=== Gen500: Collect Cross-Asset Results ==="

mkdir -p logs/gen500

for SYMBOL in DOGEUSDT XRPUSDT LINKUSDT MATICUSDT NEARUSDT ADAUSDT AVAXUSDT LTCUSDT DOTUSDT; do
    LOG="/tmp/gen500_${SYMBOL}_500.jsonl"
    LOCAL="logs/gen500/${SYMBOL}_500.jsonl"
    echo -n "  ${SYMBOL}@500: "
    scp "bigblack:${LOG}" "$LOCAL" 2>/dev/null && {
        LINES=$(wc -l < "$LOCAL" | tr -d ' ')
        echo "${LINES} lines"
    } || echo "not found"
done

for SYMBOL in BTCUSDT ETHUSDT BNBUSDT; do
    LOG="/tmp/gen500_${SYMBOL}_250.jsonl"
    LOCAL="logs/gen500/${SYMBOL}_250.jsonl"
    echo -n "  ${SYMBOL}@250: "
    scp "bigblack:${LOG}" "$LOCAL" 2>/dev/null && {
        LINES=$(wc -l < "$LOCAL" | tr -d ' ')
        echo "${LINES} lines"
    } || echo "not found"
done

echo ""
echo "--- Post-processing: fix nan/NULL ---"
for f in logs/gen500/*.jsonl; do
    [ -f "$f" ] || continue
    sed -i '' 's/:nan,/:null,/g; s/:nan}/:null}/g; s/\\N/NULL/g' "$f"
done

echo "--- Validating JSONL ---"
python3 -c "
import json, glob, sys
ok = 0
bad = 0
for f in sorted(glob.glob('logs/gen500/*.jsonl')):
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
