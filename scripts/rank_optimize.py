"""Optuna evolutionary optimizer for per-metric percentile cutoffs.

Searches the 12-dimensional integer cutoff space to find optimal
per-metric thresholds. 5 objective functions selectable via
RBP_RANK_OBJECTIVE env var.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/17
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import optuna

from rangebar_patterns import config
from rangebar_patterns.eval._io import results_dir
from rangebar_patterns.eval.ranking import (
    DEFAULT_METRICS,
    load_metric_data,
    run_ranking_with_cutoffs,
)

# Silence Optuna's verbose logging
optuna.logging.set_verbosity(optuna.logging.WARNING)


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


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


def suggest_cutoffs(trial: optuna.Trial) -> dict[str, int]:
    """Suggest cutoff values for each metric."""
    cutoffs = {}
    for spec in DEFAULT_METRICS:
        cutoffs[spec.name] = trial.suggest_int(spec.name, 5, 100, step=5)
    return cutoffs


def main():
    repo_root = Path(__file__).resolve().parent.parent
    output_dir = repo_root / "results" / "eval"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "rank_optimization.jsonl"

    git_commit = _git_commit()
    timestamp = datetime.now(tz=UTC).isoformat()
    provenance = {
        "git_commit": git_commit,
        "timestamp": timestamp,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
    }

    objective_name = config.RANK_OBJECTIVE
    n_trials = config.RANK_N_TRIALS

    print("=" * 60)
    print("Rank Cutoff Optimizer (Optuna)")
    print("=" * 60)
    print(f"  Objective: {objective_name}")
    print(f"  N trials:  {n_trials}")
    print(f"  Target N:  {config.RANK_TARGET_N}")

    # Pre-load metric data once (shared across all trials)
    rd = results_dir()
    metric_data = load_metric_data(rd, DEFAULT_METRICS)
    n_configs = len({cid for values in metric_data.values() for cid in values})
    print(f"  Configs:   {n_configs}")
    print()

    if objective_name == "pareto_efficiency":
        # Multi-objective: maximize survivors, minimize mean cutoff
        study = optuna.create_study(
            directions=["maximize", "minimize"],
            sampler=optuna.samplers.NSGAIISampler(seed=42),
        )

        def pareto_objective(trial: optuna.Trial) -> tuple[float, float]:
            cutoffs = suggest_cutoffs(trial)
            result = run_ranking_with_cutoffs(cutoffs, rd=rd, metric_data=metric_data)
            return float(result["n_intersection"]), sum(cutoffs.values()) / len(cutoffs)

        study.optimize(pareto_objective, n_trials=n_trials)

        # Collect Pareto front
        pareto_front = []
        for t in study.best_trials:
            cutoffs = {spec.name: t.params[spec.name] for spec in DEFAULT_METRICS}
            pareto_front.append({
                "number": t.number,
                "n_survivors": int(t.values[0]),
                "mean_cutoff": round(t.values[1], 2),
                "cutoffs": cutoffs,
            })

        pareto_front.sort(key=lambda x: (-x["n_survivors"], x["mean_cutoff"]))

        print(f"Pareto front: {len(pareto_front)} solutions")
        for pf in pareto_front[:10]:
            print(f"  Survivors={pf['n_survivors']} MeanCut={pf['mean_cutoff']:.1f}")

        record = {
            "objective": objective_name,
            "n_trials": n_trials,
            "best_value": None,
            "best_cutoffs": pareto_front[0]["cutoffs"] if pareto_front else None,
            "best_n_survivors": pareto_front[0]["n_survivors"] if pareto_front else 0,
            "best_mean_cutoff": pareto_front[0]["mean_cutoff"] if pareto_front else None,
            "env_vars": _cutoffs_to_env(pareto_front[0]["cutoffs"]) if pareto_front else "",
            "pareto_front": pareto_front,
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
            cutoffs = suggest_cutoffs(trial)
            result = run_ranking_with_cutoffs(cutoffs, rd=rd, metric_data=metric_data)
            return obj_fn(result, cutoffs)

        study.optimize(objective, n_trials=n_trials)

        best = study.best_trial
        best_cutoffs = {spec.name: best.params[spec.name] for spec in DEFAULT_METRICS}
        best_result = run_ranking_with_cutoffs(best_cutoffs, rd=rd, metric_data=metric_data)

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
