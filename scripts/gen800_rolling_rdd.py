"""Gen800: Rolling 90-day Return/Drawdown ratio distribution for cross-asset ranking.

Computes rolling calendar-window return/drawdown ratios from per-trade JSONL,
producing a DISTRIBUTION of ratios per asset. Assets are ranked by TOPSIS
multi-criteria on the distribution quality (median, worst-case, consistency).

Range bars are NOT time-uniform — entry/exit times are calendar timestamps
but bars span variable durations. Windows use calendar time (90 days).

Usage:
    uv run -p 3.13 python scripts/gen800_rolling_rdd.py
    uv run -p 3.13 python scripts/gen800_rolling_rdd.py --window-days 60
    uv run -p 3.13 python scripts/gen800_rolling_rdd.py --config-prefix atr14

Refs #40
"""

from __future__ import annotations

import argparse
import bisect
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

# Ensure project root on path for ranking imports
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from rangebar_patterns.eval.ranking import topsis_rank  # noqa: E402

# ---- Constants ----

WINDOW_DAYS = 90
STEP_DAYS = 1
MIN_TRADES_PER_WINDOW = 5
RATIO_CAP = 50.0
MIN_VALID_WINDOWS = 10
RESULTS_DIR = Path("results/eval/gen800")


# ---- I/O ----


def load_trades(path: Path) -> list[dict]:
    """Load trade JSONL (or .br compressed), parse exit_time, sort by exit_dt."""
    if path.suffix == ".br" or not path.exists():
        # Try brotli-compressed version
        br_path = path.with_suffix(path.suffix + ".br") if path.suffix != ".br" else path
        if not br_path.exists():
            raise FileNotFoundError(f"Neither {path} nor {br_path} found")
        result = subprocess.run(
            ["brotli", "-d", "-c", str(br_path)],
            capture_output=True,
            check=True,
        )
        lines = result.stdout.decode().strip().split("\n")
    else:
        with open(path) as f:
            lines = f.readlines()

    trades = []
    for line in lines:
        if not line.strip():
            continue
        rec = json.loads(line)
        rec["exit_dt"] = datetime.fromisoformat(rec["exit_time"])
        trades.append(rec)

    trades.sort(key=lambda t: t["exit_dt"])
    return trades


def _parse_asset_key(path: Path) -> tuple[str, str]:
    """Extract (config_prefix, asset_key) from trade filename.

    Patterns:
      trades_{safe_config_id}.jsonl              → (config, "SOLUSDT_750")
      trades_{safe_config_id}_{SYMBOL}_{THR}.jsonl → (config, "{SYMBOL}_{THR}")
    """
    stem = path.stem
    if stem.endswith(".jsonl"):  # double extension from .jsonl.br
        stem = stem[:-6]

    # Remove "trades_" prefix
    if stem.startswith("trades_"):
        stem = stem[7:]

    # Try to extract symbol_threshold suffix
    # Known symbols end with USDT, threshold is 3-4 digits
    parts = stem.rsplit("_", 2)
    if len(parts) >= 3 and parts[-2].endswith("USDT") and parts[-1].isdigit():
        config_prefix = "_".join(parts[:-2])
        asset_key = f"{parts[-2]}_{parts[-1]}"
    else:
        config_prefix = stem
        asset_key = "SOLUSDT_750"  # Default

    return config_prefix, asset_key


# ---- Core Computation ----


def build_window_boundaries(
    trades: list[dict],
    window_days: int = WINDOW_DAYS,
    step_days: int = STEP_DAYS,
) -> list[tuple[datetime, datetime]]:
    """Generate rolling (start, end) window tuples covering all trades."""
    if not trades:
        return []

    earliest = trades[0]["exit_dt"]
    latest = trades[-1]["exit_dt"]

    # First window starts so that it ends at earliest + window_days
    first_end = earliest + timedelta(days=window_days)
    if first_end > latest:
        # Single window covering everything
        return [(earliest, latest)]

    boundaries = []
    w_end = first_end
    while w_end <= latest:
        w_start = w_end - timedelta(days=window_days)
        boundaries.append((w_start, w_end))
        w_end += timedelta(days=step_days)

    return boundaries


def compute_rolling_rdd(
    trades: list[dict],
    window_days: int = WINDOW_DAYS,
    step_days: int = STEP_DAYS,
    min_trades: int = MIN_TRADES_PER_WINDOW,
    ratio_cap: float = RATIO_CAP,
) -> list[dict]:
    """Compute rolling return/drawdown ratio for all windows."""
    if not trades:
        return []

    boundaries = build_window_boundaries(trades, window_days, step_days)
    exit_times = [t["exit_dt"] for t in trades]

    results = []
    for w_start, w_end in boundaries:
        lo = bisect.bisect_left(exit_times, w_start)
        hi = bisect.bisect_right(exit_times, w_end)
        n_trades = hi - lo

        if n_trades < min_trades:
            continue

        returns = np.array([trades[i]["return_pct"] for i in range(lo, hi)])
        total_ret = float(np.sum(returns))

        # Max drawdown within window
        cum = np.cumsum(returns)
        running_max = np.maximum.accumulate(cum)
        drawdowns = running_max - cum
        max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

        # Ratio
        if max_dd > 1e-12:
            ratio = total_ret / max_dd
        elif total_ret > 0:
            ratio = ratio_cap
        else:
            ratio = 0.0

        ratio = min(ratio, ratio_cap)

        results.append({
            "window_start": w_start.isoformat(),
            "window_end": w_end.isoformat(),
            "n_trades": n_trades,
            "total_return": round(total_ret, 6),
            "max_drawdown": round(max_dd, 6),
            "return_dd_ratio": round(ratio, 4),
        })

    return results


def compute_distribution_stats(window_results: list[dict]) -> dict:
    """Compute summary statistics from the ratio distribution."""
    if not window_results:
        return {"status": "insufficient_data", "n_windows": 0}

    ratios = np.array([w["return_dd_ratio"] for w in window_results])
    n = len(ratios)

    if n < MIN_VALID_WINDOWS:
        return {"status": "insufficient_data", "n_windows": n}

    # Find worst and best windows
    worst_idx = int(np.argmin(ratios))
    best_idx = int(np.argmax(ratios))

    stats = {
        "status": "ok",
        "n_windows": n,
        "n_trades_total": sum(w["n_trades"] for w in window_results),
        "median_ratio": round(float(np.median(ratios)), 4),
        "mean_ratio": round(float(np.mean(ratios)), 4),
        "std_ratio": round(float(np.std(ratios)), 4),
        "p10_ratio": round(float(np.percentile(ratios, 10)), 4),
        "p25_ratio": round(float(np.percentile(ratios, 25)), 4),
        "p75_ratio": round(float(np.percentile(ratios, 75)), 4),
        "p90_ratio": round(float(np.percentile(ratios, 90)), 4),
        "min_ratio": round(float(np.min(ratios)), 4),
        "max_ratio": round(float(np.max(ratios)), 4),
        "frac_gt_2": round(float(np.mean(ratios > 2.0)), 4),
        "frac_gt_1": round(float(np.mean(ratios > 1.0)), 4),
        "frac_lt_1": round(float(np.mean(ratios < 1.0)), 4),
        "frac_negative": round(float(np.mean(ratios < 0)), 4),
        "worst_window_start": window_results[worst_idx]["window_start"],
        "worst_window_ratio": window_results[worst_idx]["return_dd_ratio"],
        "best_window_start": window_results[best_idx]["window_start"],
        "best_window_ratio": window_results[best_idx]["return_dd_ratio"],
    }

    # Coefficient of variation (only meaningful if mean > 0)
    if stats["mean_ratio"] > 1e-6:
        stats["ratio_cv"] = round(stats["std_ratio"] / stats["mean_ratio"], 4)
    else:
        stats["ratio_cv"] = float("inf")

    return stats


def rank_assets(asset_stats: dict[str, dict]) -> list[dict]:
    """Rank assets by TOPSIS on distribution quality metrics."""
    # Filter to assets with sufficient data
    valid = {k: v for k, v in asset_stats.items() if v.get("status") == "ok"}

    if not valid:
        return []

    asset_keys = sorted(valid.keys())
    n = len(asset_keys)

    # Build decision matrix: 4 criteria
    # [median_ratio, p10_ratio, frac_gt_2, frac_lt_1]
    matrix = np.zeros((n, 4))
    for i, key in enumerate(asset_keys):
        s = valid[key]
        matrix[i, 0] = s["median_ratio"]
        matrix[i, 1] = s["p10_ratio"]
        matrix[i, 2] = s["frac_gt_2"]
        matrix[i, 3] = s["frac_lt_1"]

    weights = np.array([0.35, 0.30, 0.20, 0.15])
    types = np.array([1, 1, 1, -1])  # frac_lt_1 is cost (lower better)

    scores = topsis_rank(matrix, weights, types)

    # Build ranked output
    results = []
    for i, key in enumerate(asset_keys):
        rec = {"asset": key, "topsis_score": round(float(scores[i]), 4)}
        rec.update(valid[key])
        results.append(rec)

    results.sort(key=lambda r: -r["topsis_score"])
    for rank, rec in enumerate(results, 1):
        rec["rank"] = rank

    return results


def build_report(rankings: list[dict], window_days: int) -> str:
    """Generate human-readable markdown ranking report."""
    lines = [
        f"# Gen800 Cross-Asset Rolling {window_days}-Day Return/Drawdown Ranking",
        "",
        f"Window: {window_days} calendar days, sliding by 1 day",
        f"Min trades per window: {MIN_TRADES_PER_WINDOW}",
        f"Ratio cap: {RATIO_CAP}",
        "",
        "## Asset Rankings (TOPSIS: 35% median + 30% p10 + 20% frac>2 + 15% frac<1)",
        "",
        "| Rank | Asset | TOPSIS | Median | P10 | P90 | %>2 | %<1 | %Neg | Windows |",
        "|------|-------|--------|--------|-----|-----|-----|-----|------|---------|",
    ]

    for r in rankings:
        lines.append(
            f"| {r['rank']} "
            f"| {r['asset']} "
            f"| {r['topsis_score']:.3f} "
            f"| {r['median_ratio']:.2f} "
            f"| {r['p10_ratio']:.2f} "
            f"| {r['p90_ratio']:.2f} "
            f"| {r['frac_gt_2']:.1%} "
            f"| {r['frac_lt_1']:.1%} "
            f"| {r['frac_negative']:.1%} "
            f"| {r['n_windows']} |"
        )

    lines.extend(["", "## Per-Asset Detail", ""])

    for r in rankings:
        lines.extend([
            f"### #{r['rank']} {r['asset']}",
            "",
            f"- **Trades**: {r['n_trades_total']} across {r['n_windows']} windows",
            f"- **Ratio distribution**: "
            f"min={r['min_ratio']:.2f}, p10={r['p10_ratio']:.2f}, "
            f"median={r['median_ratio']:.2f}, p90={r['p90_ratio']:.2f}, "
            f"max={r['max_ratio']:.2f}",
            f"- **Consistency**: CV={r.get('ratio_cv', 'N/A')}",
            f"- **Best window**: {r['best_window_start'][:10]} "
            f"(ratio={r['best_window_ratio']:.2f})",
            f"- **Worst window**: {r['worst_window_start'][:10]} "
            f"(ratio={r['worst_window_ratio']:.2f})",
            "",
        ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Gen800 rolling return/drawdown ratio analysis"
    )
    parser.add_argument(
        "--window-days", type=int, default=WINDOW_DAYS,
        help=f"Rolling window size in calendar days (default: {WINDOW_DAYS})",
    )
    parser.add_argument(
        "--config-prefix", default=None,
        help="Filter to trade files matching this config prefix",
    )
    args = parser.parse_args()

    window_days = args.window_days

    # Discover trade files (both .jsonl and .jsonl.br)
    trade_files = sorted(RESULTS_DIR.glob("trades_*.jsonl"))
    trade_files_br = sorted(RESULTS_DIR.glob("trades_*.jsonl.br"))

    # Merge: prefer .jsonl if both exist, add .br-only files
    seen_stems = {p.stem for p in trade_files}
    for br_path in trade_files_br:
        jsonl_stem = br_path.stem  # "foo.jsonl" from "foo.jsonl.br"
        if jsonl_stem not in seen_stems:
            trade_files.append(br_path)

    if not trade_files:
        print("No trade files found in", RESULTS_DIR)
        sys.exit(1)

    # Group by config prefix → process one config at a time
    config_groups: dict[str, list[tuple[str, Path]]] = {}
    for path in trade_files:
        config_prefix, asset_key = _parse_asset_key(path)
        if args.config_prefix and args.config_prefix not in config_prefix:
            continue
        config_groups.setdefault(config_prefix, []).append((asset_key, path))

    print(f"Found {len(config_groups)} config(s), {len(trade_files)} trade file(s)")
    print(f"Window: {window_days} days, step: {STEP_DAYS} day(s)\n")

    for config_prefix, assets in sorted(config_groups.items()):
        print(f"=== Config: {config_prefix} ===")

        asset_stats: dict[str, dict] = {}
        for asset_key, path in sorted(assets):
            print(f"  {asset_key}: ", end="", flush=True)
            trades = load_trades(path)
            windows = compute_rolling_rdd(
                trades, window_days=window_days, min_trades=MIN_TRADES_PER_WINDOW,
            )
            stats = compute_distribution_stats(windows)
            stats["config_prefix"] = config_prefix
            asset_stats[asset_key] = stats

            if stats["status"] == "ok":
                print(
                    f"{stats['n_windows']} windows, "
                    f"median={stats['median_ratio']:.2f}, "
                    f"p10={stats['p10_ratio']:.2f}, "
                    f"frac>2={stats['frac_gt_2']:.1%}"
                )
            else:
                print(f"insufficient data ({stats['n_windows']} windows)")

        # Rank
        rankings = rank_assets(asset_stats)

        if not rankings:
            print("  No assets with sufficient data for ranking.\n")
            continue

        # Print ranking summary
        print(f"\n  Ranking ({len(rankings)} assets):")
        for r in rankings:
            print(
                f"    #{r['rank']} {r['asset']:15s} "
                f"TOPSIS={r['topsis_score']:.3f} "
                f"median={r['median_ratio']:.2f} "
                f"p10={r['p10_ratio']:.2f}"
            )

        # Write outputs
        safe_prefix = config_prefix[:60]
        rankings_path = RESULTS_DIR / f"rolling_rdd_{safe_prefix}.jsonl"
        with open(rankings_path, "w") as f:
            for r in rankings:
                f.write(json.dumps(r) + "\n")
        print(f"\n  Rankings: {rankings_path}")

        report = build_report(rankings, window_days)
        report_path = RESULTS_DIR / f"rolling_rdd_{safe_prefix}.md"
        with open(report_path, "w") as f:
            f.write(report)
        print(f"  Report:   {report_path}")
        print()

    print("Done.")


if __name__ == "__main__":
    main()
