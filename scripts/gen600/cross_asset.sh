#!/usr/bin/env bash
set -euo pipefail

# Gen600 Cross-Asset Consistency Matrix
# Copied from: scripts/gen600/report.sh (same shell wrapper, deeper Python analysis)
# Purpose: Identify configs that are positive across multiple asset/threshold combos
# Gate #119 acceptance: >=5 configs positive on 8+ combos out of 10

echo "=== Gen600: Cross-Asset Consistency Matrix ==="
echo ""

LOGDIR="logs/gen600"

if [ ! -d "$LOGDIR" ] || [ -z "$(ls -A "$LOGDIR"/*.jsonl 2>/dev/null)" ]; then
    echo "ERROR: No JSONL files in ${LOGDIR}. Run collect.sh or decompress .br files first."
    exit 1
fi

# Merge all JSONL into one temporary file
MERGED="/tmp/gen600_merged.jsonl"
cat "$LOGDIR"/*.jsonl > "$MERGED"
TOTAL_LINES=$(wc -l < "$MERGED" | tr -d ' ')
echo "Total result lines: ${TOTAL_LINES}"
echo ""

# Output TSV for downstream consumption
OUTPUT_TSV="/tmp/gen600_cross_asset_top50.tsv"

python3 << 'PYEOF'
import json
import sys
from collections import defaultdict, Counter
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

# =================================================================
# Build the consistency matrix
# Key: feature_config (includes pattern + features)
# Value: dict of {(symbol, threshold): kelly} for inverted barrier only
# =================================================================

ALL_COMBOS = [
    ("BNBUSDT", 750), ("BNBUSDT", 1000),
    ("BTCUSDT", 750), ("BTCUSDT", 1000),
    ("ETHUSDT", 750), ("ETHUSDT", 1000),
    ("SOLUSDT", 750), ("SOLUSDT", 1000),
    ("XRPUSDT", 750), ("XRPUSDT", 1000),
]

MIN_SIGNALS = 30  # Minimum signals to count as valid (relaxed from 100 for cross-asset)

config_matrix = defaultdict(dict)  # feature_config -> {(sym, thr): {kelly, signals, ...}}

for rec in lines:
    bp = rec.get("barrier_profile", "")
    if bp != "inverted":
        continue
    fc = rec.get("feature_config", "")
    if not fc:
        continue
    sym = rec.get("environment", {}).get("symbol", "")
    thr = rec.get("environment", {}).get("threshold_dbps", 0)
    kelly = rec.get("results", {}).get("kelly_fraction")
    sigs = rec.get("results", {}).get("filtered_signals", 0)
    wr = rec.get("results", {}).get("hit_rate")
    pf = rec.get("results", {}).get("profit_factor")
    pattern = rec.get("base_pattern", "")

    if kelly is None or not isinstance(kelly, (int, float)):
        continue

    config_matrix[fc][(sym, thr)] = {
        "kelly": kelly,
        "signals": sigs,
        "hit_rate": wr,
        "profit_factor": pf,
        "pattern": pattern,
    }

print(f"Unique feature configs (inverted): {len(config_matrix)}")

# =================================================================
# 1. Consistency ranking: N combos with positive Kelly + min signals
# =================================================================
print("\n" + "=" * 90)
print("1. CONSISTENCY MATRIX: Configs ranked by N positive combos (inverted, >= 30 signals)")
print("=" * 90)

ranked = []
for fc, combos in config_matrix.items():
    valid = [(k, v) for k, v in combos.items() if v["signals"] >= MIN_SIGNALS]
    positive = [(k, v) for k, v in valid if v["kelly"] > 0]
    if not positive:
        continue
    avg_kelly_pos = sum(v["kelly"] for _, v in positive) / len(positive)
    avg_kelly_all = sum(v["kelly"] for _, v in valid) / len(valid) if valid else 0
    min_kelly = min(v["kelly"] for _, v in positive)
    pattern = ""
    for _, v in combos.items():
        pattern = v.get("pattern", "")
        if pattern:
            break
    ranked.append({
        "feature_config": fc,
        "pattern": pattern,
        "n_positive": len(positive),
        "n_valid": len(valid),
        "n_total": len(combos),
        "avg_kelly_pos": avg_kelly_pos,
        "avg_kelly_all": avg_kelly_all,
        "min_kelly_pos": min_kelly,
        "combos": combos,
    })

ranked.sort(key=lambda x: (-x["n_positive"], -x["avg_kelly_pos"]))

# Header
combo_labels = [f"{s[:3]}@{t}" for s, t in ALL_COMBOS]
header = f"{'#':<4s} {'Feature Config':<55s} {'Pat':<8s} {'N+':<4s} {'AvgK+':<8s} "
header += " ".join(f"{l:>8s}" for l in combo_labels)
print(f"\n{header}")
print("-" * len(header))

for i, item in enumerate(ranked[:50], 1):
    row = f"{i:<4d} {item['feature_config'][:54]:<55s} {item['pattern']:<8s} {item['n_positive']:<4d} {item['avg_kelly_pos']:+.4f} "
    for combo in ALL_COMBOS:
        entry = item["combos"].get(combo)
        if entry is None:
            row += f"{'---':>8s} "
        elif entry["signals"] < MIN_SIGNALS:
            row += f"{'(low)':>8s} "
        elif entry["kelly"] > 0:
            row += f"{entry['kelly']:>+8.4f} "
        else:
            row += f"{entry['kelly']:>+8.4f} "
    print(row)

# =================================================================
# 2. Heatmap: Pattern × Asset/Threshold (avg Kelly for top 10 configs per pattern)
# =================================================================
print("\n" + "=" * 90)
print("2. PATTERN HEATMAP: Avg Kelly of top-10 configs per pattern per combo")
print("=" * 90)

# For each pattern, find top 10 configs by avg Kelly, then show per-combo
pattern_configs = defaultdict(list)
for item in ranked:
    if item["n_positive"] >= 3:
        pattern_configs[item["pattern"]].append(item)

# Sort patterns by best avg Kelly
pattern_order = sorted(
    pattern_configs.keys(),
    key=lambda p: -max(c["avg_kelly_pos"] for c in pattern_configs[p]),
)

header2 = f"{'Pattern':<12s} {'#Cfgs':<7s} "
header2 += " ".join(f"{l:>8s}" for l in combo_labels)
print(f"\n{header2}")
print("-" * len(header2))

for pattern in pattern_order:
    configs = pattern_configs[pattern][:10]
    # Average Kelly across top 10 configs for each combo
    combo_avgs = {}
    for combo in ALL_COMBOS:
        vals = []
        for c in configs:
            entry = c["combos"].get(combo)
            if entry and entry["signals"] >= MIN_SIGNALS:
                vals.append(entry["kelly"])
        combo_avgs[combo] = sum(vals) / len(vals) if vals else None

    row = f"{pattern:<12s} {len(configs):<7d} "
    for combo in ALL_COMBOS:
        v = combo_avgs[combo]
        if v is None:
            row += f"{'---':>8s} "
        else:
            row += f"{v:>+8.4f} "
    print(row)

# =================================================================
# 3. Stability: Configs with positive Kelly on ALL 10 combos
# =================================================================
print("\n" + "=" * 90)
print("3. STABILITY: Configs with positive Kelly on N = 8, 9, or 10 combos")
print("=" * 90)

for threshold_n in [10, 9, 8, 7, 6]:
    survivors = [r for r in ranked if r["n_positive"] >= threshold_n]
    if survivors:
        print(f"\n  N >= {threshold_n}: {len(survivors)} configs")
        for s in survivors[:10]:
            print(f"    {s['feature_config']:<55s} N+={s['n_positive']} AvgK={s['avg_kelly_pos']:+.4f} Pat={s['pattern']}")
        if len(survivors) > 10:
            print(f"    ... and {len(survivors) - 10} more")
    else:
        print(f"\n  N >= {threshold_n}: 0 configs")

# =================================================================
# 4. Feature frequency in top cross-asset configs
# =================================================================
print("\n" + "=" * 90)
print("4. FEATURE FREQUENCY IN TOP 100 CROSS-ASSET CONFIGS (3+ combos)")
print("=" * 90)

feat_counter = Counter()
direction_counter = Counter()
quantile_counter = Counter()
for item in ranked[:100]:
    fc = item["feature_config"]
    parts = fc.split("__")
    if len(parts) >= 3:
        for part_idx in [1, 2]:
            part = parts[part_idx]
            tokens = part.split("_")
            # Find direction (gt/lt) and quantile (p50/p10/p25/p75/p90)
            dir_idx = None
            for j, tok in enumerate(tokens):
                if tok in ("gt", "lt"):
                    dir_idx = j
                    break
            if dir_idx is not None:
                feat_name = "_".join(tokens[:dir_idx])
                direction = tokens[dir_idx]
                quantile = "_".join(tokens[dir_idx + 1:])
                feat_counter[feat_name] += 1
                direction_counter[f"{feat_name}_{direction}"] += 1
                quantile_counter[f"{feat_name}_{direction}_{quantile}"] += 1

print(f"\n{'Feature':<35s} {'Count':<6s} {'Direction (gt/lt)':<20s}")
print("-" * 62)
for feat, count in feat_counter.most_common(25):
    gt = direction_counter.get(f"{feat}_gt", 0)
    lt = direction_counter.get(f"{feat}_lt", 0)
    dir_str = f"gt={gt}, lt={lt}"
    print(f"{feat:<35s} {count:<6d} {dir_str:<20s}")

# =================================================================
# 5. Per-asset leaderboard
# =================================================================
print("\n" + "=" * 90)
print("5. PER-ASSET LEADERBOARD: Top 5 configs per asset/threshold combo")
print("=" * 90)

for sym, thr in ALL_COMBOS:
    entries = []
    for fc, combos in config_matrix.items():
        e = combos.get((sym, thr))
        if e and e["signals"] >= MIN_SIGNALS and e["kelly"] > 0:
            entries.append((fc, e))
    entries.sort(key=lambda x: -x[1]["kelly"])
    print(f"\n  {sym}@{thr} (top 5 of {len(entries)} positive):")
    for fc, e in entries[:5]:
        print(f"    Kelly={e['kelly']:+.4f} WR={e['hit_rate']:.3f} PF={e['profit_factor']:.3f} N={e['signals']:4d} | {fc[:60]}")

# =================================================================
# 6. Threshold sensitivity: same config, @750 vs @1000
# =================================================================
print("\n" + "=" * 90)
print("6. THRESHOLD SENSITIVITY: Kelly@750 vs Kelly@1000 (same config, same symbol)")
print("=" * 90)

symbols = ["BNBUSDT", "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
for sym in symbols:
    same_both = []
    for fc, combos in config_matrix.items():
        e750 = combos.get((sym, 750))
        e1000 = combos.get((sym, 1000))
        if (e750 and e750["signals"] >= MIN_SIGNALS and
            e1000 and e1000["signals"] >= MIN_SIGNALS):
            same_both.append((fc, e750["kelly"], e1000["kelly"]))
    if not same_both:
        continue
    # Correlation
    k750 = [x[1] for x in same_both]
    k1000 = [x[2] for x in same_both]
    n = len(same_both)
    mean750 = sum(k750) / n
    mean1000 = sum(k1000) / n
    cov = sum((a - mean750) * (b - mean1000) for a, b in zip(k750, k1000)) / n
    std750 = (sum((a - mean750) ** 2 for a in k750) / n) ** 0.5
    std1000 = (sum((b - mean1000) ** 2 for b in k1000) / n) ** 0.5
    corr = cov / (std750 * std1000) if std750 > 0 and std1000 > 0 else 0
    both_pos = sum(1 for _, a, b in same_both if a > 0 and b > 0)
    print(f"  {sym}: N={n}, corr(Kelly@750, Kelly@1000)={corr:+.3f}, both_positive={both_pos}/{n} ({both_pos/n*100:.1f}%)")

# =================================================================
# 7. Write top 50 to TSV for downstream (Gen610 input)
# =================================================================
print("\n" + "=" * 90)
print("7. WRITING TOP 50 CROSS-ASSET CONFIGS TO TSV")
print("=" * 90)

tsv_path = "/tmp/gen600_cross_asset_top50.tsv"
with open(tsv_path, "w") as f:
    headers = ["rank", "feature_config", "pattern", "n_positive", "n_valid",
               "avg_kelly_pos", "avg_kelly_all", "min_kelly_pos"]
    for s, t in ALL_COMBOS:
        headers.append(f"kelly_{s[:3]}_{t}")
    f.write("\t".join(headers) + "\n")

    for i, item in enumerate(ranked[:50], 1):
        row = [
            str(i),
            item["feature_config"],
            item["pattern"],
            str(item["n_positive"]),
            str(item["n_valid"]),
            f"{item['avg_kelly_pos']:.6f}",
            f"{item['avg_kelly_all']:.6f}",
            f"{item['min_kelly_pos']:.6f}",
        ]
        for combo in ALL_COMBOS:
            entry = item["combos"].get(combo)
            if entry and entry["signals"] >= MIN_SIGNALS:
                row.append(f"{entry['kelly']:.6f}")
            else:
                row.append("")
        f.write("\t".join(row) + "\n")

print(f"Written to: {tsv_path}")

# =================================================================
# GATE #119 CHECK
# =================================================================
print("\n" + "=" * 90)
print("GATE #119: Cross-asset survivors (>= 5 configs positive on 8+ combos)")
print("=" * 90)

n8plus = len([r for r in ranked if r["n_positive"] >= 8])
gate_pass = n8plus >= 5
verdict = "PASS" if gate_pass else "FAIL"
print(f"\nConfigs with 8+ positive combos: {n8plus}")
print(f"Gate threshold: >= 5 configs")
print(f"GATE #119: {verdict}")

if not gate_pass:
    # Fall back to lower threshold
    for thr in [7, 6, 5]:
        n_thr = len([r for r in ranked if r["n_positive"] >= thr])
        if n_thr >= 5:
            print(f"\nFallback: {n_thr} configs with {thr}+ positive combos (meets threshold)")
            break

print("\n" + "=" * 90)
print("CROSS-ASSET ANALYSIS COMPLETE")
print("=" * 90)
PYEOF

echo ""
echo "Cross-asset analysis complete."
echo "TSV output: ${OUTPUT_TSV}"
