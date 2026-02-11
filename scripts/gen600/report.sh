#!/usr/bin/env bash
set -euo pipefail

echo "=== Gen600: Cross-Dimensional Analysis Report ==="
echo ""

LOGDIR="logs/gen600"

if [ ! -d "$LOGDIR" ] || [ -z "$(ls -A "$LOGDIR"/*.jsonl 2>/dev/null)" ]; then
    echo "ERROR: No JSONL files in ${LOGDIR}. Run collect.sh first."
    exit 1
fi

# Merge all JSONL into one temporary file
MERGED="/tmp/gen600_merged.jsonl"
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

merged = Path("/tmp/gen600_merged.jsonl")
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

# ---- 1. Top configs by Kelly (cross-asset) ----
print("=" * 80)
print("1. TOP 30 CONFIGS BY KELLY FRACTION (inverted barrier)")
print("=" * 80)

# Group by feature_config + barrier_profile across assets
config_assets = defaultdict(list)
for rec in lines:
    key = (rec.get("feature_config", ""), rec.get("barrier_profile", ""))
    kelly = rec.get("results", {}).get("kelly_fraction")
    symbol = rec.get("environment", {}).get("symbol", "")
    threshold = rec.get("environment", {}).get("threshold_dbps", "")
    sigs = rec.get("results", {}).get("filtered_signals", 0)
    if kelly is not None and isinstance(kelly, (int, float)):
        config_assets[key].append({
            "symbol": symbol, "threshold": threshold,
            "kelly": kelly, "signals": sigs
        })

# Find configs with positive Kelly on most assets (inverted profile)
cross_asset = []
for (fc, bp), entries in config_assets.items():
    if bp != "inverted":
        continue
    pos = [e for e in entries if e["kelly"] > 0 and e["signals"] >= 100]
    if len(pos) >= 3:  # Positive on 3+ asset/threshold combos
        avg_kelly = sum(e["kelly"] for e in pos) / len(pos)
        cross_asset.append({
            "feature_config": fc,
            "n_positive": len(pos),
            "n_total": len(entries),
            "avg_kelly": avg_kelly,
            "combos": [(e["symbol"], e["threshold"], e["kelly"]) for e in pos]
        })

cross_asset.sort(key=lambda x: (-x["n_positive"], -x["avg_kelly"]))

print(f"\nConfigs with positive Kelly on 3+ combos (inverted): {len(cross_asset)}")
print(f"{'Feature Config':<65s} {'N+':<4s} {'N':<4s} {'Avg Kelly':<10s}")
print("-" * 85)
for item in cross_asset[:30]:
    print(f"{item['feature_config']:<65s} {item['n_positive']:<4d} {item['n_total']:<4d} {item['avg_kelly']:+.4f}")

# ---- 2. Pattern-level summary ----
print("\n" + "=" * 80)
print("2. PATTERN-LEVEL SUMMARY (inverted barrier, all assets)")
print("=" * 80)

pattern_stats = defaultdict(lambda: {"pos_kelly": 0, "total": 0, "avg_kelly": 0, "kellys": []})
for rec in lines:
    bp = rec.get("barrier_profile", "")
    if bp != "inverted":
        continue
    pattern = rec.get("base_pattern", "unknown")
    kelly = rec.get("results", {}).get("kelly_fraction")
    sigs = rec.get("results", {}).get("filtered_signals", 0)
    if kelly is not None and isinstance(kelly, (int, float)) and sigs >= 100:
        ps = pattern_stats[pattern]
        ps["total"] += 1
        ps["kellys"].append(kelly)
        if kelly > 0:
            ps["pos_kelly"] += 1

print(f"\n{'Pattern':<15s} {'Total':<8s} {'Kelly>0':<8s} {'%Pos':<8s} {'Avg Kelly':<10s} {'Med Kelly':<10s}")
print("-" * 60)
for pattern in sorted(pattern_stats.keys()):
    ps = pattern_stats[pattern]
    if ps["total"] == 0:
        continue
    avg_k = sum(ps["kellys"]) / len(ps["kellys"])
    med_k = sorted(ps["kellys"])[len(ps["kellys"]) // 2]
    pct_pos = ps["pos_kelly"] / ps["total"] * 100
    print(f"{pattern:<15s} {ps['total']:<8d} {ps['pos_kelly']:<8d} {pct_pos:<8.1f} {avg_k:<+10.4f} {med_k:<+10.4f}")

# ---- 3. LONG vs SHORT comparison ----
print("\n" + "=" * 80)
print("3. LONG vs SHORT COMPARISON (inverted barrier)")
print("=" * 80)

long_patterns = {"2down", "3down", "dud", "udd", "2down_ng", "hvd", "vwap_l", "wl2d", "wl1d", "exh_l", "exh_l_ng"}
short_patterns = {"2up_s", "3up_s", "udu_s", "duu_s", "2up_ng_s", "hvu_s", "vwap_s", "wl2u_s", "wl1u_s", "exh_s", "exh_s_ng"}

long_kellys = []
short_kellys = []
for rec in lines:
    if rec.get("barrier_profile") != "inverted":
        continue
    pattern = rec.get("base_pattern", "")
    kelly = rec.get("results", {}).get("kelly_fraction")
    sigs = rec.get("results", {}).get("filtered_signals", 0)
    if kelly is None or not isinstance(kelly, (int, float)) or sigs < 100:
        continue
    if pattern in long_patterns:
        long_kellys.append(kelly)
    elif pattern in short_patterns:
        short_kellys.append(kelly)

if long_kellys:
    print(f"\nLONG:  N={len(long_kellys)}, Avg Kelly={sum(long_kellys)/len(long_kellys):+.5f}, "
          f"Kelly>0: {sum(1 for k in long_kellys if k > 0)} ({sum(1 for k in long_kellys if k > 0)/len(long_kellys)*100:.1f}%)")
if short_kellys:
    print(f"SHORT: N={len(short_kellys)}, Avg Kelly={sum(short_kellys)/len(short_kellys):+.5f}, "
          f"Kelly>0: {sum(1 for k in short_kellys if k > 0)} ({sum(1 for k in short_kellys if k > 0)/len(short_kellys)*100:.1f}%)")

# ---- 4. Feature frequency in top configs ----
print("\n" + "=" * 80)
print("4. FEATURE FREQUENCY IN TOP 100 CONFIGS (inverted, Kelly>0, 3+ combos)")
print("=" * 80)

from collections import Counter
feat_counter = Counter()
for item in cross_asset[:100]:
    fc = item["feature_config"]
    # Parse feature_config: pattern__f1_dir_p50__f2_dir_p50
    parts = fc.split("__")
    if len(parts) >= 3:
        f1_part = parts[1]  # e.g., ofi_gt_p50
        f2_part = parts[2]  # e.g., lookback_hurst_lt_p50
        # Extract feature name (remove _gt_p50 or _lt_p50 suffix)
        f1 = "_".join(f1_part.split("_")[:-2]) if f1_part.count("_") >= 2 else f1_part
        f2 = "_".join(f2_part.split("_")[:-2]) if f2_part.count("_") >= 2 else f2_part
        feat_counter[f1] += 1
        feat_counter[f2] += 1

print(f"\n{'Feature':<35s} {'Count':<6s}")
print("-" * 42)
for feat, count in feat_counter.most_common(20):
    print(f"{feat:<35s} {count:<6d}")

# ---- 5. Barrier profile comparison ----
print("\n" + "=" * 80)
print("5. BARRIER PROFILE COMPARISON (all configs, >=100 signals)")
print("=" * 80)

bp_stats = defaultdict(lambda: {"kellys": [], "pfs": [], "wrs": []})
for rec in lines:
    bp = rec.get("barrier_profile", "")
    kelly = rec.get("results", {}).get("kelly_fraction")
    pf = rec.get("results", {}).get("profit_factor")
    wr = rec.get("results", {}).get("hit_rate")
    sigs = rec.get("results", {}).get("filtered_signals", 0)
    if kelly is None or not isinstance(kelly, (int, float)) or sigs < 100:
        continue
    bp_stats[bp]["kellys"].append(kelly)
    if pf is not None and isinstance(pf, (int, float)):
        bp_stats[bp]["pfs"].append(pf)
    if wr is not None and isinstance(wr, (int, float)):
        bp_stats[bp]["wrs"].append(wr)

print(f"\n{'Profile':<12s} {'N':<8s} {'Avg Kelly':<12s} {'Med Kelly':<12s} {'Kelly>0%':<10s} {'Avg PF':<10s} {'Avg WR':<10s}")
print("-" * 75)
for bp in ["inverted", "symmetric", "momentum"]:
    if bp not in bp_stats:
        continue
    s = bp_stats[bp]
    n = len(s["kellys"])
    avg_k = sum(s["kellys"]) / n
    med_k = sorted(s["kellys"])[n // 2]
    pct_pos = sum(1 for k in s["kellys"] if k > 0) / n * 100
    avg_pf = sum(s["pfs"]) / len(s["pfs"]) if s["pfs"] else 0
    avg_wr = sum(s["wrs"]) / len(s["wrs"]) if s["wrs"] else 0
    print(f"{bp:<12s} {n:<8d} {avg_k:<+12.5f} {med_k:<+12.5f} {pct_pos:<10.1f} {avg_pf:<10.3f} {avg_wr:<10.3f}")

# ---- 6. Threshold comparison ----
print("\n" + "=" * 80)
print("6. THRESHOLD COMPARISON (@750 vs @1000, inverted barrier)")
print("=" * 80)

thresh_stats = defaultdict(lambda: {"kellys": [], "pos": 0})
for rec in lines:
    if rec.get("barrier_profile") != "inverted":
        continue
    thresh = rec.get("environment", {}).get("threshold_dbps")
    kelly = rec.get("results", {}).get("kelly_fraction")
    sigs = rec.get("results", {}).get("filtered_signals", 0)
    if kelly is None or not isinstance(kelly, (int, float)) or sigs < 100:
        continue
    thresh_stats[thresh]["kellys"].append(kelly)
    if kelly > 0:
        thresh_stats[thresh]["pos"] += 1

print(f"\n{'Threshold':<12s} {'N':<8s} {'Avg Kelly':<12s} {'Kelly>0':<8s} {'%Pos':<8s}")
print("-" * 50)
for thresh in sorted(thresh_stats.keys()):
    s = thresh_stats[thresh]
    n = len(s["kellys"])
    avg_k = sum(s["kellys"]) / n
    print(f"@{thresh:<11s} {n:<8d} {avg_k:<+12.5f} {s['pos']:<8d} {s['pos']/n*100:<8.1f}")

# ---- 7. Bonferroni check ----
print("\n" + "=" * 80)
print("7. BONFERRONI MULTIPLE TESTING (inverted barrier)")
print("=" * 80)
import math

# Count number of independent tests
n_tests = len([k for k in config_assets if k[1] == "inverted"])
alpha = 0.05
bonf_alpha = alpha / n_tests if n_tests > 0 else alpha
# z-threshold for Bonferroni
from math import sqrt, log
z_bonf = 0
if bonf_alpha > 0:
    # Approximate: z = sqrt(2) * erfinv(1 - 2*bonf_alpha)
    # Use simpler approximation: -log(bonf_alpha) * 0.6 + 1.5 for small alpha
    # For exact: from scipy.stats import norm; z_bonf = norm.ppf(1 - bonf_alpha)
    # Manual approximation good enough for reporting
    z_bonf = sqrt(2 * log(1 / bonf_alpha))  # Tight upper bound

print(f"\nTotal tests (inverted profile): {n_tests}")
print(f"Bonferroni alpha: {bonf_alpha:.2e}")
print(f"Approximate z-threshold: {z_bonf:.2f}")

# Check if any config survives
survivors = 0
for (fc, bp), entries in config_assets.items():
    if bp != "inverted":
        continue
    for e in entries:
        if e["kelly"] is None or not isinstance(e["kelly"], (int, float)):
            continue
        sigs = e["signals"]
        if sigs < 100:
            continue
        # Approximate z-score: kelly / se(kelly) ~ kelly * sqrt(N)
        z = abs(e["kelly"]) * sqrt(sigs) if e["kelly"] > 0 else 0
        if z > z_bonf:
            survivors += 1

print(f"Configs surviving Bonferroni: {survivors}")
if survivors == 0:
    print("VERDICT: No configs pass multiple testing correction (expected for 300K tests)")
else:
    print(f"WARNING: {survivors} configs survive — investigate for possible data artifacts")

print("\n" + "=" * 80)
print("REPORT COMPLETE")
print("=" * 80)
PYEOF

echo ""
echo "Report complete."
