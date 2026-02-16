"""Optuna evolutionary optimizer for per-metric percentile cutoffs.

Searches the 12-dimensional integer cutoff space to find optimal
per-metric thresholds. 5 objective functions selectable via
RBP_RANK_OBJECTIVE env var.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/17
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import optuna

from rangebar_patterns import config
from rangebar_patterns.eval._io import provenance_dict, results_dir
from rangebar_patterns.eval.ranking import (
    DEFAULT_METRICS,
    filter_discriminating_metrics,
    get_all_metrics,
    knee_detect,
    load_metric_data,
    run_ranking_with_cutoffs,
    topsis_rank,
)

# Silence Optuna's verbose logging
optuna.logging.set_verbosity(optuna.logging.WARNING)


# ---- Objective Functions ----


def obj_max_survivors_min_cutoff(result: dict, cutoffs: dict[str, int]) -> float:
    """Maximize: survivors / mean_cutoff. Higher = more configs at tighter cutoffs."""
    n = result["n_intersection"]
    if n == 0:
        return 0.0
    mean_cutoff = sum(cutoffs.values()) / len(cutoffs)
    if mean_cutoff < 1:
        return 0.0
    return n / mean_cutoff


def obj_quality_at_target_n(result: dict, cutoffs: dict[str, int]) -> float:
    """Maximize avg percentile of survivors, penalize if fewer than target_n."""
    n = result["n_intersection"]
    avg_pct = result["avg_percentile"]
    target_n = config.RANK_TARGET_N
    if n < target_n:
        return avg_pct * (n / target_n)
    return avg_pct


def obj_tightest_nonempty(result: dict, cutoffs: dict[str, int]) -> float:
    """Minimize total cutoff budget while keeping >= 1 survivor."""
    n = result["n_intersection"]
    if n == 0:
        return 0.0
    total_budget = sum(cutoffs.values())
    max_budget = len(cutoffs) * 100
    return max_budget - total_budget


def obj_diversity_reward(result: dict, cutoffs: dict[str, int]) -> float:
    """Reward: survivors * unique_contribution_ratio."""
    n = result["n_intersection"]
    if n == 0:
        return 0.0
    n_binding = result["n_binding_metrics"]
    n_active = sum(1 for v in cutoffs.values() if v < 100)
    if n_active == 0:
        return 0.0
    efficiency = n_binding / n_active
    return n * efficiency


OBJECTIVES = {
    "max_survivors_min_cutoff": obj_max_survivors_min_cutoff,
    "quality_at_target_n": obj_quality_at_target_n,
    "tightest_nonempty": obj_tightest_nonempty,
    "pareto_efficiency": None,  # Special: multi-objective
    "diversity_reward": obj_diversity_reward,
}


def suggest_cutoffs(
    trial: optuna.Trial, specs: tuple | None = None
) -> dict[str, int]:
    """Suggest cutoff values for each metric."""
    if specs is None:
        specs = DEFAULT_METRICS
    cutoffs = {}
    for spec in specs:
        cutoffs[spec.name] = trial.suggest_int(spec.name, 5, 100, step=5)
    return cutoffs


def main():
    repo_root = Path(__file__).resolve().parent.parent
    output_dir = repo_root / "results" / "eval"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "rank_optimization.jsonl"

    provenance = provenance_dict()

    objective_name = config.RANK_OBJECTIVE
    n_trials = config.RANK_N_TRIALS

    print("=" * 60)
    print("Rank Cutoff Optimizer (Optuna)")
    print("=" * 60)
    print(f"  Objective: {objective_name}")
    print(f"  N trials:  {n_trials}")
    print(f"  Target N:  {config.RANK_TARGET_N}")

    # Pre-load metric data once (shared across all trials)
    # Use get_all_metrics() to auto-include cross-asset metrics when available
    rd = results_dir()
    all_specs_raw = get_all_metrics(rd)
    metric_data = load_metric_data(rd, all_specs_raw)
    n_configs = len({cid for values in metric_data.values() for cid in values})
    xa_active = len(all_specs_raw) > len(DEFAULT_METRICS)

    # Filter out degenerate metrics (e.g. DSR where 99.7% of values are identical)
    all_specs = filter_discriminating_metrics(all_specs_raw, metric_data)
    n_excluded = len(all_specs_raw) - len(all_specs)
    if n_excluded > 0:
        excluded = set(s.name for s in all_specs_raw) - set(s.name for s in all_specs)
        print(f"  Excluded:  {n_excluded} degenerate metrics ({', '.join(sorted(excluded))})")

    print(f"  Metrics:   {len(all_specs)} ({'+ cross-asset' if xa_active else 'single-asset only'})")
    print(f"  Configs:   {n_configs}")
    print()

    if objective_name == "pareto_efficiency":
        # Multi-objective NSGA-II: maximize survivors, maximize avg quality, minimize mean cutoff
        study = optuna.create_study(
            directions=["maximize", "maximize", "minimize"],
            sampler=optuna.samplers.NSGAIISampler(seed=42),
        )

        def pareto_objective(trial: optuna.Trial) -> tuple[float, float, float]:
            cutoffs = suggest_cutoffs(trial, specs=all_specs)
            result = run_ranking_with_cutoffs(
                cutoffs, specs=all_specs, rd=rd, metric_data=metric_data
            )
            return (
                float(result["n_intersection"]),
                result["avg_percentile"],
                sum(cutoffs.values()) / len(cutoffs),
            )

        study.optimize(pareto_objective, n_trials=n_trials)

        # Collect Pareto front
        pareto_front = []
        for t in study.best_trials:
            cutoffs = {spec.name: t.params[spec.name] for spec in all_specs}
            pareto_front.append({
                "number": t.number,
                "n_survivors": int(t.values[0]),
                "avg_quality": round(t.values[1], 2),
                "mean_cutoff": round(t.values[2], 2),
                "cutoffs": cutoffs,
            })

        # TOPSIS ranking of Pareto front (threshold-free, Issue #28)
        if pareto_front:
            topsis_matrix = np.array([
                [pf["n_survivors"], pf["avg_quality"], pf["mean_cutoff"]]
                for pf in pareto_front
            ], dtype=float)
            topsis_weights = np.array([1.0 / 3, 1.0 / 3, 1.0 / 3])
            topsis_types = np.array([1.0, 1.0, -1.0])  # survivors↑, quality↑, cutoff↓
            topsis_scores = topsis_rank(topsis_matrix, topsis_weights, topsis_types)
            for i, pf in enumerate(pareto_front):
                pf["topsis_score"] = round(float(topsis_scores[i]), 6)

        # Time TOPSIS (retroactive — already computed above)
        t0 = time.perf_counter_ns()
        _ = topsis_rank(topsis_matrix, topsis_weights, topsis_types) if pareto_front else None
        topsis_us = (time.perf_counter_ns() - t0) / 1000

        # Knee detection on Pareto front (Issue #28)
        knee_indices: list[int] = []
        knee_error: str | None = None
        t0 = time.perf_counter_ns()
        if pareto_front:
            try:
                ki = knee_detect(
                    topsis_matrix, topsis_types, epsilon=config.RANK_KNEE_EPSILON,
                )
                knee_indices = ki.tolist()
            except (ImportError, ValueError, RuntimeError) as exc:
                knee_error = str(exc)[:200]
        knee_us = (time.perf_counter_ns() - t0) / 1000

        # Annotate each Pareto solution
        knee_set = set(knee_indices)
        for i, pf in enumerate(pareto_front):
            pf["is_knee"] = i in knee_set

        # Sort by TOPSIS score (best first), fallback to old sort for empty scores
        pareto_front.sort(key=lambda x: -x.get("topsis_score", 0))

        print(f"Pareto front: {len(pareto_front)} solutions (TOPSIS-ranked)")
        for pf in pareto_front[:10]:
            knee_marker = " [KNEE]" if pf.get("is_knee") else ""
            print(
                f"  TOPSIS={pf.get('topsis_score', 0):.4f} "
                f"Survivors={pf['n_survivors']} "
                f"AvgQuality={pf['avg_quality']:.1f} "
                f"MeanCut={pf['mean_cutoff']:.1f}"
                f"{knee_marker}"
            )
        n_knees = sum(1 for pf in pareto_front if pf.get("is_knee"))
        print(f"  Knee points: {n_knees} (epsilon={config.RANK_KNEE_EPSILON})")

        record = {
            "objective": objective_name,
            "n_trials": n_trials,
            "n_metrics": len(all_specs),
            "cross_asset_active": xa_active,
            "best_value": None,
            "best_cutoffs": pareto_front[0]["cutoffs"] if pareto_front else None,
            "best_n_survivors": pareto_front[0]["n_survivors"] if pareto_front else 0,
            "best_avg_quality": pareto_front[0]["avg_quality"] if pareto_front else None,
            "best_mean_cutoff": pareto_front[0]["mean_cutoff"] if pareto_front else None,
            "env_vars": _cutoffs_to_env(pareto_front[0]["cutoffs"]) if pareto_front else "",
            "pareto_front": pareto_front,
            "knee_analysis": {
                "n_knee_points": n_knees,
                "knee_indices": knee_indices,
                "epsilon": config.RANK_KNEE_EPSILON,
                "error": knee_error,
            },
            "timing": {
                "topsis_us": round(topsis_us, 1),
                "knee_us": round(knee_us, 1),
                "total_mcdm_us": round(topsis_us + knee_us, 1),
            },
            "provenance": provenance,
        }

    else:
        # Single-objective
        obj_fn = OBJECTIVES[objective_name]
        study = optuna.create_study(
            direction="maximize",
            sampler=optuna.samplers.TPESampler(seed=42),
        )

        def objective(trial: optuna.Trial) -> float:
            cutoffs = suggest_cutoffs(trial, specs=all_specs)
            result = run_ranking_with_cutoffs(
                cutoffs, specs=all_specs, rd=rd, metric_data=metric_data
            )
            return obj_fn(result, cutoffs)

        study.optimize(objective, n_trials=n_trials)

        best = study.best_trial
        best_cutoffs = {spec.name: best.params[spec.name] for spec in all_specs}
        best_result = run_ranking_with_cutoffs(
            best_cutoffs, specs=all_specs, rd=rd, metric_data=metric_data
        )

        print(f"\nBest trial #{best.number}: value={best.value:.4f}")
        print(f"  Survivors:    {best_result['n_intersection']}")
        print(f"  Avg pctile:   {best_result['avg_percentile']:.2f}")
        print(f"  Binding:      {best_result['n_binding_metrics']}")
        print(f"  Cutoffs:      {best_cutoffs}")
        print("\n  Env vars:")
        env_str = _cutoffs_to_env(best_cutoffs)
        print(f"    {env_str}")

        record = {
            "objective": objective_name,
            "n_trials": n_trials,
            "best_value": round(best.value, 6),
            "best_cutoffs": best_cutoffs,
            "best_n_survivors": best_result["n_intersection"],
            "best_mean_cutoff": round(sum(best_cutoffs.values()) / len(best_cutoffs), 2),
            "env_vars": env_str,
            "pareto_front": None,
            "provenance": provenance,
        }

    with open(output_file, "w") as f:
        f.write(json.dumps(record) + "\n")

    print(f"\nOutput: {output_file}")
    return 0


def _cutoffs_to_env(cutoffs: dict[str, int]) -> str:
    """Convert cutoffs dict to env var string for copy-paste."""
    parts = []
    for name, val in sorted(cutoffs.items()):
        env_name = f"RBP_RANK_CUT_{name.upper()}"
        parts.append(f"{env_name}={val}")
    return " ".join(parts)


if __name__ == "__main__":
    sys.exit(main())
