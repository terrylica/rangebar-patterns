#!/usr/bin/env python3
# FILE-SIZE-OK: standalone experiment script, self-contained by design
"""Gen720 Ranking Experiments — 5 diverse MCDM methods on WFO barrier data.

Each round produces self-contained JSON artifacts optimized for LLM post-forensic
analysis. See results/eval/gen720/ranking/_manifest.json for the experiment index.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/37

Usage:
    python scripts/gen720_ranking_experiments.py --direction long
    python scripts/gen720_ranking_experiments.py --direction short
    python scripts/gen720_ranking_experiments.py --cross-round
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import polars as pl
from scipy import stats

# Reuse existing TOPSIS implementation
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from rangebar_patterns.eval.ranking import topsis_rank  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results" / "eval" / "gen720"
RANKING_DIR = RESULTS / "ranking"

ROUND_DIRS = {
    1: "round1_entropy_topsis",
    2: "round2_promethee",
    3: "round3_stability_weighted",
    4: "round4_cross_consistency",
    5: "round5_bootstrap_stability",
}

FOLD_METRICS = ["profit_factor", "omega", "rachev", "cdar", "total_return", "win_rate", "max_drawdown"]
FOLD_TYPES = np.array([1, 1, 1, -1, 1, 1, -1])  # benefit/cost

COMBO_METRICS = ["avg_oos_omega", "avg_oos_rachev", "avg_oos_pf", "fold_sharpe", "consistency", "omega_cv"]
COMBO_TYPES = np.array([1, 1, 1, 1, 1, -1])

STABILITY_METRICS = ["profit_factor", "omega", "rachev", "total_return", "win_rate"]


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "unknown"


# ---------------------------------------------------------------------------
# Shared Infrastructure
# ---------------------------------------------------------------------------


def load_folds(direction: str) -> pl.LazyFrame:
    """Load fold-level Parquet, excluding degenerate slt000 barriers."""
    path = RESULTS / "folds" / f"{direction}_folds.parquet"
    return pl.scan_parquet(path).filter(~pl.col("barrier_id").str.contains("slt000"))


def load_combos(direction: str) -> list[dict]:
    """Load all combo JSON files for a direction."""
    pattern = f"_combo_{direction}_*.json"
    combo_dir = RESULTS / "combos"
    combos = []
    for f in sorted(combo_dir.glob(pattern)):
        combos.append(json.loads(f.read_text()))
    return combos


def load_baseline(direction: str) -> list[dict]:
    """Load baseline TOPSIS top-20 from gen720 JSONL."""
    path = RESULTS / f"gen720_{direction}.jsonl"
    for line in path.open():
        d = json.loads(line)
        if "topsis_ranking" in d:
            return d["topsis_ranking"][:20]
    return []


def barrier_medians(lf: pl.LazyFrame, metrics: list[str]) -> pl.DataFrame:
    """Compute per-barrier median of specified metrics."""
    return (
        lf.group_by("barrier_id")
        .agg([pl.col(m).median().alias(m) for m in metrics])
        .sort("barrier_id")
        .collect()
    )


def compare_to_baseline(
    ranking: list[dict], baseline: list[dict], all_scores: dict[str, float]
) -> dict:
    """Compute rank correlation and overlap vs baseline TOPSIS."""
    baseline_ids = [b["barrier_id"] for b in baseline[:20]]
    this_ids = [r["barrier_id"] for r in ranking[:20]]

    # Build full rank vectors for correlation (only barriers in both)
    baseline_order = {b["barrier_id"]: b["rank"] for b in baseline}
    this_order = {r["barrier_id"]: r["rank"] for r in ranking}
    common = sorted(set(baseline_order) & set(this_order))

    if len(common) >= 3:
        b_ranks = [baseline_order[c] for c in common]
        t_ranks = [this_order[c] for c in common]
        tau, _ = stats.kendalltau(b_ranks, t_ranks)
        rho, _ = stats.spearmanr(b_ranks, t_ranks)
    else:
        tau, rho = float("nan"), float("nan")

    # Top-10 Jaccard
    b10 = set(baseline_ids[:10])
    t10 = set(this_ids[:10])
    jaccard = len(b10 & t10) / len(b10 | t10) if (b10 | t10) else 0.0

    return {
        "baseline_method": "equal_weight_topsis_3metric",
        "kendall_tau": round(float(tau), 4) if not np.isnan(tau) else None,
        "spearman_rho": round(float(rho), 4) if not np.isnan(rho) else None,
        "top10_jaccard": round(jaccard, 4),
        "rank1_agreement": (baseline_ids[0] == this_ids[0]) if baseline_ids and this_ids else False,
        "baseline_top10": baseline_ids[:10],
        "this_top10": this_ids[:10],
    }


def build_ranking_list(
    bids: list[str], scores: np.ndarray, metrics_df: pl.DataFrame | None = None
) -> list[dict]:
    """Build sorted ranking list from barrier IDs and scores."""
    ranked_idx = np.argsort(-scores)
    ranking = []
    for rank, idx in enumerate(ranked_idx, 1):
        entry = {
            "rank": rank,
            "barrier_id": bids[idx],
            "score": round(float(scores[idx]), 6),
        }
        if metrics_df is not None:
            row = metrics_df.filter(pl.col("barrier_id") == bids[idx])
            if len(row) > 0:
                entry["metrics"] = {
                    c: round(float(row[c][0]), 6) if row[c][0] is not None else None
                    for c in row.columns
                    if c != "barrier_id"
                }
        ranking.append(entry)
    return ranking


def save_round(
    round_num: int,
    method: str,
    method_description: str,
    direction: str,
    ranking: list[dict],
    method_params: dict,
    comparison: dict,
    n_folds: int,
    data_source: str,
) -> Path:
    """Save self-contained round JSON."""
    slug = ROUND_DIRS[round_num]
    out_dir = RANKING_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{direction}.json"

    doc = {
        "meta": {
            "round": round_num,
            "method": method,
            "method_description": method_description,
            "direction": direction,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "n_barriers_ranked": len(ranking),
            "n_barriers_excluded": 62,
            "exclusion_reason": "slt000 (no stop-loss) barriers removed",
            "data_source": data_source,
            "n_folds_used": n_folds,
            "git_commit": _git_commit(),
        },
        "method_params": method_params,
        "ranking": ranking,
        "comparison_to_baseline": comparison,
    }

    out_path.write_text(json.dumps(doc, indent=2, default=str))
    return out_path


# ---------------------------------------------------------------------------
# Round 1: Entropy-Weighted TOPSIS (Fold-Level)
# ---------------------------------------------------------------------------


def entropy_weights(matrix: np.ndarray) -> np.ndarray:
    """Compute Shannon entropy weights for TOPSIS criteria."""
    # Min-max normalize to [0, 1]
    mins = matrix.min(axis=0)
    maxs = matrix.max(axis=0)
    ranges = maxs - mins
    ranges[ranges == 0] = 1.0
    normed = (matrix - mins) / ranges

    # Shift to avoid log(0)
    normed = normed + 1e-10
    # Normalize columns to proportions
    col_sums = normed.sum(axis=0)
    col_sums[col_sums == 0] = 1.0
    p = normed / col_sums

    # Shannon entropy
    n = matrix.shape[0]
    k = 1.0 / np.log(n)
    entropy = -k * (p * np.log(p)).sum(axis=0)

    # Divergence (1 - entropy) = information content
    divergence = 1.0 - entropy
    total = divergence.sum()
    if total == 0:
        return np.ones(matrix.shape[1]) / matrix.shape[1]
    return divergence / total


def run_round1(direction: str) -> tuple[list[dict], dict[str, float]]:
    """Round 1: Entropy-Weighted TOPSIS on fold-level medians."""
    lf = load_folds(direction)
    n_folds = lf.select(pl.len()).collect().item()
    medians = barrier_medians(lf, FOLD_METRICS)

    bids = medians["barrier_id"].to_list()
    matrix = medians.select(FOLD_METRICS).to_numpy()

    # Remove rows with NaN
    finite_mask = np.all(np.isfinite(matrix), axis=1)
    matrix = matrix[finite_mask]
    bids = [b for b, m in zip(bids, finite_mask) if m]

    weights = entropy_weights(matrix)
    scores = topsis_rank(matrix, weights, FOLD_TYPES)

    ranking = build_ranking_list(bids, scores, medians.filter(pl.col("barrier_id").is_in(bids)))
    all_scores = {r["barrier_id"]: r["score"] for r in ranking}
    baseline = load_baseline(direction)
    comparison = compare_to_baseline(ranking, baseline, all_scores)

    save_round(
        round_num=1,
        method="entropy_weighted_topsis",
        method_description="Shannon entropy auto-derives criterion weights from fold-level data. "
        "High-entropy columns (more discriminating) get higher weight.",
        direction=direction,
        ranking=ranking,
        method_params={
            "metrics": FOLD_METRICS,
            "types": FOLD_TYPES.tolist(),
            "entropy_weights": [round(float(w), 6) for w in weights],
            "data_level": "fold",
            "aggregation": "median",
        },
        comparison=comparison,
        n_folds=n_folds,
        data_source=f"results/eval/gen720/folds/{direction}_folds.parquet",
    )

    print(f"  Round 1 [{direction}]: #1 = {ranking[0]['barrier_id']} ({ranking[0]['score']:.4f})")
    print(f"    Entropy weights: {dict(zip(FOLD_METRICS, [round(w, 3) for w in weights]))}")
    tau, rho, j10 = comparison["kendall_tau"], comparison["spearman_rho"], comparison["top10_jaccard"]
    print(f"    vs baseline: tau={tau}, rho={rho}, J10={j10}")
    return ranking, all_scores


# ---------------------------------------------------------------------------
# Round 2: PROMETHEE II (Combo-Level)
# ---------------------------------------------------------------------------


def promethee_ii(matrix: np.ndarray, types: np.ndarray, q: np.ndarray, p: np.ndarray) -> np.ndarray:
    """PROMETHEE II net flow ranking (vectorized).

    Args:
        matrix: (n_alternatives, n_criteria) decision matrix
        types: +1 benefit, -1 cost per criterion
        q: indifference threshold per criterion
        p: strict preference threshold per criterion

    Returns:
        Net flow scores (higher = better).
    """
    n = matrix.shape[0]

    # Flip cost criteria so higher = better
    adjusted = matrix * types

    # Pairwise differences: d[i,j,c] = adjusted[i,c] - adjusted[j,c]
    d = adjusted[:, np.newaxis, :] - adjusted[np.newaxis, :, :]  # (n, n, k)

    # Linear preference function (Type V): P = (d - q) / (p - q), clipped to [0, 1]
    denom = p - q
    denom[denom == 0] = 1.0
    pref = np.clip((d - q) / denom, 0.0, 1.0)  # (n, n, k)

    # Aggregated preference index (equal weights)
    pi = pref.mean(axis=2)  # (n, n)

    # Positive and negative flows
    phi_plus = pi.sum(axis=1) / (n - 1)   # outgoing preference
    phi_minus = pi.sum(axis=0) / (n - 1)  # incoming preference

    return phi_plus - phi_minus  # net flow


def run_round2(direction: str) -> tuple[list[dict], dict[str, float]]:
    """Round 2: PROMETHEE II on combo-level metrics."""
    combos = load_combos(direction)
    n_folds = sum(c.get("n_wf_folds", 0) for c in combos)

    # Aggregate per-barrier medians from combo data
    barrier_data: dict[str, dict[str, list]] = {}
    for combo in combos:
        for b in combo.get("top_barriers", []):
            bid = b["barrier_id"]
            if "slt000" in bid:
                continue
            if bid not in barrier_data:
                barrier_data[bid] = {m: [] for m in COMBO_METRICS}
            for m in COMBO_METRICS:
                v = b.get(m)
                if v is not None and np.isfinite(v):
                    barrier_data[bid][m].append(v)

    bids = sorted(barrier_data.keys())
    matrix = np.array([
        [float(np.median(barrier_data[bid][m])) if barrier_data[bid][m] else 0.0 for m in COMBO_METRICS]
        for bid in bids
    ])

    # Remove NaN rows
    finite_mask = np.all(np.isfinite(matrix), axis=1)
    matrix = matrix[finite_mask]
    bids = [b for b, m in zip(bids, finite_mask) if m]

    # PROMETHEE preference thresholds: q=0, p=range/4
    ranges = matrix.max(axis=0) - matrix.min(axis=0)
    q = np.zeros(matrix.shape[1])
    p = ranges / 4.0
    p[p == 0] = 1.0

    scores = promethee_ii(matrix, COMBO_TYPES, q, p)

    # Build metrics df for output
    metrics_df = pl.DataFrame(
        [
            {"barrier_id": bids[i], **{m: float(matrix[i, j]) for j, m in enumerate(COMBO_METRICS)}}
            for i in range(len(bids))
        ]
    )
    ranking = build_ranking_list(bids, scores, metrics_df)
    all_scores = {r["barrier_id"]: r["score"] for r in ranking}
    baseline = load_baseline(direction)
    comparison = compare_to_baseline(ranking, baseline, all_scores)

    save_round(
        round_num=2,
        method="promethee_ii",
        method_description="Pairwise outranking with linear preference functions (Type V). "
        "Produces net flow ranking that handles incomparable alternatives better than TOPSIS.",
        direction=direction,
        ranking=ranking,
        method_params={
            "metrics": COMBO_METRICS,
            "types": COMBO_TYPES.tolist(),
            "preference_fn": "linear_type_v",
            "q_thresholds": q.tolist(),
            "p_thresholds": [round(float(x), 6) for x in p],
            "data_level": "combo",
            "aggregation": "median",
        },
        comparison=comparison,
        n_folds=n_folds,
        data_source=f"results/eval/gen720/combos/_combo_{direction}_*.json",
    )

    print(f"  Round 2 [{direction}]: #1 = {ranking[0]['barrier_id']} ({ranking[0]['score']:.4f})")
    tau, rho, j10 = comparison["kendall_tau"], comparison["spearman_rho"], comparison["top10_jaccard"]
    print(f"    vs baseline: tau={tau}, rho={rho}, J10={j10}")
    return ranking, all_scores


# ---------------------------------------------------------------------------
# Round 3: Stability-Weighted Composite (Fold-Level)
# ---------------------------------------------------------------------------


def run_round3(direction: str) -> tuple[list[dict], dict[str, float]]:
    """Round 3: Stability-weighted composite — median × (1/(1+CV))."""
    lf = load_folds(direction)
    n_folds = lf.select(pl.len()).collect().item()

    # Per-barrier: median and std for stability metrics
    agg_exprs = []
    for m in STABILITY_METRICS:
        agg_exprs.append(pl.col(m).median().alias(f"{m}_median"))
        agg_exprs.append(pl.col(m).std().alias(f"{m}_std"))

    stats_df = lf.group_by("barrier_id").agg(agg_exprs).sort("barrier_id").collect()
    bids = stats_df["barrier_id"].to_list()

    # Compute stability-weighted scores
    scores_per_metric = {}
    for m in STABILITY_METRICS:
        med = stats_df[f"{m}_median"].to_numpy().astype(float)
        std = stats_df[f"{m}_std"].to_numpy().astype(float)
        cv = np.where(np.abs(med) > 1e-10, std / np.abs(med), 10.0)  # cap CV for near-zero medians
        stability_weight = 1.0 / (1.0 + cv)
        raw = med * stability_weight
        scores_per_metric[m] = raw

    # Min-max normalize each metric to [0, 1] then sum
    normalized = np.zeros(len(bids))
    for m in STABILITY_METRICS:
        raw = scores_per_metric[m]
        rmin, rmax = raw.min(), raw.max()
        if rmax - rmin > 1e-10:
            normed = (raw - rmin) / (rmax - rmin)
        else:
            normed = np.zeros_like(raw)
        normalized += normed

    # Filter NaN
    finite_mask = np.isfinite(normalized)
    bids_f = [b for b, m in zip(bids, finite_mask) if m]
    scores_f = normalized[finite_mask]

    medians_df = barrier_medians(load_folds(direction), STABILITY_METRICS)
    ranking = build_ranking_list(bids_f, scores_f, medians_df.filter(pl.col("barrier_id").is_in(bids_f)))
    all_scores = {r["barrier_id"]: r["score"] for r in ranking}
    baseline = load_baseline(direction)
    comparison = compare_to_baseline(ranking, baseline, all_scores)

    save_round(
        round_num=3,
        method="stability_weighted_composite",
        method_description="Weight each barrier's median score by fold-to-fold stability (inverse CV). "
        "A consistent PF=1.08 beats a volatile PF=1.15.",
        direction=direction,
        ranking=ranking,
        method_params={
            "metrics": STABILITY_METRICS,
            "formula": "score = median × (1 / (1 + CV)), then min-max normalize, sum across metrics",
            "data_level": "fold",
        },
        comparison=comparison,
        n_folds=n_folds,
        data_source=f"results/eval/gen720/folds/{direction}_folds.parquet",
    )

    print(f"  Round 3 [{direction}]: #1 = {ranking[0]['barrier_id']} ({ranking[0]['score']:.4f})")
    tau, rho, j10 = comparison["kendall_tau"], comparison["spearman_rho"], comparison["top10_jaccard"]
    print(f"    vs baseline: tau={tau}, rho={rho}, J10={j10}")
    return ranking, all_scores


# ---------------------------------------------------------------------------
# Round 4: Cross-Asset × Cross-Formation Consistency
# ---------------------------------------------------------------------------


def run_round4(direction: str) -> tuple[list[dict], dict[str, float]]:
    """Round 4: Rank by universality — geometric mean of symbol/formation/threshold fractions."""
    lf = load_folds(direction)
    n_folds = lf.select(pl.len()).collect().item()

    # Per-barrier per-symbol: median PF > 1?
    sym_pf = (
        lf.group_by("barrier_id", "symbol")
        .agg(pl.col("profit_factor").median().alias("pf_median"))
        .with_columns((pl.col("pf_median") > 1.0).cast(pl.Int32).alias("above1"))
        .group_by("barrier_id")
        .agg([
            pl.col("above1").sum().alias("n_symbols_above1"),
            pl.col("above1").count().alias("n_symbols_total"),
        ])
        .collect()
    )

    # Per-barrier per-formation: median PF > 1?
    fmt_pf = (
        lf.group_by("barrier_id", "formation")
        .agg(pl.col("profit_factor").median().alias("pf_median"))
        .with_columns((pl.col("pf_median") > 1.0).cast(pl.Int32).alias("above1"))
        .group_by("barrier_id")
        .agg([
            pl.col("above1").sum().alias("n_formations_above1"),
            pl.col("above1").count().alias("n_formations_total"),
        ])
        .collect()
    )

    # Per-barrier per-threshold: median PF > 1?
    thr_pf = (
        lf.group_by("barrier_id", "threshold")
        .agg(pl.col("profit_factor").median().alias("pf_median"))
        .with_columns((pl.col("pf_median") > 1.0).cast(pl.Int32).alias("above1"))
        .group_by("barrier_id")
        .agg([
            pl.col("above1").sum().alias("n_thresholds_above1"),
            pl.col("above1").count().alias("n_thresholds_total"),
        ])
        .collect()
    )

    # Join all three
    joined = sym_pf.join(fmt_pf, on="barrier_id").join(thr_pf, on="barrier_id").sort("barrier_id")

    bids = joined["barrier_id"].to_list()
    sym_frac = (joined["n_symbols_above1"] / joined["n_symbols_total"]).to_numpy().astype(float)
    fmt_frac = (joined["n_formations_above1"] / joined["n_formations_total"]).to_numpy().astype(float)
    thr_frac = (joined["n_thresholds_above1"] / joined["n_thresholds_total"]).to_numpy().astype(float)

    # Geometric mean — handle zeros by clamping to small epsilon
    eps = 1e-6
    geo_mean = np.cbrt(np.maximum(sym_frac, eps) * np.maximum(fmt_frac, eps) * np.maximum(thr_frac, eps))

    # Build metrics df
    metrics_df = pl.DataFrame({
        "barrier_id": bids,
        "symbol_fraction": sym_frac,
        "formation_fraction": fmt_frac,
        "threshold_fraction": thr_frac,
    })

    ranking = build_ranking_list(bids, geo_mean, metrics_df)
    all_scores = {r["barrier_id"]: r["score"] for r in ranking}
    baseline = load_baseline(direction)
    comparison = compare_to_baseline(ranking, baseline, all_scores)

    save_round(
        round_num=4,
        method="cross_consistency",
        method_description="Rank by universality: geometric mean of (symbols with PF>1 fraction, "
        "formations with PF>1 fraction, thresholds with PF>1 fraction).",
        direction=direction,
        ranking=ranking,
        method_params={
            "metric": "profit_factor",
            "threshold": 1.0,
            "aggregation": "geometric_mean",
            "dimensions": ["symbol", "formation", "threshold"],
            "data_level": "fold",
        },
        comparison=comparison,
        n_folds=n_folds,
        data_source=f"results/eval/gen720/folds/{direction}_folds.parquet",
    )

    print(f"  Round 4 [{direction}]: #1 = {ranking[0]['barrier_id']} ({ranking[0]['score']:.4f})")
    print(f"    Symbol frac: {ranking[0].get('metrics', {}).get('symbol_fraction', '?')}")
    tau, rho, j10 = comparison["kendall_tau"], comparison["spearman_rho"], comparison["top10_jaccard"]
    print(f"    vs baseline: tau={tau}, rho={rho}, J10={j10}")
    return ranking, all_scores


# ---------------------------------------------------------------------------
# Round 5: Bootstrap Rank Stability
# ---------------------------------------------------------------------------


def run_round5(direction: str, n_bootstrap: int = 200, seed: int = 42) -> tuple[list[dict], dict[str, float]]:
    """Round 5: Bootstrap rank stability — resample folds, count top-10 frequency."""
    lf = load_folds(direction)
    n_folds_total = lf.select(pl.len()).collect().item()

    # Collect full data for resampling
    df = lf.select(["barrier_id", "fold_id"] + FOLD_METRICS).collect()

    # Get unique fold IDs for resampling
    fold_ids = df["fold_id"].unique().sort().to_list()
    n_folds = len(fold_ids)
    bids_all = sorted(df["barrier_id"].unique().to_list())
    bid_to_idx = {b: i for i, b in enumerate(bids_all)}
    n_barriers = len(bids_all)

    rng = np.random.default_rng(seed)  # noqa: S311
    top10_counts = np.zeros(n_barriers, dtype=int)

    for _ in range(n_bootstrap):
        # Resample fold IDs with replacement
        sampled_folds = rng.choice(fold_ids, size=n_folds, replace=True).tolist()
        resampled = df.filter(pl.col("fold_id").is_in(sampled_folds))

        # Per-barrier medians
        medians = (
            resampled.lazy()
            .group_by("barrier_id")
            .agg([pl.col(m).median().alias(m) for m in FOLD_METRICS])
            .sort("barrier_id")
            .collect()
        )

        r_bids = medians["barrier_id"].to_list()
        matrix = medians.select(FOLD_METRICS).to_numpy()

        finite_mask = np.all(np.isfinite(matrix), axis=1)
        if finite_mask.sum() < 3:
            continue
        matrix = matrix[finite_mask]
        r_bids = [b for b, m in zip(r_bids, finite_mask) if m]

        weights = entropy_weights(matrix)
        scores = topsis_rank(matrix, weights, FOLD_TYPES)

        # Record top-10
        top10_idx = np.argsort(-scores)[:10]
        for idx in top10_idx:
            bid = r_bids[idx]
            if bid in bid_to_idx:
                top10_counts[bid_to_idx[bid]] += 1

    # Score = frequency / n_bootstrap
    frequency = top10_counts / n_bootstrap
    ranking = build_ranking_list(bids_all, frequency)
    all_scores = {r["barrier_id"]: r["score"] for r in ranking}
    baseline = load_baseline(direction)
    comparison = compare_to_baseline(ranking, baseline, all_scores)

    save_round(
        round_num=5,
        method="bootstrap_rank_stability",
        method_description=f"Resample folds {n_bootstrap} times, run entropy-weighted TOPSIS each time, "
        "count top-10 appearances. High frequency = robust to fold selection.",
        direction=direction,
        ranking=ranking,
        method_params={
            "n_bootstrap": n_bootstrap,
            "seed": seed,
            "inner_method": "entropy_weighted_topsis",
            "metrics": FOLD_METRICS,
            "types": FOLD_TYPES.tolist(),
            "data_level": "fold",
            "top_k": 10,
        },
        comparison=comparison,
        n_folds=n_folds_total,
        data_source=f"results/eval/gen720/folds/{direction}_folds.parquet",
    )

    print(f"  Round 5 [{direction}]: #1 = {ranking[0]['barrier_id']} (freq={ranking[0]['score']:.3f})")
    tau, rho, j10 = comparison["kendall_tau"], comparison["spearman_rho"], comparison["top10_jaccard"]
    print(f"    vs baseline: tau={tau}, rho={rho}, J10={j10}")
    return ranking, all_scores


# ---------------------------------------------------------------------------
# Cross-Round Comparison
# ---------------------------------------------------------------------------


def run_cross_round_comparison():
    """Generate rank correlation matrix across all rounds × both directions."""
    results = {}

    for direction in ["long", "short"]:
        round_rankings: dict[int, dict[str, int]] = {}

        for rnum, slug in ROUND_DIRS.items():
            path = RANKING_DIR / slug / f"{direction}.json"
            if not path.exists():
                continue
            doc = json.loads(path.read_text())
            round_rankings[rnum] = {r["barrier_id"]: r["rank"] for r in doc["ranking"]}

        # Also include baseline (round 0)
        baseline = load_baseline(direction)
        if baseline:
            round_rankings[0] = {b["barrier_id"]: b["rank"] for b in baseline}

        # Pairwise Kendall tau and Spearman rho
        rounds = sorted(round_rankings.keys())
        tau_matrix = {}
        rho_matrix = {}

        for i in rounds:
            for j in rounds:
                common = sorted(set(round_rankings[i]) & set(round_rankings[j]))
                if len(common) >= 3:
                    ri = [round_rankings[i][c] for c in common]
                    rj = [round_rankings[j][c] for c in common]
                    tau, _ = stats.kendalltau(ri, rj)
                    rho, _ = stats.spearmanr(ri, rj)
                else:
                    tau, rho = float("nan"), float("nan")
                tau_matrix[f"{i}-{j}"] = round(float(tau), 4) if not np.isnan(tau) else None
                rho_matrix[f"{i}-{j}"] = round(float(rho), 4) if not np.isnan(rho) else None

        # Top-10 overlap matrix
        overlap_matrix = {}
        for i in rounds:
            sorted_i = sorted(round_rankings[i].items(), key=lambda x: x[1])[:10]
            top10_i = set(b for b, _ in sorted_i)
            for j in rounds:
                sorted_j = sorted(round_rankings[j].items(), key=lambda x: x[1])[:10]
                top10_j = set(b for b, _ in sorted_j)
                union = top10_i | top10_j
                overlap_matrix[f"{i}-{j}"] = round(len(top10_i & top10_j) / len(union), 4) if union else 0.0

        results[direction] = {
            "rounds_compared": rounds,
            "round_labels": {0: "baseline_topsis", **{k: v for k, v in ROUND_DIRS.items()}},
            "kendall_tau": tau_matrix,
            "spearman_rho": rho_matrix,
            "top10_jaccard": overlap_matrix,
        }

    out_path = RANKING_DIR / "cross_round_comparison.json"
    doc = {
        "experiment_set": "gen720_ranking",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "description": "Pairwise rank correlation (Kendall tau, Spearman rho) and top-10 Jaccard overlap "
        "across all ranking methods. Round 0 = baseline equal-weight TOPSIS.",
        "directions": results,
    }
    out_path.write_text(json.dumps(doc, indent=2))
    print(f"\nCross-round comparison saved to {out_path}")
    return doc


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def write_manifest():
    """Write _manifest.json — LLM entry point for experiment discovery."""
    baseline_long = load_baseline("long")
    baseline_short = load_baseline("short")

    manifest = {
        "experiment_set": "gen720_ranking",
        "created": datetime.now(timezone.utc).isoformat(),
        "n_rounds": 5,
        "directions": ["long", "short"],
        "baseline": {
            "method": "equal_weight_topsis_3metric",
            "metrics": ["avg_oos_omega", "xa_consistency", "omega_cv"],
            "long_rank1": baseline_long[0]["barrier_id"] if baseline_long else None,
            "short_rank1": baseline_short[0]["barrier_id"] if baseline_short else None,
        },
        "rounds": [
            {"round": 1, "slug": "entropy_topsis", "dir": "round1_entropy_topsis/",
             "method": "Entropy-Weighted TOPSIS", "data_level": "fold", "n_metrics": 7},
            {"round": 2, "slug": "promethee", "dir": "round2_promethee/",
             "method": "PROMETHEE II", "data_level": "combo", "n_metrics": 6},
            {"round": 3, "slug": "stability_weighted", "dir": "round3_stability_weighted/",
             "method": "Stability-Weighted Composite", "data_level": "fold", "n_metrics": 5},
            {"round": 4, "slug": "cross_consistency", "dir": "round4_cross_consistency/",
             "method": "Cross-Asset x Cross-Formation Consistency", "data_level": "fold", "n_metrics": 1},
            {"round": 5, "slug": "bootstrap_stability", "dir": "round5_bootstrap_stability/",
             "method": "Bootstrap Rank Stability", "data_level": "fold", "n_metrics": 7},
        ],
        "cross_round_file": "cross_round_comparison.json",
        "degenerate_filter": "slt000 barriers excluded (62 of 434 = 372 ranked)",
        "git_commit": _git_commit(),
    }

    path = RANKING_DIR / "_manifest.json"
    path.write_text(json.dumps(manifest, indent=2))
    print(f"Manifest saved to {path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Gen720 ranking experiments")
    parser.add_argument("--direction", choices=["long", "short"], help="Direction to run")
    parser.add_argument("--cross-round", action="store_true", help="Generate cross-round comparison")
    parser.add_argument("--round", type=int, choices=[1, 2, 3, 4, 5], help="Run specific round only")
    args = parser.parse_args()

    if args.cross_round:
        run_cross_round_comparison()
        write_manifest()
        return

    if not args.direction:
        parser.error("--direction required unless --cross-round")

    direction = args.direction
    print(f"\n{'='*60}")
    print(f"Gen720 Ranking Experiments — {direction.upper()}")
    print(f"{'='*60}\n")

    rounds_to_run = [args.round] if args.round else [1, 2, 3, 4, 5]

    for r in rounds_to_run:
        if r == 1:
            run_round1(direction)
        elif r == 2:
            run_round2(direction)
        elif r == 3:
            run_round3(direction)
        elif r == 4:
            run_round4(direction)
        elif r == 5:
            run_round5(direction)
        print()

    print("All rounds complete.")


if __name__ == "__main__":
    main()
