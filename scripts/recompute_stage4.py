#!/usr/bin/env python3
"""Post-hoc recompute of Stage 4 GT-composite scores from Parquet fold data.

Reads existing combo JSONs + fold Parquets, recalculates GT-composite with
corrected n_trials (= survivor count, not 434), and overwrites combo JSONs.

Also normalizes Stage 3 field names to the canonical naming convention:
  n_surviving_barriers → n_pbo_survivors_in
  n_bootstrap_pass → n_bootstrap_accepted
  n_bootstrap_reject → n_bootstrap_rejected

Usage:
    python scripts/recompute_stage4.py [--dry-run]

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/28
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np
import polars as pl
from scipy.stats import kurtosis, skew

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rangebar_patterns.eval.dsr import (
    compute_psr,
    expected_max_sr,
    sr_standard_error,
)
from rangebar_patterns.eval.walk_forward import compute_gt_composite

COMBO_DIR = Path("results/eval/gen720/combos")
FOLD_DIR = Path("results/eval/gen720/folds")

# Stage 3 field renames: old name → new name
STAGE3_RENAMES = {
    "n_surviving_barriers": "n_pbo_survivors_in",
    "n_bootstrap_pass": "n_bootstrap_accepted",
    "n_bootstrap_reject": "n_bootstrap_rejected",
}


def load_all_folds() -> pl.DataFrame:
    """Load and concatenate all fold Parquet chunks."""
    parquets = sorted(glob.glob(str(FOLD_DIR / "_chunk_*.parquet")))
    if not parquets:
        print(f"ERROR: No parquet files found in {FOLD_DIR}")
        sys.exit(1)
    dfs = [pl.read_parquet(p) for p in parquets]
    combined = pl.concat(dfs)
    print(f"Loaded {len(parquets)} parquet chunks → {combined.shape[0]:,} rows")
    return combined


def recompute_gt_for_combo(
    combo: dict, fold_df: pl.DataFrame
) -> tuple[dict, bool]:
    """Recompute GT-composite scores for a single combo.

    Returns (updated_combo, changed).
    """
    changed = False

    # === Normalize Stage 3 field names ===
    s3 = combo.get("stage3_bootstrap")
    if s3:
        for old_name, new_name in STAGE3_RENAMES.items():
            if old_name in s3 and new_name not in s3:
                s3[new_name] = s3.pop(old_name)
                changed = True

    # Filter fold data for this combo (needed for GT recompute + top_barrier metrics)
    fm = combo["formation"]
    sym = combo["symbol"]
    thr = combo["threshold"]
    combo_folds = fold_df.filter(
        (pl.col("formation") == fm)
        & (pl.col("symbol") == sym)
        & (pl.col("threshold") == thr)
    )

    # === Add median_max_drawdown + fold_sharpe to top_barriers (always) ===
    if not combo_folds.is_empty():
        for barrier in combo.get("top_barriers", []):
            if "median_max_drawdown" not in barrier:
                bid_folds = combo_folds.filter(pl.col("barrier_id") == barrier["barrier_id"])
                if not bid_folds.is_empty():
                    n_folds = len(bid_folds)
                    barrier["median_max_drawdown"] = round(
                        float(bid_folds["max_drawdown"].median()), 6
                    )
                    avg_returns = bid_folds["avg_return"].to_numpy()
                    std_r = float(np.std(avg_returns))
                    barrier["fold_sharpe"] = round(
                        float(np.mean(avg_returns) / std_r)
                        if n_folds > 1 and std_r > 1e-12 else 0.0,
                        6,
                    )
                    changed = True

    # === Recompute GT-composite ===
    s4 = combo.get("stage4_ranking")
    s3 = combo.get("stage3_bootstrap")  # re-read after possible rename
    if not s4 or not s3:
        return combo, changed

    final_bids = s3.get("final_barrier_ids", [])
    if not final_bids or combo_folds.is_empty():
        return combo, changed

    # Get PBO scores from stage2_cpcv
    pbo_scores = {}
    s2 = combo.get("stage2_cpcv")
    if s2 and s2.get("pbo_scores"):
        pbo_scores = s2["pbo_scores"]

    # Recompute GT for each final survivor
    n_survivors = max(len(final_bids), 2)
    gt_scores = {}

    for bid in final_bids:
        bid_folds = combo_folds.filter(pl.col("barrier_id") == bid)
        returns = bid_folds["avg_return"].to_list()
        arr = np.array(returns, dtype=float)
        n = len(arr)

        if n < 3:
            gt_scores[bid] = 0.0
            continue

        # DSR from OOS fold-level returns
        std_val = float(np.std(arr))
        sr_val = float(np.mean(arr) / std_val) if std_val > 1e-12 else 0.0
        skew_val = float(skew(arr))
        kurt_val = float(kurtosis(arr, fisher=False))  # raw kurtosis
        se = sr_standard_error(sr_val, n, skew_val, kurt_val)
        sr_star = expected_max_sr(n_trials=n_survivors, var_sr=1.0)
        dsr_val = compute_psr(sr_val, sr_star, se)

        # Median OOS Omega and MaxDD
        omega_val = float(bid_folds["omega"].median())
        mdd_val = float(bid_folds["max_drawdown"].median())
        pbo_val = pbo_scores.get(bid, 0.5)

        gt_scores[bid] = compute_gt_composite(
            omega=omega_val, dsr=dsr_val, pbo=pbo_val, max_drawdown=mdd_val,
        )

    # Update stage4_ranking
    old_gt = s4.get("gt_scores", {})
    new_gt = {k: round(v, 6) for k, v in sorted(gt_scores.items(), key=lambda x: -x[1])}

    if new_gt != old_gt:
        changed = True

    s4["n_trials_dsr"] = n_survivors
    s4["gt_scores"] = new_gt
    s4["top_gt_barrier"] = max(gt_scores, key=gt_scores.get) if gt_scores else None
    s4["n_gt_scored"] = len(gt_scores)

    # Update top_barriers with recomputed GT scores
    for barrier in combo.get("top_barriers", []):
        bid = barrier["barrier_id"]
        if bid in gt_scores:
            barrier["gt_composite"] = round(gt_scores[bid], 6)
            barrier["survived_all_stages"] = bid in final_bids

    combo["stage4_ranking"] = s4
    return combo, changed


def main():
    parser = argparse.ArgumentParser(description="Recompute Stage 4 GT-composite from Parquet data")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing")
    args = parser.parse_args()

    combo_files = sorted(glob.glob(str(COMBO_DIR / "_combo_*.json")))
    print(f"Found {len(combo_files)} combo JSONs")

    fold_df = load_all_folds()

    n_updated = 0
    n_skipped = 0
    n_gt_positive = 0
    gt_values = []

    for combo_path in combo_files:
        with open(combo_path) as f:
            combo = json.load(f)

        updated_combo, changed = recompute_gt_for_combo(combo, fold_df)

        # Collect stats
        s4 = updated_combo.get("stage4_ranking")
        if s4 and s4.get("gt_scores"):
            for v in s4["gt_scores"].values():
                gt_values.append(v)
                if v > 0:
                    n_gt_positive += 1

        if changed:
            n_updated += 1
            if not args.dry_run:
                with open(combo_path, "w") as f:
                    json.dump(updated_combo, f, indent=None, separators=(",", ":"))
                    f.write("\n")
        else:
            n_skipped += 1

    # Report
    mode = "[DRY RUN] " if args.dry_run else ""
    print(f"\n{mode}Recompute complete:")
    print(f"  Updated: {n_updated}")
    print(f"  Skipped (no change): {n_skipped}")
    print(f"  GT > 0: {n_gt_positive}/{len(gt_values)}")
    if gt_values:
        arr = np.array(gt_values)
        pos = arr[arr > 0]
        print(f"  GT distribution: min={arr.min():.6f}, max={arr.max():.6f}, "
              f"mean={arr.mean():.6f}, median={np.median(arr):.6f}")
        if len(pos) > 0:
            print(f"  GT positive only: min={pos.min():.6f}, max={pos.max():.6f}, "
                  f"mean={pos.mean():.6f}")


if __name__ == "__main__":
    main()
