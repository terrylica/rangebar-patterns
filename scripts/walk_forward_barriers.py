# FILE-SIZE-OK
"""Gen720 Walk-Forward Barrier Optimization orchestrator.

4-stage WFO pipeline per formation × symbol × threshold combo,
then cross-formation and cross-asset aggregation.

LONG and SHORT are strictly isolated — separate analysis, telemetry, verdicts.

Usage:
    uv run -p 3.13 python scripts/walk_forward_barriers.py --direction long
    uv run -p 3.13 python scripts/walk_forward_barriers.py --direction short

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/28
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent.parent))

from rangebar_patterns import config
from rangebar_patterns.eval._io import provenance_dict, results_dir
from rangebar_patterns.eval._schemas import WFAggregationV1
from rangebar_patterns.eval.ranking import knee_detect, topsis_rank
from rangebar_patterns.eval.walk_forward import (
    build_cpcv_folds,
    build_fold_metadata,
    build_stability_matrix,
    build_wfo_folds,
    compute_gt_composite,
    compute_pbo_from_cpcv,
    compute_vorob_stability,
    evaluate_barriers_in_fold,
    run_bootstrap_validation,
    run_nested_cpcv,
    screen_top_k_barriers,
)

# ---- Constants ----

LONG_FORMATIONS = [
    "udd", "wl1d", "2down", "dud", "vwap_l",
    "hvd", "exh_l", "3down", "2down_ng", "exh_l_ng", "wl2d",
]

SHORT_FORMATIONS_A = ["2up_ng_s", "exh_s"]  # Strategy A: LONG-mirrored
SHORT_FORMATIONS_B = ["2up_ng_s_rev", "exh_s_rev"]  # Strategy B: reverse time-decay

SYMBOLS = [
    "ADAUSDT", "ATOMUSDT", "AVAXUSDT", "BNBUSDT", "BTCUSDT",
    "DOGEUSDT", "DOTUSDT", "ETHUSDT", "LINKUSDT", "LTCUSDT",
    "NEARUSDT", "SHIBUSDT", "SOLUSDT", "UNIUSDT", "XRPUSDT",
]

THRESHOLDS = [500, 750, 1000]


def _get_raw_dir() -> Path:
    """Get results/eval/gen720/raw/ directory."""
    return results_dir() / "gen720" / "raw"


def _get_output_dir() -> Path:
    """Get results/eval/gen720/ directory."""
    d = results_dir() / "gen720"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 of a file (first 8 hex chars)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:8]


# ---- TSV Loading ----


def load_tsv(tsv_path: Path) -> pl.DataFrame:
    """Load Gen720 TSV into Polars DataFrame.

    Expected columns: formation, barrier_id, signal_ts_ms, entry_price,
    exit_type, exit_bar, exit_price, return_pct, tp_price,
    sl_wide_price, sl_tight_price, phase1_bars, max_bars.
    """
    df = pl.read_csv(
        tsv_path,
        separator="\t",
        has_header=True,
        null_values=["\\N", "nan", ""],
        infer_schema_length=10000,
    )

    # Add signal_idx: unique signal index by timestamp ordering
    unique_signals = (
        df.select("signal_ts_ms")
        .unique()
        .sort("signal_ts_ms")
        .with_row_index("signal_idx")
    )
    df = df.join(unique_signals, on="signal_ts_ms")

    # Cast return_pct to float
    if "return_pct" in df.columns:
        df = df.with_columns(pl.col("return_pct").cast(pl.Float64))

    return df


# ---- Per-Combo WFO ----


def run_combo_wfo(
    df: pl.DataFrame,
    formation: str,
    symbol: str,
    threshold: int,
    strategy: str,
    tsv_path: Path,
) -> tuple[pl.DataFrame, dict]:
    """Run 4-stage WFO pipeline for a single combo.

    Stage 1: WFO screening (all 434 barriers → top K by median Omega)
    Stage 2: CPCV validation + nested barrier selection + PBO estimation
    Stage 3: Bootstrap CIs on surviving barriers (PBO < 0.50)
    Stage 4: GT-composite ranking (Omega × DSR × (1-PBO) × DD penalty)

    Returns (fold_results_df, combo_summary_dict).
    """
    t0 = time.monotonic()

    n_unique_signals = df.select("signal_ts_ms").n_unique()

    # Build signal-level DataFrame for fold indexing
    signal_df = (
        df.select("signal_ts_ms", "signal_idx")
        .unique(subset=["signal_ts_ms"])
        .sort("signal_idx")
        .with_columns(pl.col("signal_ts_ms").alias("timestamp_ms"))
    )

    t_load = time.monotonic() - t0

    # Build WFO folds
    t_fold_start = time.monotonic()
    purge_bars = 100  # max_bars for trade outcome lookahead
    folds = build_wfo_folds(
        n_unique_signals,
        purge_bars=purge_bars,
    )
    t_fold = time.monotonic() - t_fold_start

    if len(folds) < 2:
        print(f"    LOW POWER: only {len(folds)} folds for {n_unique_signals} signals")

    # Evaluate all barriers across all folds
    t_eval_start = time.monotonic()
    all_fold_dfs = []
    for fold_id, (train_idx, test_idx) in enumerate(folds):
        fold_df = evaluate_barriers_in_fold(df, test_idx)
        fold_df = fold_df.with_columns(pl.lit(fold_id).alias("fold_id"))
        all_fold_dfs.append(fold_df)

    if not all_fold_dfs:
        empty_df = pl.DataFrame()
        return empty_df, _empty_combo_summary(
            formation, symbol, threshold, strategy, n_unique_signals, tsv_path,
        )

    fold_results = pl.concat(all_fold_dfs)
    t_eval = time.monotonic() - t_eval_start

    # Vorob'ev stability
    t_vorob_start = time.monotonic()
    vorob_result = None
    required_cols = {"barrier_id", "fold_id", "omega", "rachev", "total_return"}
    if required_cols.issubset(set(fold_results.columns)):
        try:
            matrix, sets, _bids = build_stability_matrix(fold_results)
            if matrix.shape[0] >= 3:
                vorob_result = compute_vorob_stability(matrix, sets)
        except (ValueError, RuntimeError, TimeoutError) as e:
            print(f"    Vorob'ev failed: {e}")
    t_vorob = time.monotonic() - t_vorob_start

    # Stage 1: Top barriers by median OOS Omega
    top_bids = screen_top_k_barriers(fold_results, k=config.WF_SCREEN_TOP_K)

    # Stage 2: CPCV validation + nested barrier selection + PBO
    t_cpcv_start = time.monotonic()
    pbo_scores: dict[str, float] = {}
    cpcv_results_df = pl.DataFrame()
    cpcv_folds = []

    if len(top_bids) >= 3 and n_unique_signals >= 100:
        try:
            cpcv_n_folds = max(6, min(12, n_unique_signals // 200))
            cpcv_folds = build_cpcv_folds(
                n_unique_signals,
                n_folds=cpcv_n_folds,
                purge_bars=purge_bars,
            )
            if len(cpcv_folds) >= 3:
                cpcv_results_df = run_nested_cpcv(
                    df, cpcv_folds, top_bids,
                )
                if not cpcv_results_df.is_empty():
                    pbo_scores = compute_pbo_from_cpcv(cpcv_results_df)
        except (ValueError, RuntimeError, ImportError) as e:
            print(f"    Stage 2 (CPCV) failed: {e}")
    t_cpcv = time.monotonic() - t_cpcv_start

    # Stage 2 → Stage 3 filter: barriers with PBO < 0.50
    surviving_bids = [
        bid for bid in top_bids
        if pbo_scores.get(bid, 0.5) < 0.50
    ]

    # Stage 3: Bootstrap CIs on surviving barriers
    t_boot_start = time.monotonic()
    bootstrap_df = pl.DataFrame()

    if surviving_bids and cpcv_folds and n_unique_signals >= 100:
        try:
            bootstrap_df = run_bootstrap_validation(
                df, cpcv_folds, surviving_bids,
            )
        except (ValueError, RuntimeError, ImportError) as e:
            print(f"    Stage 3 (Bootstrap) failed: {e}")
    t_boot = time.monotonic() - t_boot_start

    # Build bootstrap rejection map
    bootstrap_rejected: dict[str, bool] = {}
    if not bootstrap_df.is_empty():
        for row in bootstrap_df.to_dicts():
            bootstrap_rejected[row["barrier_id"]] = row.get("rejected", False)

    # Final surviving barriers: passed PBO AND bootstrap
    final_bids = [
        bid for bid in surviving_bids
        if not bootstrap_rejected.get(bid, False)
    ]

    # Stage 4: GT-composite ranking for final survivors
    gt_scores: dict[str, float] = {}
    if final_bids:
        from scipy.stats import kurtosis, skew

        from rangebar_patterns.eval.dsr import compute_psr, expected_max_sr, sr_standard_error

        for bid in final_bids:
            bid_fold_df = fold_results.filter(pl.col("barrier_id") == bid)
            returns = bid_fold_df["avg_return"].to_list()
            arr = np.array(returns, dtype=float)
            n = len(arr)
            if n < 3:
                gt_scores[bid] = 0.0
                continue

            # Compute DSR from OOS fold-level returns
            # n_trials = number of Stage 4 survivors (NOT 434 grid size).
            # CPCV already filtered from 434 → final_bids — these are the
            # surviving hypotheses. Using 434 here double-penalizes, producing
            # SR* ~ 3.01 which floors DSR to 0 for all realistic fold-level SR.
            sr_val = float(np.mean(arr) / np.std(arr)) if np.std(arr) > 1e-12 else 0.0
            skew_val = float(skew(arr))
            kurt_val = float(kurtosis(arr, fisher=False))  # excess=False → raw kurtosis
            se = sr_standard_error(sr_val, n, skew_val, kurt_val)
            n_survivors = max(len(final_bids), 2)  # at least 2 to avoid degenerate SR*
            sr_star = expected_max_sr(n_trials=n_survivors, var_sr=1.0)
            dsr_val = compute_psr(sr_val, sr_star, se)

            # Median OOS Omega and MaxDD
            omega_val = float(bid_fold_df["omega"].median())
            mdd_val = float(bid_fold_df["max_drawdown"].median())
            pbo_val = pbo_scores.get(bid, 0.5)

            gt_scores[bid] = compute_gt_composite(
                omega=omega_val, dsr=dsr_val, pbo=pbo_val, max_drawdown=mdd_val,
            )

    # Build top_barriers list with Stage 2/3/4 annotations
    top_barriers = []
    for bid in top_bids:
        bid_df = fold_results.filter(pl.col("barrier_id") == bid)
        n_folds = len(bid_df)
        avg_omega = float(bid_df["omega"].mean()) if n_folds > 0 else 0.0
        avg_rachev = float(bid_df["rachev"].mean()) if n_folds > 0 else 0.0
        avg_pf = float(bid_df["profit_factor"].mean()) if n_folds > 0 else 0.0
        omega_vals = bid_df["omega"].to_numpy()
        omega_cv = float(np.std(omega_vals) / np.mean(omega_vals)) if np.mean(omega_vals) > 1e-12 else float("inf")
        n_viable = int((bid_df["omega"] > 1.0).sum())
        consistency = n_viable / n_folds if n_folds > 0 else 0.0

        # Compute per-barrier fold-level metrics for post-hoc recomputation
        avg_returns = bid_df["avg_return"].to_numpy()
        mdd_median = float(bid_df["max_drawdown"].median()) if n_folds > 0 else 0.0
        std_r = float(np.std(avg_returns))
        sr_val = float(np.mean(avg_returns) / std_r) if n_folds > 1 and std_r > 1e-12 else 0.0

        barrier_info = {
            "barrier_id": bid,
            "consistency": round(consistency, 4),
            "avg_oos_omega": round(avg_omega, 4),
            "avg_oos_rachev": round(avg_rachev, 4),
            "avg_oos_pf": round(avg_pf, 4),
            "omega_cv": round(omega_cv, 4),
            "median_max_drawdown": round(mdd_median, 6),
            "fold_sharpe": round(sr_val, 6),
            "n_tamrs_viable_folds": n_viable,
            "n_total_folds": n_folds,
            "pbo": round(pbo_scores.get(bid, -1.0), 4),
            "pbo_pass": pbo_scores.get(bid, 0.5) < 0.50,
            "bootstrap_rejected": bootstrap_rejected.get(bid, False),
            "survived_all_stages": bid in final_bids,
            "gt_composite": round(gt_scores.get(bid, 0.0), 6) if bid in final_bids else None,
        }

        # Add bootstrap CI details if available
        if not bootstrap_df.is_empty():
            boot_row = bootstrap_df.filter(pl.col("barrier_id") == bid)
            if not boot_row.is_empty():
                boot_dict = boot_row.to_dicts()[0]
                barrier_info["omega_ci_lower"] = round(boot_dict.get("omega_ci_lower", 0.0), 4)
                barrier_info["omega_ci_upper"] = round(boot_dict.get("omega_ci_upper", 0.0), 4)
                barrier_info["rachev_ci_lower"] = round(boot_dict.get("rachev_ci_lower", 0.0), 4)

        top_barriers.append(barrier_info)

    # Fold metadata
    fold_meta = build_fold_metadata(folds, signal_df, purge_bars=purge_bars)

    t_total = time.monotonic() - t0

    # Build combo summary
    combo = {
        "schema_version": 1,
        "direction": "SHORT" if strategy != "standard" else "LONG",
        "formation": formation,
        "strategy": strategy,
        "symbol": symbol,
        "threshold": threshold,
        "n_signals": n_unique_signals,
        "n_wf_folds": len(folds),
        "n_barriers_tested": df.select("barrier_id").n_unique(),
        "low_power": len(folds) < 3,
        "fold_metadata": fold_meta,
        "vorob_stability": vorob_result,
        "top_barriers": top_barriers,
        "stage2_cpcv": {
            "n_cpcv_folds": len(cpcv_folds),
            "n_top_k_screened": len(top_bids),
            "n_pbo_pass": sum(1 for v in pbo_scores.values() if v < 0.50),
            "n_pbo_fail": sum(1 for v in pbo_scores.values() if v >= 0.50),
            "pbo_scores": {k: round(v, 4) for k, v in pbo_scores.items()},
        } if pbo_scores else None,
        "stage3_bootstrap": {
            "n_pbo_survivors_in": len(surviving_bids),  # input: passed PBO < 0.50
            "n_bootstrap_accepted": sum(1 for v in bootstrap_rejected.values() if not v),  # CI above threshold
            "n_bootstrap_rejected": sum(1 for v in bootstrap_rejected.values() if v),  # CI below threshold
            "n_final_survivors": len(final_bids),  # output: passed all stages
            "final_barrier_ids": final_bids,
        } if surviving_bids else None,
        "stage4_ranking": {
            "n_trials_dsr": max(len(final_bids), 2),  # DSR n_trials = survivor count (not 434)
            "n_gt_scored": len(gt_scores),
            "gt_scores": {k: round(v, 6) for k, v in sorted(gt_scores.items(), key=lambda x: -x[1])},
            "top_gt_barrier": max(gt_scores, key=gt_scores.get) if gt_scores else None,
            "regime_detection": "skipped:no_lookback_features_in_tsv",
        } if gt_scores else None,
        "environment": {
            "sql_template": f"gen720_wf_{formation}_template.sql",
            "sql_template_sha256": _sha256_file(tsv_path) if tsv_path.exists() else "",
            "tsv_file": f"raw/{tsv_path.name}",
            "tsv_row_count": len(df),
            "bar_count_aligned": 0,
            "end_ts_ms": 0,
        },
        "timing": {
            "tsv_load_s": round(t_load, 2),
            "fold_build_s": round(t_fold, 2),
            "barrier_eval_s": round(t_eval, 2),
            "vorob_s": round(t_vorob, 2),
            "cpcv_s": round(t_cpcv, 2),
            "bootstrap_s": round(t_boot, 2),
            "total_s": round(t_total, 2),
        },
        "provenance": provenance_dict(include_env=True),
    }

    # Add formation/symbol/threshold to fold results for Tier 1
    fold_results = fold_results.with_columns(
        pl.lit(formation).alias("formation"),
        pl.lit(strategy).alias("strategy"),
        pl.lit(symbol).alias("symbol"),
        pl.lit(threshold).alias("threshold"),
    )

    return fold_results, combo


def _empty_combo_summary(
    formation: str, symbol: str, threshold: int, strategy: str,
    n_signals: int, tsv_path: Path,
) -> dict:
    """Return empty combo summary when no folds generated."""
    return {
        "schema_version": 1,
        "direction": "SHORT" if strategy != "standard" else "LONG",
        "formation": formation,
        "strategy": strategy,
        "symbol": symbol,
        "threshold": threshold,
        "n_signals": n_signals,
        "n_wf_folds": 0,
        "n_barriers_tested": 0,
        "low_power": True,
        "fold_metadata": [],
        "vorob_stability": None,
        "top_barriers": [],
        "environment": {
            "sql_template": f"gen720_wf_{formation}_template.sql",
            "sql_template_sha256": "",
            "tsv_file": f"raw/{tsv_path.name}",
            "tsv_row_count": 0,
            "bar_count_aligned": 0,
            "end_ts_ms": 0,
        },
        "timing": {"tsv_load_s": 0, "fold_build_s": 0, "barrier_eval_s": 0, "vorob_s": 0, "total_s": 0},
        "provenance": provenance_dict(include_env=True),
    }


# ---- Cross-Formation / Cross-Asset Aggregation ----


def aggregate_cross_formation(combo_summaries: list[dict]) -> dict:
    """Aggregate barrier performance across formations.

    For each barrier, count how many formations it works on
    (OOS Omega > 1.0 AND consistency > 50%).
    """
    formations = sorted({c["formation"] for c in combo_summaries})
    n_formations = len(formations)

    # Collect per-barrier stats across formations
    barrier_xf = {}
    for combo in combo_summaries:
        for b in combo.get("top_barriers", []):
            bid = b["barrier_id"]
            if bid not in barrier_xf:
                barrier_xf[bid] = {"formations_positive": []}
            if b["avg_oos_omega"] > 1.0 and b["consistency"] > 0.5:
                barrier_xf[bid]["formations_positive"].append(combo["formation"])

    # Deduplicate formation lists (barrier may appear in multiple combos of same formation)
    per_barrier_xf = {}
    for bid, data in barrier_xf.items():
        unique_fmts = sorted(set(data["formations_positive"]))
        per_barrier_xf[bid] = {
            "n_formations_positive": len(unique_fmts),
            "formations_positive": unique_fmts,
        }

    # Find barriers universal across all formations
    universal = [
        bid for bid, data in per_barrier_xf.items()
        if data["n_formations_positive"] == n_formations
    ]

    return {
        "n_formations": n_formations,
        "per_barrier_xf_consistency": per_barrier_xf,
        "barriers_universal": universal,
    }


def aggregate_cross_asset(combo_summaries: list[dict]) -> dict:
    """Aggregate barrier performance across assets.

    For each combo, check if any barrier achieves Omega > 1.0 OOS.
    """
    n_total = len(combo_summaries)
    n_positive = sum(
        1 for c in combo_summaries
        if any(b["avg_oos_omega"] > 1.0 for b in c.get("top_barriers", []))
    )

    # Per-formation summary
    per_formation = {}
    for combo in combo_summaries:
        fmt = combo["formation"]
        if fmt not in per_formation:
            per_formation[fmt] = {"n_tamrs_viable": 0, "n_total": 0, "omegas": [], "rachevs": []}
        per_formation[fmt]["n_total"] += 1
        top_omega = max((b["avg_oos_omega"] for b in combo.get("top_barriers", [])), default=0)
        top_rachev = max((b["avg_oos_rachev"] for b in combo.get("top_barriers", [])), default=0)
        per_formation[fmt]["omegas"].append(top_omega)
        per_formation[fmt]["rachevs"].append(top_rachev)
        if top_omega > 1.0:
            per_formation[fmt]["n_tamrs_viable"] += 1

    per_formation_summary = {}
    for fmt, data in per_formation.items():
        per_formation_summary[fmt] = {
            "n_tamrs_viable": data["n_tamrs_viable"],
            "n_total": data["n_total"],
            "avg_oos_omega": round(float(np.mean(data["omegas"])), 4) if data["omegas"] else 0.0,
            "avg_oos_rachev": round(float(np.mean(data["rachevs"])), 4) if data["rachevs"] else 0.0,
        }

    return {
        "n_combos_tested": n_total,
        "n_combos_positive_oos": n_positive,
        "xa_consistency": round(n_positive / n_total, 4) if n_total > 0 else 0.0,
        "per_formation_summary": per_formation_summary,
    }


def aggregate_short_strategies(combo_summaries: list[dict]) -> dict:
    """Compare Strategy A (mirrored) vs Strategy B (reverse) for SHORT.

    Groups by base formation (exh_s, 2up_ng_s) and compares strategies.
    """
    # Map formation → strategy → combos
    by_base = {}
    for combo in combo_summaries:
        fmt = combo["formation"]
        strategy = combo["strategy"]
        base = fmt.replace("_rev", "")
        if base not in by_base:
            by_base[base] = {}
        if strategy not in by_base[base]:
            by_base[base][strategy] = []
        by_base[base][strategy].append(combo)

    comparison = {}
    for base, strategies in by_base.items():
        entry = {}
        for strat_name, combos in strategies.items():
            n_positive = sum(
                1 for c in combos
                if any(b["avg_oos_omega"] > 1.0 for b in c.get("top_barriers", []))
            )
            avg_oos = float(np.mean([
                max((b["avg_oos_omega"] for b in c.get("top_barriers", [])), default=0)
                for c in combos
            ])) if combos else 0.0
            avg_consistency = float(np.mean([
                max((b["consistency"] for b in c.get("top_barriers", [])), default=0)
                for c in combos
            ])) if combos else 0.0

            entry[strat_name] = {
                "n_combos_positive": n_positive,
                "avg_oos_return": round(avg_oos, 4),
                "avg_consistency": round(avg_consistency, 4),
            }

        comparison[base] = entry

    return comparison


# ---- Knee Detection + TOPSIS ----


def run_knee_and_topsis(combo_summaries: list[dict]) -> tuple[dict, list[dict]]:
    """Run knee detection and TOPSIS on cross-asset barrier matrix.

    Matrix columns: avg_oos_omega (↑), xa_consistency (↑), omega_cv (↓)
    """
    # Collect per-barrier aggregated stats
    barrier_stats = {}
    for combo in combo_summaries:
        for b in combo.get("top_barriers", []):
            bid = b["barrier_id"]
            if bid not in barrier_stats:
                barrier_stats[bid] = {"omegas": [], "rachevs": [], "consistencies": [], "cvs": []}
            barrier_stats[bid]["omegas"].append(b["avg_oos_omega"])
            barrier_stats[bid]["rachevs"].append(b["avg_oos_rachev"])
            barrier_stats[bid]["consistencies"].append(b["consistency"])
            barrier_stats[bid]["cvs"].append(b["omega_cv"])

    if len(barrier_stats) < 3:
        return {"n_knee_points": 0, "knee_barrier_ids": [], "epsilon": config.RANK_KNEE_EPSILON}, []

    bids = sorted(barrier_stats.keys())
    matrix = np.array([
        [
            float(np.nanmean(barrier_stats[bid]["omegas"])),
            float(np.nanmean(barrier_stats[bid]["consistencies"])),
            float(np.nanmean(barrier_stats[bid]["cvs"])),
        ]
        for bid in bids
    ])

    # Filter out rows with NaN/Inf (from combos with 0 folds)
    finite_mask = np.all(np.isfinite(matrix), axis=1)
    if finite_mask.sum() < 3:
        return {"n_knee_points": 0, "knee_barrier_ids": [], "epsilon": config.RANK_KNEE_EPSILON}, []
    matrix = matrix[finite_mask]
    bids = [b for b, m in zip(bids, finite_mask) if m]

    # Types: omega=benefit(1), consistency=benefit(1), cv=cost(-1)
    types = np.array([1, 1, -1])

    # Knee detection
    knee_idx = knee_detect(matrix, types, epsilon=config.RANK_KNEE_EPSILON)
    knee_bids = [bids[i] for i in knee_idx]
    knee_analysis = {
        "n_knee_points": len(knee_idx),
        "knee_barrier_ids": knee_bids,
        "epsilon": config.RANK_KNEE_EPSILON,
    }

    # TOPSIS ranking (equal weights for 3 criteria)
    weights = np.ones(matrix.shape[1]) / matrix.shape[1]
    topsis_scores = topsis_rank(matrix, weights, types)
    topsis_ranking = []
    ranked_indices = np.argsort(-topsis_scores)
    for rank, idx in enumerate(ranked_indices[:20], 1):
        topsis_ranking.append({
            "barrier_id": bids[idx],
            "topsis_score": round(float(topsis_scores[idx]), 4),
            "rank": rank,
        })

    return knee_analysis, topsis_ranking


def _run_aggregation(
    direction: str,
    combo_summaries: list[dict],
    n_processed: int,
    t_start: float,
    t_wf: float,
    out_dir: Path,
    agg_jsonl_name: str,
    parquet_name: str = "long_folds.parquet",
    combo_jsonl_name: str = "long_combos.jsonl",
) -> None:
    """Run Tier 3 aggregation: cross-formation, cross-asset, knee, TOPSIS.

    Extracted so both normal pipeline completion and --aggregate-only can call it.
    """
    t_agg_start = time.monotonic()

    # Cross-formation
    xf = aggregate_cross_formation(combo_summaries)

    # Cross-asset
    xa = aggregate_cross_asset(combo_summaries)

    # Direction-specific analysis
    if direction == "short":
        strategy_comparison = aggregate_short_strategies(combo_summaries)
    else:
        strategy_comparison = None

    # Knee + TOPSIS
    knee_analysis, topsis_ranking = run_knee_and_topsis(combo_summaries)

    t_agg = time.monotonic() - t_agg_start
    t_total = time.monotonic() - t_start

    # Build Tier 3 aggregation record
    agg = {
        "schema_version": 1,
        "direction": direction.upper(),
        "data_lineage": {
            "fold_parquet": f"folds/{parquet_name}",
            "combo_jsonl": f"combos/{combo_jsonl_name}",
            "raw_tsv_dir": "raw/",
            "n_raw_tsv_files": n_processed,
            "n_combo_records": len(combo_summaries),
        },
        "per_combo_summary": [
            {
                "formation": c["formation"],
                "symbol": c["symbol"],
                "threshold": c["threshold"],
                "strategy": c.get("strategy", "standard"),
                "n_signals": c["n_signals"],
                "n_wf_folds": c["n_wf_folds"],
                "low_power": c["low_power"],
                "vorob_deviation": (c["vorob_stability"]["vorob_deviation"]
                                    if c.get("vorob_stability") else None),
                "top_barrier": c["top_barriers"][0]["barrier_id"] if c.get("top_barriers") else None,
                "top_barrier_consistency": c["top_barriers"][0]["consistency"] if c.get("top_barriers") else None,
                # Stage 2/3/4 summaries
                "n_pbo_pass": c["stage2_cpcv"]["n_pbo_pass"] if c.get("stage2_cpcv") else None,
                "n_bootstrap_pass": (
                    c["stage3_bootstrap"]["n_bootstrap_accepted"]
                    if c.get("stage3_bootstrap") else None
                ),
                "n_final_survivors": c["stage3_bootstrap"]["n_final_survivors"] if c.get("stage3_bootstrap") else None,
                "top_gt_composite": c["stage4_ranking"]["gt_scores"].get(
                    c["stage4_ranking"]["top_gt_barrier"], 0.0
                ) if c.get("stage4_ranking") and c["stage4_ranking"].get("top_gt_barrier") else None,
            }
            for c in combo_summaries
        ],
        "cross_formation": xf,
        "cross_asset": xa,
        "knee_analysis": knee_analysis,
        "topsis_ranking": topsis_ranking,
        "timing": {
            "total_wf_s": round(t_wf, 1),
            "aggregation_s": round(t_agg, 1),
            "total_s": round(t_total, 1),
        },
        "provenance": provenance_dict(include_env=True),
    }

    if strategy_comparison:
        agg["strategy_comparison"] = strategy_comparison

    # Validate against Pydantic schema (log warning on failure, don't block)
    try:
        WFAggregationV1.model_validate(agg)
    except (ValueError, KeyError) as e:
        print(f"WARNING: Tier 3 schema validation failed: {e}")

    agg_path = out_dir / agg_jsonl_name
    with open(agg_path, "w") as f:
        f.write(json.dumps(agg, default=str) + "\n")
    print(f"Tier 3 JSONL: {agg_path}")

    # ---- Summary ----
    print(f"\n{'='*60}")
    print(f"Gen720-{'L' if direction == 'long' else 'S'} Summary:")
    print(f"  Combos: {n_processed} processed ({len(combo_summaries)} total)")
    print(f"  XA consistency: {xa['xa_consistency']:.1%} positive OOS")
    print(f"  XF universal barriers: {len(xf.get('barriers_universal', []))}")
    print(f"  Knee points: {knee_analysis['n_knee_points']}")
    if topsis_ranking:
        print(f"  TOPSIS #1: {topsis_ranking[0]['barrier_id']} "
              f"(score={topsis_ranking[0]['topsis_score']:.4f})")
    print(f"  Total time: {t_total:.1f}s")


# ---- Main Orchestrator ----


def _fetch_remote_tsv(remote_spec: str, tsv_name: str, local_path: Path) -> bool:
    """Fetch a single TSV from remote host via rsync. Returns True if successful.

    Args:
        remote_spec: "host:/remote/dir" (e.g., "bigblack:/tmp/gen720_tsv")
        tsv_name: filename (e.g., "exh_l_SOLUSDT_500.tsv")
        local_path: local destination path
    """
    result = subprocess.run(
        ["rsync", "-q", f"{remote_spec}/{tsv_name}", str(local_path)],
        capture_output=True, timeout=300, check=False,
    )
    return result.returncode == 0 and local_path.exists() and local_path.stat().st_size > 0


def run_direction(direction: str, remote: str | None = None, *, aggregate_only: bool = False) -> None:
    """Run full WFO pipeline for one direction (LONG or SHORT).

    If remote is set (e.g., "bigblack:/tmp/gen720_tsv"), fetch TSVs from remote
    host one at a time, process, then delete the local copy to save disk space.

    If aggregate_only is True, skip all WFO processing and load combo summaries
    from existing Tier 2 JSONL, then run Tier 3 aggregation only.
    """
    out_dir = _get_output_dir()

    if direction == "long":
        formations = LONG_FORMATIONS
        strategy_map = {f: "standard" for f in formations}
        parquet_name = "long_folds.parquet"
        combo_jsonl_name = "long_combos.jsonl"
        agg_jsonl_name = "gen720_long.jsonl"
    else:
        formations = SHORT_FORMATIONS_A + SHORT_FORMATIONS_B
        strategy_map = {}
        for f in SHORT_FORMATIONS_A:
            strategy_map[f] = "A_mirrored"
        for f in SHORT_FORMATIONS_B:
            strategy_map[f] = "B_reverse"
        parquet_name = "short_folds.parquet"
        combo_jsonl_name = "short_combos.jsonl"
        agg_jsonl_name = "gen720_short.jsonl"

    print(f"Gen720 Walk-Forward Barrier Optimization: {direction.upper()}")
    print(f"  Formations: {len(formations)}")
    print(f"  Symbols: {len(SYMBOLS)}")
    print(f"  Thresholds: {THRESHOLDS}")
    print(f"  Max combos: {len(formations) * len(SYMBOLS) * len(THRESHOLDS)}")
    if remote:
        print(f"  Remote streaming: {remote}")
    if aggregate_only:
        print("  Mode: AGGREGATE-ONLY (Tier 3 from existing Tier 2 JSONL)")
    print()

    t_start = time.monotonic()

    # ---- Aggregate-only mode: load from existing combo data ----
    if aggregate_only:
        combos_dir = out_dir / "combos"
        folds_dir = out_dir / "folds"
        combo_path = combos_dir / combo_jsonl_name

        combo_summaries = []

        # Build set of valid formation names for this direction
        valid_formations = set(formations)

        # Try JSONL first, then fall back to individual JSON files
        if combo_path.exists():
            with open(combo_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        rec = json.loads(line)
                        if rec.get("formation") in valid_formations:
                            combo_summaries.append(rec)
            print(f"Loaded {len(combo_summaries)} combos from {combo_path}")
        else:
            # Load from individual _combo_*.json files (pueue --single-combo mode)
            # Filter by formation prefix to match this direction
            json_files = sorted(combos_dir.glob("_combo_*.json"))
            if not json_files:
                print(f"ERROR: No combo data in {combos_dir}. Run pipeline first.")
                sys.exit(1)
            skipped = 0
            for jf in json_files:
                with open(jf) as f:
                    rec = json.loads(f.read())
                if rec.get("formation") in valid_formations:
                    combo_summaries.append(rec)
                else:
                    skipped += 1
            print(f"Loaded {len(combo_summaries)} combos from JSON files"
                  f" (skipped {skipped} other-direction)")

            # Merge direction-specific JSONs into Tier 2 JSONL
            with open(combo_path, "w") as f:
                for combo in combo_summaries:
                    f.write(json.dumps(combo, default=str) + "\n")
            print(f"Wrote Tier 2 JSONL: {combo_path}")

        # Merge Parquet chunks if merged file doesn't exist yet
        parquet_path = folds_dir / parquet_name
        if not parquet_path.exists():
            chunk_files = sorted(folds_dir.glob("_chunk_*.parquet"))
            if chunk_files:
                chunk_dfs = [pl.read_parquet(p) for p in chunk_files]
                full_fold_df = pl.concat(chunk_dfs)
                full_fold_df.write_parquet(parquet_path, compression="zstd")
                print(f"Merged {len(chunk_files)} chunks → {parquet_path} ({len(full_fold_df)} rows)")
                del full_fold_df, chunk_dfs
                gc.collect()
                for p in chunk_files:
                    p.unlink(missing_ok=True)
            else:
                print("WARNING: No fold Parquet chunks to merge")

        n_processed = len(combo_summaries)

        # Jump to Tier 3 aggregation
        t_wf = 0.0
        return _run_aggregation(
            direction, combo_summaries, n_processed, t_start, t_wf,
            out_dir, agg_jsonl_name, parquet_name, combo_jsonl_name,
        )

    # Subprocess isolation: each combo runs in a child process to prevent
    # memory fragmentation from large TSV loads (300MB-1.6GB each).
    # Child writes fold Parquet chunk + combo JSON, then exits — OS fully
    # reclaims memory. Parent collects results from disk.
    folds_dir = out_dir / "folds"
    combos_dir = out_dir / "combos"
    folds_dir.mkdir(parents=True, exist_ok=True)
    combos_dir.mkdir(parents=True, exist_ok=True)

    combo_summaries = []
    n_processed = 0
    n_skipped = 0

    python_exe = str(Path(sys.executable))
    script_path = str(Path(__file__))

    for fmt in formations:
        for sym in SYMBOLS:
            for thr in THRESHOLDS:
                strategy = strategy_map[fmt]
                combo_idx = n_processed + n_skipped + 1

                # Resume: skip combos that already have output files
                combo_json_path = combos_dir / f"_combo_{fmt}_{sym}_{thr}.json"
                if combo_json_path.exists():
                    with open(combo_json_path) as f:
                        combo_summaries.append(json.loads(f.read()))
                    n_processed += 1
                    continue

                print(f"  [{combo_idx}] {fmt} {sym}@{thr} ({strategy})...", end="", flush=True)

                # Run combo in subprocess for memory isolation
                cmd = [
                    python_exe, script_path,
                    "--direction", direction,
                    "--single-combo", f"{fmt},{sym},{thr}",
                ]
                if remote:
                    cmd.extend(["--remote", remote])

                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=1800,
                        check=False,  # We handle exit codes below
                    )
                except subprocess.TimeoutExpired:
                    print(" TIMEOUT (>1800s)")
                    n_skipped += 1
                    continue

                # Parse subprocess output (last line: "OK|..." or "FAIL|...")
                stdout_lines = result.stdout.strip().splitlines()
                last_line = stdout_lines[-1] if stdout_lines else ""

                if last_line.startswith("OK|"):
                    msg = last_line[3:]
                    print(f" {msg}")
                    n_processed += 1

                    # Read combo summary from disk
                    combo_json_path = combos_dir / f"_combo_{fmt}_{sym}_{thr}.json"
                    if combo_json_path.exists():
                        with open(combo_json_path) as f:
                            combo_summaries.append(json.loads(f.read()))
                elif last_line.startswith("FAIL|"):
                    msg = last_line[5:]
                    if msg.startswith("SKIP:"):
                        n_skipped += 1
                        # Don't print for skips — too noisy
                    else:
                        print(f" {msg}")
                        n_skipped += 1
                else:
                    # Unexpected output or crash
                    stderr_tail = result.stderr[-200:] if result.stderr else ""
                    print(f" CRASH (exit={result.returncode}): {stderr_tail}")
                    n_skipped += 1

    t_wf = time.monotonic() - t_start
    print(f"\nProcessed {n_processed} combos, skipped {n_skipped}, in {t_wf:.1f}s")

    if not combo_summaries:
        print("ERROR: No combos processed. Check results/eval/gen720/raw/ for TSV files.")
        sys.exit(1)

    # ---- Tier 1: Merge per-combo Parquet chunks ----
    parquet_path = folds_dir / parquet_name
    chunk_files = sorted(folds_dir.glob("_chunk_*.parquet"))
    if chunk_files:
        chunk_dfs = [pl.read_parquet(p) for p in chunk_files]
        full_fold_df = pl.concat(chunk_dfs)
        full_fold_df.write_parquet(parquet_path, compression="zstd")
        print(f"Tier 1 Parquet: {parquet_path} ({len(full_fold_df)} rows)")
        del full_fold_df, chunk_dfs
        gc.collect()
        # Clean up chunk files
        for p in chunk_files:
            p.unlink(missing_ok=True)
    else:
        print("WARNING: No fold data to write to Parquet")

    # ---- Tier 2: Write combo JSONL (merge individual JSON files) ----
    combo_path = combos_dir / combo_jsonl_name
    with open(combo_path, "w") as f:
        for combo in combo_summaries:
            f.write(json.dumps(combo, default=str) + "\n")
    print(f"Tier 2 JSONL: {combo_path} ({len(combo_summaries)} combos)")
    # Clean up individual combo JSON files
    for p in combos_dir.glob("_combo_*.json"):
        p.unlink(missing_ok=True)

    # ---- Tier 3: Aggregation ----
    _run_aggregation(
        direction, combo_summaries, n_processed, t_start, t_wf,
        out_dir, agg_jsonl_name, parquet_name, combo_jsonl_name,
    )


def _run_single_combo(
    fmt: str, sym: str, thr: int, strategy: str,
    remote: str | None, raw_dir: Path, folds_dir: Path, combos_dir: Path,
) -> tuple[bool, str]:
    """Process a single combo in isolation.

    Writes fold Parquet chunk + combo JSONL. Returns (success, message).
    Called by parent via subprocess to ensure full memory reclamation.
    """
    tsv_name = f"{fmt}_{sym}_{thr}.tsv"
    tsv_path = raw_dir / tsv_name
    fetched_remote = False

    if not tsv_path.exists() and remote:
        tsv_path.parent.mkdir(parents=True, exist_ok=True)
        if _fetch_remote_tsv(remote, tsv_name, tsv_path):
            fetched_remote = True
        else:
            return False, "SKIP:fetch_failed"
    elif not tsv_path.exists():
        return False, "SKIP:not_found"

    try:
        df = load_tsv(tsv_path)
        fold_df, combo = run_combo_wfo(df, fmt, sym, thr, strategy, tsv_path)
        del df

        # Write fold Parquet chunk
        chunk_path = folds_dir / f"_chunk_{fmt}_{sym}_{thr}.parquet"
        if not fold_df.is_empty():
            fold_df.write_parquet(chunk_path, compression="zstd")

        # Write combo summary as single JSONL line
        combo_line_path = combos_dir / f"_combo_{fmt}_{sym}_{thr}.json"
        with open(combo_line_path, "w") as f:
            f.write(json.dumps(combo, default=str))

        n_folds = combo["n_wf_folds"]
        t = combo["timing"]["total_s"]
        s2 = combo.get("stage2_cpcv")
        s3 = combo.get("stage3_bootstrap")
        pbo_info = f" PBO:{s2['n_pbo_pass']}/{s2['n_top_k_screened']}" if s2 else ""
        boot_info = f" Boot:{s3['n_final_survivors']}/{s3['n_pbo_survivors_in']}" if s3 else ""
        return True, f"{n_folds} folds{pbo_info}{boot_info}, {t:.1f}s"

    except (ValueError, RuntimeError, OSError) as e:
        # Write low_power combo JSON stub so aggregation knows about this combo
        combo_line_path = combos_dir / f"_combo_{fmt}_{sym}_{thr}.json"
        if not combo_line_path.exists():
            n_sig = 0
            try:
                n_sig = load_tsv(tsv_path).select("signal_ts_ms").n_unique()
            except (ValueError, OSError, pl.exceptions.ComputeError):
                print(f"    Could not count signals from {tsv_path.name}")
            try:
                stub = _empty_combo_summary(
                    fmt, sym, thr, strategy, n_sig, tsv_path,
                )
                stub["error"] = str(e)
                with open(combo_line_path, "w") as f:
                    f.write(json.dumps(stub, default=str))
            except (OSError, TypeError) as write_err:
                print(f"    Could not write stub combo JSON: {write_err}")
        return False, f"ERROR:{e}"
    finally:
        if fetched_remote and tsv_path.exists():
            tsv_path.unlink()


def main():
    parser = argparse.ArgumentParser(description="Gen720 Walk-Forward Barrier Optimization")
    parser.add_argument(
        "--direction", required=True, choices=["long", "short"],
        help="Direction to analyze (LONG and SHORT are strictly isolated)",
    )
    parser.add_argument(
        "--remote", default=None,
        help="Stream TSVs from remote host (e.g., bigblack:/tmp/gen720_tsv). "
             "Fetches one at a time, processes, deletes local copy.",
    )
    parser.add_argument(
        "--aggregate-only", action="store_true",
        help="Skip WFO processing; read existing combo JSONL and run Tier 3 aggregation only. "
             "Use after pipeline completed Tier 1+2 but crashed during aggregation.",
    )
    parser.add_argument(
        "--single-combo", default=None,
        help="Process a single combo: FMT,SYM,THR (e.g., wl1d,BTCUSDT,750). "
             "Used internally for subprocess isolation.",
    )
    args = parser.parse_args()

    if args.single_combo:
        # Subprocess mode: process one combo and exit
        fmt, sym, thr_s = args.single_combo.split(",")
        thr = int(thr_s)
        direction = args.direction

        if direction == "long":
            strategy = "standard"
        elif fmt.endswith("_rev"):
            strategy = "B_reverse"
        else:
            strategy = "A_mirrored"

        raw_dir = _get_raw_dir()
        out_dir = _get_output_dir()
        folds_dir = out_dir / "folds"
        combos_dir = out_dir / "combos"
        folds_dir.mkdir(parents=True, exist_ok=True)
        combos_dir.mkdir(parents=True, exist_ok=True)

        ok, msg = _run_single_combo(
            fmt, sym, thr, strategy, args.remote,
            raw_dir, folds_dir, combos_dir,
        )
        # Write result to stdout for parent to parse
        print(f"{'OK' if ok else 'FAIL'}|{msg}")
        sys.exit(0 if ok else 1)

    run_direction(args.direction, remote=args.remote, aggregate_only=args.aggregate_only)


if __name__ == "__main__":
    main()
