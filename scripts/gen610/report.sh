#!/usr/bin/env bash
set -euo pipefail

echo "=== Gen610: Barrier Grid Optimization Report ==="
echo ""

LOGDIR="logs/gen610"

if [ ! -d "$LOGDIR" ] || [ -z "$(ls -A "$LOGDIR"/*.jsonl 2>/dev/null)" ]; then
    echo "ERROR: No JSONL files in ${LOGDIR}. Run collect.sh first."
    exit 1
fi

# Merge all JSONL into one temporary file
MERGED="/tmp/gen610_merged.jsonl"
cat "$LOGDIR"/*.jsonl > "$MERGED"
TOTAL_LINES=$(wc -l < "$MERGED" | tr -d ' ')
echo "Total result lines: ${TOTAL_LINES}"
echo ""

# Run Python analysis
python3 << 'PYEOF'
import json
import sys
from collections import defaultdict
from pathlib import Path
from math import sqrt, log

merged = Path("/tmp/gen610_merged.jsonl")
lines = []
errors = 0
skipped = 0

for line in merged.open():
    try:
        rec = json.loads(line.strip())
    except json.JSONDecodeError:
        errors += 1
        continue
    if rec.get("error"):
        errors += 1
        continue
    if rec.get("skipped"):
        skipped += 1
        continue
    lines.append(rec)

print(f"Parsed: {len(lines)} valid, {errors} errors, {skipped} skipped")
print()

if not lines:
    print("No valid results to analyze.")
    sys.exit(1)

# ---- 1. Best Barrier per Config (cross-asset) ----
print("=" * 90)
print("1. TOP 30 CONFIGS BY BEST BARRIER (cross-asset avg Kelly)")
print("=" * 90)

# Group by (feature_config, barrier_id) across assets
config_barrier_assets = defaultdict(list)
for rec in lines:
    fc = rec.get("feature_config", "")
    bid = rec.get("barrier_id", "")
    kelly = rec.get("results", {}).get("kelly_fraction")
    symbol = rec.get("environment", {}).get("symbol", "")
    threshold = rec.get("environment", {}).get("threshold_dbps", "")
    sigs = rec.get("results", {}).get("filtered_signals", 0)
    if kelly is not None and isinstance(kelly, (int, float)):
        config_barrier_assets[(fc, bid)].append({
            "symbol": symbol, "threshold": threshold,
            "kelly": kelly, "signals": sigs
        })

# For each (config, barrier), count combos with positive Kelly
cross_results = []
for (fc, bid), entries in config_barrier_assets.items():
    pos = [e for e in entries if e["kelly"] > 0 and e["signals"] >= 30]
    if len(pos) >= 5:  # Positive on 5+ of 10 combos
        avg_kelly = sum(e["kelly"] for e in pos) / len(pos)
        total_sigs = sum(e["signals"] for e in entries)
        cross_results.append({
            "feature_config": fc,
            "barrier_id": bid,
            "n_positive": len(pos),
            "n_total": len(entries),
            "avg_kelly": avg_kelly,
            "total_signals": total_sigs,
        })

cross_results.sort(key=lambda x: (-x["n_positive"], -x["avg_kelly"]))

print(f"\nConfigs with positive Kelly on 5+ combos: {len(cross_results)}")
print(f"{'Config':<55s} {'Barrier':<20s} {'N+':<4s} {'Avg Kelly':<10s} {'Signals':<8s}")
print("-" * 100)
for item in cross_results[:30]:
    print(f"{item['feature_config']:<55s} {item['barrier_id']:<20s} {item['n_positive']:<4d} {item['avg_kelly']:+.4f}    {item['total_signals']:<8d}")

# ---- 2. Barrier Grid Heatmap (avg Kelly per barrier across all configs) ----
print("\n" + "=" * 90)
print("2. BARRIER GRID HEATMAP (avg Kelly across all configs and assets)")
print("=" * 90)

barrier_stats = defaultdict(lambda: {"kellys": [], "pos": 0})
for rec in lines:
    bid = rec.get("barrier_id", "")
    kelly = rec.get("results", {}).get("kelly_fraction")
    sigs = rec.get("results", {}).get("filtered_signals", 0)
    if kelly is not None and isinstance(kelly, (int, float)) and sigs >= 30:
        barrier_stats[bid]["kellys"].append(kelly)
        if kelly > 0:
            barrier_stats[bid]["pos"] += 1

print(f"\n{'Barrier ID':<25s} {'N':<6s} {'Avg Kelly':<12s} {'Med Kelly':<12s} {'%Pos':<8s}")
print("-" * 65)
for bid in sorted(barrier_stats.keys()):
    s = barrier_stats[bid]
    n = len(s["kellys"])
    avg_k = sum(s["kellys"]) / n
    med_k = sorted(s["kellys"])[n // 2]
    pct_pos = s["pos"] / n * 100
    print(f"{bid:<25s} {n:<6d} {avg_k:<+12.5f} {med_k:<+12.5f} {pct_pos:<8.1f}")

# ---- 3. Best Barrier per Config (ignoring cross-asset) ----
print("\n" + "=" * 90)
print("3. OPTIMAL BARRIER PER CONFIG (pooled across assets)")
print("=" * 90)

config_barrier_pool = defaultdict(lambda: defaultdict(list))
for rec in lines:
    fc = rec.get("feature_config", "")
    bid = rec.get("barrier_id", "")
    kelly = rec.get("results", {}).get("kelly_fraction")
    sigs = rec.get("results", {}).get("filtered_signals", 0)
    if kelly is not None and isinstance(kelly, (int, float)) and sigs >= 30:
        config_barrier_pool[fc][bid].append(kelly)

print(f"\n{'Config':<55s} {'Best Barrier':<20s} {'Avg Kelly':<10s} {'2nd Best':<20s} {'2nd Kelly':<10s}")
print("-" * 118)
for fc in sorted(config_barrier_pool.keys()):
    barrier_avgs = {}
    for bid, kellys in config_barrier_pool[fc].items():
        barrier_avgs[bid] = sum(kellys) / len(kellys)
    ranked = sorted(barrier_avgs.items(), key=lambda x: -x[1])
    if len(ranked) >= 2:
        print(f"{fc:<55s} {ranked[0][0]:<20s} {ranked[0][1]:+.4f}    {ranked[1][0]:<20s} {ranked[1][1]:+.4f}")
    elif len(ranked) == 1:
        print(f"{fc:<55s} {ranked[0][0]:<20s} {ranked[0][1]:+.4f}")

# ---- 4. TP/SL/MaxBars Marginal Effects ----
print("\n" + "=" * 90)
print("4. MARGINAL EFFECTS: TP, SL, MAX_BARS")
print("=" * 90)

tp_stats = defaultdict(list)
sl_stats = defaultdict(list)
mb_stats = defaultdict(list)
for rec in lines:
    kelly = rec.get("results", {}).get("kelly_fraction")
    sigs = rec.get("results", {}).get("filtered_signals", 0)
    barrier = rec.get("barrier", {})
    if kelly is None or not isinstance(kelly, (int, float)) or sigs < 30:
        continue
    tp = barrier.get("tp_mult")
    sl = barrier.get("sl_mult")
    mb = barrier.get("max_bars")
    if tp is not None:
        tp_stats[tp].append(kelly)
    if sl is not None:
        sl_stats[sl].append(kelly)
    if mb is not None:
        mb_stats[mb].append(kelly)

print("\n  --- TP Multiplier ---")
print(f"  {'TP':<8s} {'N':<6s} {'Avg Kelly':<12s} {'%Pos':<8s}")
for tp in sorted(tp_stats.keys()):
    ks = tp_stats[tp]
    n = len(ks)
    avg = sum(ks) / n
    ppos = sum(1 for k in ks if k > 0) / n * 100
    print(f"  {tp:<8.2f} {n:<6d} {avg:<+12.5f} {ppos:<8.1f}")

print("\n  --- SL Multiplier ---")
print(f"  {'SL':<8s} {'N':<6s} {'Avg Kelly':<12s} {'%Pos':<8s}")
for sl in sorted(sl_stats.keys()):
    ks = sl_stats[sl]
    n = len(ks)
    avg = sum(ks) / n
    ppos = sum(1 for k in ks if k > 0) / n * 100
    print(f"  {sl:<8.2f} {n:<6d} {avg:<+12.5f} {ppos:<8.1f}")

print("\n  --- Max Bars ---")
print(f"  {'MB':<8s} {'N':<6s} {'Avg Kelly':<12s} {'%Pos':<8s}")
for mb in sorted(mb_stats.keys()):
    ks = mb_stats[mb]
    n = len(ks)
    avg = sum(ks) / n
    ppos = sum(1 for k in ks if k > 0) / n * 100
    print(f"  {mb:<8d} {n:<6d} {avg:<+12.5f} {ppos:<8.1f}")

# ---- 5. Per-Asset Leaderboard ----
print("\n" + "=" * 90)
print("5. PER-ASSET LEADERBOARD (top 5 per asset/threshold)")
print("=" * 90)

asset_configs = defaultdict(list)
for rec in lines:
    fc = rec.get("feature_config", "")
    bid = rec.get("barrier_id", "")
    kelly = rec.get("results", {}).get("kelly_fraction")
    sigs = rec.get("results", {}).get("filtered_signals", 0)
    symbol = rec.get("environment", {}).get("symbol", "")
    threshold = rec.get("environment", {}).get("threshold_dbps", "")
    if kelly is not None and isinstance(kelly, (int, float)) and sigs >= 30:
        asset_configs[f"{symbol}@{threshold}"].append({
            "config": fc, "barrier": bid, "kelly": kelly, "signals": sigs
        })

for asset_key in sorted(asset_configs.keys()):
    items = sorted(asset_configs[asset_key], key=lambda x: -x["kelly"])
    print(f"\n  {asset_key}:")
    for item in items[:5]:
        print(f"    {item['config']:<50s} {item['barrier']:<20s} Kelly={item['kelly']:+.4f} ({item['signals']} sigs)")

# ---- 6. Bonferroni Check ----
print("\n" + "=" * 90)
print("6. BONFERRONI MULTIPLE TESTING")
print("=" * 90)

n_tests = len(config_barrier_assets)
alpha = 0.05
bonf_alpha = alpha / n_tests if n_tests > 0 else alpha
z_bonf = sqrt(2 * log(1 / bonf_alpha)) if bonf_alpha > 0 else 0

print(f"\nTotal tests: {n_tests}")
print(f"Bonferroni alpha: {bonf_alpha:.2e}")
print(f"Approximate z-threshold: {z_bonf:.2f}")

survivors = 0
for (fc, bid), entries in config_barrier_assets.items():
    for e in entries:
        if e["kelly"] is None or not isinstance(e["kelly"], (int, float)):
            continue
        sigs = e["signals"]
        if sigs < 30:
            continue
        z = abs(e["kelly"]) * sqrt(sigs) if e["kelly"] > 0 else 0
        if z > z_bonf:
            survivors += 1

print(f"Configs surviving Bonferroni: {survivors}")
if survivors == 0:
    print("VERDICT: No configs pass multiple testing correction")
else:
    print(f"NOTE: {survivors} individual results survive — investigate")

print("\n" + "=" * 90)
print("REPORT COMPLETE")
print("=" * 90)
PYEOF

echo ""
echo "Report complete."
