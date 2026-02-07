#!/usr/bin/env bash
set -euo pipefail

echo "=== Gen400: Multi-Feature Sweep Report ==="
echo ""

# Merge all results
MERGED=/tmp/gen400_merged.jsonl
cat logs/gen400/2feature.jsonl logs/gen400/3feature.jsonl logs/gen400/4feature.jsonl 2>/dev/null > "$MERGED" || {
    echo "No results found. Run gen400:collect first."
    exit 1
}

TOTAL=$(wc -l < "$MERGED" | tr -d '[:space:]')
ERRORS=$(grep -c '"error":true' "$MERGED" 2>/dev/null || true)
ERRORS=${ERRORS:-0}
VALID=$((TOTAL - ERRORS))
echo "Total configs: ${TOTAL} (${VALID} valid, ${ERRORS} errors)"
echo ""

echo "--- Top 30 by Kelly (all phases, >=100 signals) ---"
printf "%-70s %4s %7s %8s %8s %8s\n" "CONFIG" "N_F" "SIGNALS" "PF" "KELLY" "WIN_RT"
printf "%-70s %4s %7s %8s %8s %8s\n" "---" "---" "---" "---" "---" "---"

# Use python3 for robust JSON parsing (handles null Kelly, nan, etc.)
python3 -c "
import json, sys
results = []
for line in open('$MERGED'):
    try:
        d = json.loads(line)
    except:
        continue
    if d.get('error') or d.get('skipped'):
        continue
    r = d.get('results', {})
    kelly = r.get('kelly_fraction')
    signals = r.get('filtered_signals', 0)
    if kelly is None or signals < 100:
        continue
    results.append((
        d.get('config_id', ''),
        d.get('n_features', 0),
        signals,
        r.get('profit_factor', 0) or 0,
        kelly,
        r.get('win_rate', 0) or 0,
    ))
results.sort(key=lambda x: x[4], reverse=True)
for cfg, nf, sig, pf, kelly, wr in results[:30]:
    print(f'{cfg:<70s} {nf:>4d} {sig:>7d} {pf:>8.4f} {kelly:>8.5f} {wr:>8.4f}')
"

echo ""
echo "--- Positive Kelly Summary (>=100 signals) ---"
python3 -c "
import json
pos = total = 0
for line in open('$MERGED'):
    try:
        d = json.loads(line)
    except:
        continue
    if d.get('error') or d.get('skipped'):
        continue
    r = d.get('results', {})
    kelly = r.get('kelly_fraction')
    signals = r.get('filtered_signals', 0)
    if kelly is None or signals < 100:
        continue
    total += 1
    if kelly > 0:
        pos += 1
print(f'Configs with Kelly > 0 (>=100 signals): {pos} / {total}')
"

echo ""
echo "--- Feature Frequency in Positive-Kelly Combos ---"
python3 -c "
import json
from collections import Counter
freq = Counter()
for line in open('$MERGED'):
    try:
        d = json.loads(line)
    except:
        continue
    if d.get('error') or d.get('skipped'):
        continue
    r = d.get('results', {})
    kelly = r.get('kelly_fraction')
    if kelly is None or kelly <= 0:
        continue
    # Extract feature names from config_id
    parts = d.get('config_id', '').split('__')
    for p in parts:
        # Remove quantile suffix like _gt_p50
        feature = p.rsplit('_gt_', 1)[0].rsplit('_lt_', 1)[0]
        if feature:
            freq[feature] += 1
for feat, count in freq.most_common(10):
    print(f'  {count:>5d} {feat}')
"

echo ""
echo "--- Bonferroni Check ---"
for phase_info in "2feature|1008" "3feature|12096" "4feature|1120"; do
    IFS='|' read -r phase n_tests <<< "$phase_info"
    FILE="logs/gen400/${phase}.jsonl"
    if [ ! -f "$FILE" ]; then continue; fi

    python3 -c "
import json, math
best_kelly = -999
best_id = ''
best_n = 0
best_wr = 0
for line in open('$FILE'):
    try:
        d = json.loads(line)
    except:
        continue
    if d.get('error') or d.get('skipped'):
        continue
    r = d.get('results', {})
    kelly = r.get('kelly_fraction')
    signals = r.get('filtered_signals', 0)
    if kelly is None or signals < 100:
        continue
    if kelly > best_kelly:
        best_kelly = kelly
        best_id = d.get('config_id', '')
        best_n = signals
        best_wr = r.get('win_rate', 0) or 0

if best_n > 0:
    z = (best_wr - 0.5) / math.sqrt(0.25 / best_n) if best_n > 0 else 0
    print(f'  ${phase} (${n_tests} tests): best={best_id} Kelly={best_kelly:.5f} z={z:.3f}')
else:
    print(f'  ${phase}: no valid results')
"
done

echo ""
echo "--- Decision ---"
python3 -c "
import json
best_kelly = -999
for line in open('$MERGED'):
    try:
        d = json.loads(line)
    except:
        continue
    if d.get('error') or d.get('skipped'):
        continue
    r = d.get('results', {})
    kelly = r.get('kelly_fraction')
    signals = r.get('filtered_signals', 0)
    if kelly is None or signals < 100:
        continue
    if kelly > best_kelly:
        best_kelly = kelly
print(f'Best Kelly across all (>=100 signals): {best_kelly:.5f}')
if best_kelly > 0.02:
    print('VERDICT: POTENTIAL WINNER. Run barrier grid + backtest alignment.')
elif best_kelly > 0:
    print('VERDICT: MARGINAL. Feature combos show slight edge. Consider NN pathway.')
else:
    print('VERDICT: NO EDGE. Multi-feature filters exhaustively tested. Pattern is NN-only.')
"
