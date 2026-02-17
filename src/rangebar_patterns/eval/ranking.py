# FILE-SIZE-OK
"""Per-metric percentile ranking with configurable cutoffs and intersection.

Independent from screening.py — reads the same JSONL result files but computes
percentile ranks per metric, applies per-metric cutoff filters, and reports the
intersection of configs passing all cutoffs. Designed for evolutionary optimization
of cutoff parameters via Optuna.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/17
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

from rangebar_patterns import config
from rangebar_patterns.eval._io import load_jsonl, results_dir


@dataclass(frozen=True)
class MetricSpec:
    """Specification for a single ranking metric."""

    name: str
    label: str
    higher_is_better: bool
    default_cutoff: int
    source_file: str
    source_field: str


# Kelly formally removed as metric per Issue #17 (contradictory with TAMRS,
# rewards temporal clustering, pathological false positives). See commit 4ee7980.
DEFAULT_METRICS: tuple[MetricSpec, ...] = (
    MetricSpec("tamrs", "TAMRS", True, 100, "tamrs_rankings.jsonl", "tamrs"),
    MetricSpec("rachev", "Rachev", True, 100, "tamrs_rankings.jsonl", "rachev_ratio"),
    MetricSpec("ou_ratio", "OU Ratio", True, 100, "tamrs_rankings.jsonl", "ou_barrier_ratio"),
    MetricSpec("sl_cdar", "SL/CDaR", True, 100, "tamrs_rankings.jsonl", "sl_cdar_ratio"),
    MetricSpec("omega", "Omega", True, 100, "omega_rankings.jsonl", "omega_L0"),
    MetricSpec("dsr", "DSR", True, 100, "dsr_rankings.jsonl", "dsr"),
    MetricSpec("headroom", "MinBTL Headroom", True, 100, "minbtl_gate.jsonl", "headroom_ratio"),
    MetricSpec("evalue", "E-value", True, 100, "evalues.jsonl", "final_evalue"),
    MetricSpec("regularity_cv", "Regularity CV", False, 100, "signal_regularity_rankings.jsonl", "kde_peak_cv"),
    MetricSpec("coverage", "Coverage", True, 100, "signal_regularity_rankings.jsonl", "temporal_coverage"),
    MetricSpec("n_trades", "Trade Count", True, 100, "moments.jsonl", "n_trades"),
)

# Cross-asset metrics from Gen500 sweep (logs/gen500/*.jsonl)
# Appended to DEFAULT_METRICS when cross_asset_rankings.jsonl exists.
# Uses profit_factor (≈ Omega at L=0) instead of Kelly per Issue #17 decision.
CROSS_ASSET_METRICS: tuple[MetricSpec, ...] = (
    MetricSpec("xa_n_positive", "XA Positive Assets", True, 100, "cross_asset_rankings.jsonl", "xa_n_positive"),
    MetricSpec("xa_avg_pf", "XA Avg PF", True, 100, "cross_asset_rankings.jsonl", "xa_avg_pf"),
    MetricSpec("xa_total_signals", "XA Total Signals", True, 100, "cross_asset_rankings.jsonl", "xa_total_signals"),
    MetricSpec("xa_consistency", "XA Consistency", True, 100, "cross_asset_rankings.jsonl", "xa_consistency"),
)


def get_all_metrics(rd: Path | None = None) -> tuple[MetricSpec, ...]:
    """Return DEFAULT_METRICS + CROSS_ASSET_METRICS if cross-asset data exists."""
    if rd is None:
        rd = results_dir()
    xa_path = rd / "cross_asset_rankings.jsonl"
    if xa_path.exists():
        return DEFAULT_METRICS + CROSS_ASSET_METRICS
    return DEFAULT_METRICS


def filter_discriminating_metrics(
    specs: tuple[MetricSpec, ...],
    metric_data: dict[str, dict[str, float | None]],
    min_unique_ratio: float = 0.05,
) -> tuple[MetricSpec, ...]:
    """Remove metrics with poor discriminating power.

    A metric is degenerate if the fraction of unique non-None values
    relative to total non-None values is below min_unique_ratio.
    Example: DSR where 960/961 values are 0.0 → ratio = 2/961 = 0.002 → excluded.

    Returns filtered tuple of MetricSpecs. Degenerate metrics get cutoff=100
    (no filter) automatically since they aren't in the returned specs.
    """
    kept = []
    for spec in specs:
        values = metric_data.get(spec.name, {})
        non_none = [v for v in values.values() if v is not None]
        if not non_none:
            continue
        n_unique = len(set(round(v, 8) for v in non_none))
        ratio = n_unique / len(non_none)
        if ratio >= min_unique_ratio:
            kept.append(spec)
    return tuple(kept)


def _safe_float(v) -> float | None:
    """Convert value to float, returning None for non-finite or missing."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    return f


def load_metric_data(
    rd: Path, specs: tuple[MetricSpec, ...] = DEFAULT_METRICS
) -> dict[str, dict[str, float | None]]:
    """Load all metric JSONL files, return {metric_name: {config_id: raw_value}}.

    Missing files produce empty dicts (graceful degradation).
    """
    result: dict[str, dict[str, float | None]] = {}
    for spec in specs:
        path = rd / spec.source_file
        if not path.exists():
            result[spec.name] = {}
            continue
        data: dict[str, float | None] = {}
        for record in load_jsonl(path):
            cid = record.get("config_id")
            if cid is None:
                continue
            data[cid] = _safe_float(record.get(spec.source_field))
        result[spec.name] = data
    return result


def percentile_ranks(
    values: dict[str, float | None], higher_is_better: bool
) -> dict[str, float]:
    """Assign percentile rank [0, 100] to each config.

    None values get percentile 0 (worst).
    For 'lower is better' metrics, ranks are flipped so 100 = best.
    Uses scipy.stats.rankdata(method='average') for tie handling.
    """
    if not values:
        return {}

    config_ids = list(values.keys())
    raw = [values[cid] for cid in config_ids]

    # Separate None vs non-None
    valid_mask = [v is not None for v in raw]
    valid_ids = [cid for cid, m in zip(config_ids, valid_mask, strict=True) if m]
    valid_vals = [v for v, m in zip(raw, valid_mask, strict=True) if m]

    result: dict[str, float] = {}

    # None configs get rank 0
    for cid, m in zip(config_ids, valid_mask, strict=True):
        if not m:
            result[cid] = 0.0

    if not valid_vals:
        return result

    arr = np.array(valid_vals, dtype=float)
    n = len(arr)

    if not higher_is_better:
        arr = -arr

    ranks = rankdata(arr, method="average")
    pct = (ranks / n) * 100.0

    for cid, p in zip(valid_ids, pct, strict=True):
        result[cid] = round(float(p), 4)

    return result


def apply_cutoff(pct_ranks: dict[str, float], cutoff: int) -> set[str]:
    """Return config_ids in top cutoff%.

    cutoff=20 means "top 20%" → pct_rank >= 80.
    cutoff=100 → all survive.
    cutoff=0 → none survive.
    """
    if cutoff <= 0:
        return set()
    if cutoff >= 100:
        return set(pct_ranks.keys())

    threshold = 100.0 - cutoff
    return {cid for cid, pct in pct_ranks.items() if pct >= threshold}


def intersection(per_metric_pass: dict[str, set[str]]) -> set[str]:
    """Configs passing ALL metric cutoffs."""
    if not per_metric_pass:
        return set()
    sets = list(per_metric_pass.values())
    return sets[0].intersection(*sets[1:]) if len(sets) > 1 else sets[0]


def overlap_count(
    per_metric_pass: dict[str, set[str]], all_config_ids: list[str]
) -> dict[str, int]:
    """For each config, count how many metrics it passes."""
    counts: dict[str, int] = {}
    for cid in all_config_ids:
        counts[cid] = sum(1 for s in per_metric_pass.values() if cid in s)
    return counts


def tightening_analysis(
    all_pct_ranks: dict[str, dict[str, float]],
    cutoff_levels: list[int] | None = None,
) -> list[dict]:
    """Show intersection size at uniform cutoffs [100, 80, 60, 40, 20, 10, 5]."""
    if cutoff_levels is None:
        cutoff_levels = [100, 80, 60, 40, 20, 10, 5]

    results = []
    for cutoff in cutoff_levels:
        per_metric_pass = {}
        for metric_name, pct_ranks in all_pct_ranks.items():
            per_metric_pass[metric_name] = apply_cutoff(pct_ranks, cutoff)
        survivors = intersection(per_metric_pass)
        example = sorted(survivors)[0] if survivors else "-"
        results.append({
            "cutoff_pct": cutoff,
            "n_intersection": len(survivors),
            "example_survivor": example,
        })
    return results


def resolve_cutoffs(specs: tuple[MetricSpec, ...] = DEFAULT_METRICS) -> dict[str, int]:
    """Read per-metric cutoffs from config module."""
    cutoff_map = {
        "tamrs": config.RANK_CUT_TAMRS,
        "rachev": config.RANK_CUT_RACHEV,
        "ou_ratio": config.RANK_CUT_OU_RATIO,
        "sl_cdar": config.RANK_CUT_SL_CDAR,
        "omega": config.RANK_CUT_OMEGA,
        "dsr": config.RANK_CUT_DSR,
        "headroom": config.RANK_CUT_HEADROOM,
        "evalue": config.RANK_CUT_EVALUE,
        "regularity_cv": config.RANK_CUT_REGULARITY_CV,
        "coverage": config.RANK_CUT_COVERAGE,
        "n_trades": config.RANK_CUT_N_TRADES,
        # Cross-asset cutoffs
        "xa_n_positive": config.RANK_CUT_XA_N_POSITIVE,
        "xa_avg_pf": config.RANK_CUT_XA_AVG_PF,
        "xa_total_signals": config.RANK_CUT_XA_TOTAL_SIGNALS,
        "xa_consistency": config.RANK_CUT_XA_CONSISTENCY,
    }
    return {spec.name: cutoff_map.get(spec.name, spec.default_cutoff) for spec in specs}


def run_ranking_with_cutoffs(
    cutoffs: dict[str, int],
    specs: tuple[MetricSpec, ...] = DEFAULT_METRICS,
    rd: Path | None = None,
    metric_data: dict[str, dict[str, float | None]] | None = None,
) -> dict:
    """Run the full ranking pipeline with given cutoffs. API for Optuna.

    Returns dict with n_intersection, avg_percentile, survivors list,
    n_binding_metrics, and per-metric pass sets.
    """
    if rd is None:
        rd = results_dir()
    if metric_data is None:
        metric_data = load_metric_data(rd, specs)

    # Compute percentile ranks for each metric
    all_pct_ranks: dict[str, dict[str, float]] = {}
    for spec in specs:
        values = metric_data.get(spec.name, {})
        all_pct_ranks[spec.name] = percentile_ranks(values, spec.higher_is_better)

    # Collect all config IDs
    all_config_ids = sorted({
        cid for pct_ranks in all_pct_ranks.values() for cid in pct_ranks
    })

    # Apply cutoffs
    per_metric_pass: dict[str, set[str]] = {}
    for spec in specs:
        cutoff = cutoffs.get(spec.name, 100)
        per_metric_pass[spec.name] = apply_cutoff(all_pct_ranks[spec.name], cutoff)

    survivors = intersection(per_metric_pass)

    # Compute average percentile of survivors
    avg_pct = 0.0
    if survivors:
        total = 0.0
        count = 0
        for cid in survivors:
            for _metric_name, pct_ranks in all_pct_ranks.items():
                total += pct_ranks.get(cid, 0.0)
                count += 1
        avg_pct = total / count if count > 0 else 0.0

    # Count binding metrics (would change intersection if relaxed to 100)
    n_binding = 0
    for metric_name in per_metric_pass:
        if cutoffs.get(metric_name, 100) >= 100:
            continue
        relaxed = dict(per_metric_pass)
        relaxed[metric_name] = set(all_pct_ranks.get(metric_name, {}).keys())
        relaxed_survivors = intersection(relaxed)
        if len(relaxed_survivors) > len(survivors):
            n_binding += 1

    return {
        "n_intersection": len(survivors),
        "survivors": sorted(survivors),
        "avg_percentile": round(avg_pct, 4),
        "n_binding_metrics": n_binding,
        "all_pct_ranks": all_pct_ranks,
        "per_metric_pass": per_metric_pass,
        "all_config_ids": all_config_ids,
        "cutoffs": cutoffs,
        "metric_data": metric_data,
    }


def topsis_rank(
    matrix: np.ndarray,
    weights: np.ndarray,
    types: np.ndarray,
) -> np.ndarray:
    """Rank alternatives using TOPSIS with vector normalization (Hwang & Yoon, 1981).

    Args:
        matrix: Decision matrix (n_alternatives x n_criteria), raw values.
        weights: Importance weight per criterion (sums to 1 recommended).
        types: +1 for benefit (higher=better), -1 for cost (lower=better).

    Returns:
        Closeness coefficients [0, 1] per alternative (higher = better).
    """
    # Vector normalization (L2 norm per column — standard TOPSIS)
    norms = np.sqrt((matrix ** 2).sum(axis=0))
    norms[norms == 0] = 1.0
    normalized = matrix / norms

    # Weighted normalized decision matrix
    weighted = normalized * weights

    # Ideal and nadir points
    ideal = np.where(types == 1, weighted.max(axis=0), weighted.min(axis=0))
    nadir = np.where(types == 1, weighted.min(axis=0), weighted.max(axis=0))

    # Euclidean distances
    d_ideal = np.sqrt(((weighted - ideal) ** 2).sum(axis=1))
    d_nadir = np.sqrt(((weighted - nadir) ** 2).sum(axis=1))

    # Closeness coefficient
    denom = d_ideal + d_nadir
    denom[denom == 0] = 1.0
    return d_nadir / denom


def _flip_to_minimize(matrix: np.ndarray, types: np.ndarray) -> np.ndarray:
    """Flip maximization objectives to minimization (negate benefit columns).

    pymoo and moocore assume minimization. This negates columns where
    types==1 (benefit, higher=better) so they become cost objectives.

    Args:
        matrix: Decision matrix (n_alternatives x n_criteria).
        types: +1 for benefit (will be negated), -1 for cost (unchanged).

    Returns:
        Copy of matrix with benefit columns negated.
    """
    flipped = matrix.copy()
    for j in range(matrix.shape[1]):
        if types[j] == 1:
            flipped[:, j] = -flipped[:, j]
    return flipped


def knee_detect(
    matrix: np.ndarray,
    types: np.ndarray,
    epsilon: float = 0.125,
) -> np.ndarray:
    """Detect knee points on a Pareto front via tradeoff outlier analysis.

    Bypasses pymoo's buggy ``HighTradeoffPoints`` (hardcodes epsilon=0.125
    in ``_do()`` instead of using ``self.epsilon``).  Extracts the tradeoff
    calculation inline and delegates outlier detection to
    ``pymoo.core.decision_making.find_outliers_upper_tail``.

    WHEN 0 KNEE POINTS ARE FOUND
    ----------------------------
    ``find_outliers_upper_tail`` uses 2σ above mean as the outlier threshold
    (Deb & Gupta 2010). On narrow Pareto fronts (e.g., TOPSIS scores
    spanning 0.61–0.85), all tradeoff values cluster near the mean and
    none exceeds the 2σ threshold. This is *correct behaviour* — it means
    the front has no single pronounced "elbow" where sacrificing one
    objective yields disproportionate gains elsewhere.

    When ``knee_detect`` returns an empty array, the recommended fallback
    is to use TOPSIS rank #1 as the final selection. This is documented
    and expected — the orchestrator (walk_forward_barriers.py) already
    handles this by proceeding with TOPSIS ranking when n_knee_points=0.

    Alternative knee detection methods (not yet implemented, for future
    consideration if narrow fronts are common):
    - **Kneedle algorithm** (Satopaa et al. 2011): curvature-based,
      better for smooth 2D fronts. Less sensitive to score clustering.
    - **Gradient-based**: Second derivative of sorted TOPSIS scores.
    - **IQR-based**: Outliers > Q3 + 1.5*IQR (more lenient than 2σ).

    Args:
        matrix: Decision matrix (n_alternatives x n_criteria).
        types: +1 for benefit (higher=better), -1 for cost (lower=better).
        epsilon: Radius for neighbour queries (passed to ``NeighborFinder``).

    Returns:
        Integer indices of knee points.  Empty array if <3 points or if
        pymoo is unavailable.
    """
    if matrix.shape[0] < 3:
        return np.array([], dtype=int)

    try:
        from pymoo.core.decision_making import (
            NeighborFinder,
            find_outliers_upper_tail,
        )
    except ImportError:
        return np.array([], dtype=int)

    # 1. Flip to minimisation convention (pymoo assumes minimisation)
    F = _flip_to_minimize(matrix, types)

    # 2. Normalise to [0, 1] per column (required for epsilon-radius queries)
    col_min = F.min(axis=0)
    col_max = F.max(axis=0)
    col_range = col_max - col_min
    col_range[col_range == 0] = 1.0
    F_norm = (F - col_min) / col_range

    # 3. Per-point tradeoff: min sacrifice/gain ratio to all neighbours
    n = F_norm.shape[0]
    neighbors_finder = NeighborFinder(
        F_norm, epsilon=epsilon, n_min_neigbors="auto", consider_2d=False,
    )
    mu = np.full(n, -np.inf)
    for i in range(n):
        neighbors = neighbors_finder.find(i)
        diff = F_norm[neighbors] - F_norm[i]
        sacrifice = np.maximum(0, diff).sum(axis=1)
        gain = np.maximum(0, -diff).sum(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            tradeoff = sacrifice / gain
        mu[i] = np.nanmin(tradeoff)

    # 4. Outlier detection (indices >= 2σ above mean)
    result = find_outliers_upper_tail(mu)
    if result is None:
        return np.array([], dtype=int)
    return np.asarray(result, dtype=int)


def build_report(
    cutoffs: dict[str, int],
    all_pct_ranks: dict[str, dict[str, float]],
    per_metric_pass: dict[str, set[str]],
    survivors: set[str],
    all_config_ids: list[str],
    metric_data: dict[str, dict[str, float | None]],
    tightening: list[dict],
    specs: tuple[MetricSpec, ...] = DEFAULT_METRICS,
) -> str:
    """Generate human-readable markdown ranking report."""
    lines = [
        "# Per-Metric Percentile Ranking Report",
        "",
        "## 1. Cutoffs Applied",
        "",
        "| Metric | Cutoff (top X%) | Configs Passing |",
        "|--------|-----------------|-----------------|",
    ]
    for spec in specs:
        cutoff = cutoffs.get(spec.name, 100)
        n_pass = len(per_metric_pass.get(spec.name, set()))
        lines.append(f"| {spec.label} | {cutoff}% | {n_pass} |")

    lines.extend([
        "",
        f"**Intersection (pass ALL cutoffs)**: {len(survivors)} / {len(all_config_ids)} configs",
        "",
    ])

    # Intersection table
    if survivors:
        overlap_counts = overlap_count(per_metric_pass, list(survivors))
        sorted_survivors = sorted(survivors, key=lambda c: (
            -overlap_counts.get(c, 0),
            -sum(all_pct_ranks.get(m, {}).get(c, 0) for m in all_pct_ranks) / max(len(all_pct_ranks), 1),
        ))

        lines.extend([
            "## 2. Intersection Configs",
            "",
            "| Rank | Config ID | Avg Pct | " + " | ".join(s.label for s in specs) + " |",
            "|------|-----------|---------|" + "|".join("-" * (len(s.label) + 2) for s in specs) + "|",
        ])

        top_n = config.RANK_TOP_N
        for rank, cid in enumerate(sorted_survivors[:top_n], 1):
            avg = sum(all_pct_ranks.get(s.name, {}).get(cid, 0) for s in specs) / len(specs)
            pct_vals = " | ".join(
                f"{all_pct_ranks.get(s.name, {}).get(cid, 0):.1f}" for s in specs
            )
            lines.append(f"| {rank} | {cid[:55]} | {avg:.1f} | {pct_vals} |")
    else:
        lines.extend([
            "## 2. Intersection Configs",
            "",
            "**No configs pass all cutoffs at this tightness level.**",
        ])

    # Per-metric top lists
    lines.extend(["", "## 3. Per-Metric Top 10", ""])
    for spec in specs:
        pct_ranks = all_pct_ranks.get(spec.name, {})
        if not pct_ranks:
            continue
        top10 = sorted(pct_ranks.items(), key=lambda x: -x[1])[:10]
        raw = metric_data.get(spec.name, {})
        lines.extend([
            f"### {spec.label}",
            "",
            "| Rank | Config ID | Percentile | Raw Value |",
            "|------|-----------|------------|-----------|",
        ])
        for i, (cid, pct) in enumerate(top10, 1):
            rv = raw.get(cid)
            rv_str = f"{rv:.6f}" if rv is not None else "N/A"
            lines.append(f"| {i} | {cid[:55]} | {pct:.1f} | {rv_str} |")
        lines.append("")

    # Tightening analysis
    lines.extend([
        "## 4. Tightening Analysis (Uniform Cutoffs)",
        "",
        "| Cutoff | Intersection Size | Example Survivor |",
        "|--------|-------------------|------------------|",
    ])
    for t in tightening:
        lines.append(
            f"| {t['cutoff_pct']}% | {t['n_intersection']} | {t['example_survivor'][:50]} |"
        )

    # Env var format
    active = {k: v for k, v in cutoffs.items() if v < 100}
    if active:
        env_str = " ".join(f"RBP_RANK_CUT_{k.upper()}={v}" for k, v in sorted(active.items()))
    else:
        env_str = "(all cutoffs at 100% — no filtering)"
    lines.extend([
        "",
        "## 5. Evolutionary Search Ready",
        "",
        "Current cutoffs as env vars:",
        "",
        "```bash",
        f"{env_str} mise run eval:rank",
        "```",
        "",
    ])

    return "\n".join(lines) + "\n"


def main():
    print("=== Per-Metric Percentile Ranking ===\n")

    rd = results_dir()
    specs = DEFAULT_METRICS
    cutoffs = resolve_cutoffs(specs)

    print(f"Cutoffs: {cutoffs}")

    result = run_ranking_with_cutoffs(cutoffs, specs, rd)
    all_pct_ranks = result["all_pct_ranks"]
    per_metric_pass = result["per_metric_pass"]
    survivors = set(result["survivors"])
    all_config_ids = result["all_config_ids"]
    metric_data = result["metric_data"]

    print(f"Loaded {len(all_config_ids)} configs across {len(specs)} metrics")
    print(f"Intersection: {len(survivors)} configs pass all cutoffs")

    # Overlap counts
    overlaps = overlap_count(per_metric_pass, all_config_ids)

    # Tightening analysis
    tightening = tightening_analysis(all_pct_ranks)
    print("\nTightening Analysis:")
    for t in tightening:
        print(f"  {t['cutoff_pct']:>3}% → {t['n_intersection']} configs")

    # Write rankings.jsonl
    with open(rd / "rankings.jsonl", "w") as f:
        for cid in sorted(all_config_ids):
            record = {
                "config_id": cid,
                "in_intersection": cid in survivors,
                "n_metrics_passed": overlaps.get(cid, 0),
                "n_metrics_total": len(specs),
            }
            for spec in specs:
                record[f"pct_{spec.name}"] = all_pct_ranks.get(spec.name, {}).get(cid, 0.0)
            for spec in specs:
                raw = metric_data.get(spec.name, {}).get(cid)
                if raw is not None:
                    record[f"raw_{spec.name}"] = raw
            record["cutoffs_used"] = {k: v for k, v in cutoffs.items() if v < 100}
            f.write(json.dumps(record) + "\n")

    # Write report
    report = build_report(
        cutoffs, all_pct_ranks, per_metric_pass, survivors,
        all_config_ids, metric_data, tightening, specs,
    )
    with open(rd / "ranking_report.md", "w") as f:
        f.write(report)

    print("\n=== Ranking Complete ===")
    print(f"  Rankings: {rd / 'rankings.jsonl'}")
    print(f"  Report:   {rd / 'ranking_report.md'}")


if __name__ == "__main__":
    main()
