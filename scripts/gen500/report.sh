#!/usr/bin/env bash
set -euo pipefail

echo "=== Gen500: Cross-Asset 2-Feature Sweep Report ==="
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

python3 << 'PYREPORT'
import json, glob, sys
from collections import defaultdict

# Load all results
results = []
per_asset = defaultdict(list)
for f in sorted(glob.glob('logs/gen500/*.jsonl')):
    for line in open(f):
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

        env = d.get('environment', {})
        symbol = env.get('symbol', '?')
        threshold = env.get('threshold_dbps', '?')
        asset_key = f"{symbol}@{threshold}"

        entry = {
            'config_id': d.get('config_id', ''),
            'kelly': kelly,
            'profit_factor': r.get('profit_factor', 0) or 0,
            'win_rate': r.get('win_rate', 0) or 0,
            'signals': signals,
            'asset': asset_key,
        }
        results.append(entry)
        per_asset[asset_key].append(entry)

if not results:
    print("No valid results found.")
    sys.exit(0)

# --- Summary per asset ---
print("--- Per-Asset Summary ---")
print(f"{'Asset':<16s} {'Valid':>6s} {'Kelly>0':>8s} {'Best Kelly':>12s} {'Best Config':<50s}")
print("-" * 96)
for asset in sorted(per_asset.keys()):
    entries = per_asset[asset]
    pos_kelly = [e for e in entries if e['kelly'] > 0]
    best = max(entries, key=lambda e: e['kelly'])
    print(f"{asset:<16s} {len(entries):>6d} {len(pos_kelly):>8d} {best['kelly']:>+12.5f} {best['config_id']:<50s}")

# --- Top 30 across all assets ---
print()
print("--- Top 30 by Kelly (All Assets) ---")
print(f"{'Config':<50s} {'Asset':<16s} {'Signals':>8s} {'PF':>8s} {'Kelly':>10s} {'WR':>8s}")
print("-" * 104)
results.sort(key=lambda e: e['kelly'], reverse=True)
for e in results[:30]:
    print(f"{e['config_id']:<50s} {e['asset']:<16s} {e['signals']:>8d} {e['profit_factor']:>8.4f} {e['kelly']:>+10.5f} {e['win_rate']:>8.4f}")

# --- Cross-asset consistency check ---
print()
print("--- Cross-Asset Consistency: Configs Positive on 3+ Assets ---")
config_assets = defaultdict(list)
for e in results:
    if e['kelly'] > 0:
        config_assets[e['config_id']].append((e['asset'], e['kelly']))

consistent = {c: assets for c, assets in config_assets.items() if len(assets) >= 3}
if consistent:
    for config_id in sorted(consistent, key=lambda c: len(consistent[c]), reverse=True)[:20]:
        assets = consistent[config_id]
        avg_kelly = sum(k for _, k in assets) / len(assets)
        asset_list = ", ".join(f"{a}({k:+.3f})" for a, k in sorted(assets))
        print(f"  {config_id}: {len(assets)} assets, avg Kelly={avg_kelly:+.4f}")
        print(f"    {asset_list}")
else:
    print("  None found — no config has positive Kelly on 3+ assets.")

print()
print(f"Total valid results: {len(results)}")
print(f"Total configs with Kelly > 0: {sum(1 for e in results if e['kelly'] > 0)}")
PYREPORT
