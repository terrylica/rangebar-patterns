# FILE-SIZE-OK — self-contained benchmark script, splitting adds complexity without benefit
"""MCDM Benchmark POC — pymcdm TOPSIS vs pymoo knee-point vs NumPy TOPSIS.

Fail-fast POC benchmarking Multi-Criteria Decision Making methods on our
actual Pareto front from rank_optimization.jsonl (76 solutions, 11 metrics).
Also tests scale with generated benchmark data (1K, 10K, 50K strategies).

Performance is the primary concern — this determines which MCDM method
we integrate into rank_optimize.py for production WFO at scale.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/28
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Provenance (copied from tamrs_poc.py pattern)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_pareto_front(repo_root: Path) -> tuple[np.ndarray, list[str], list[str]]:
    """Load Pareto front from rank_optimization.jsonl.

    Returns (matrix, metric_names, solution_labels).
    Matrix shape: (n_solutions, n_metrics).
    """
    jsonl_path = repo_root / "results" / "eval" / "rank_optimization.jsonl"
    with open(jsonl_path) as f:
        data = json.loads(f.readline())

    pareto = data.get("pareto_front", [])
    if not pareto:
        print("ERROR: No pareto_front in rank_optimization.jsonl")
        sys.exit(1)

    # Filter out zero-survivor solutions
    pareto = [p for p in pareto if p["n_survivors"] > 0]

    # Extract the 3 objectives as our decision matrix
    # n_survivors (maximize), avg_quality (maximize), mean_cutoff (minimize)
    metric_names = ["n_survivors", "avg_quality", "mean_cutoff"]
    matrix = np.array([
        [p["n_survivors"], p["avg_quality"], p["mean_cutoff"]]
        for p in pareto
    ], dtype=float)

    labels = [f"trial_{p['number']}" for p in pareto]
    return matrix, metric_names, labels


def generate_benchmark_matrix(n_strategies: int, n_metrics: int, seed: int = 42) -> np.ndarray:  # noqa: fake-data
    """Generate benchmark matrix for scale testing (intentional for perf measurement)."""
    rng = np.random.default_rng(seed)  # noqa: fake-data
    return rng.random((n_strategies, n_metrics))


# ---------------------------------------------------------------------------
# Method 1: pymcdm TOPSIS
# ---------------------------------------------------------------------------

def bench_pymcdm_topsis(matrix: np.ndarray, weights: np.ndarray, types: np.ndarray) -> dict:
    """Benchmark pymcdm TOPSIS ranking."""
    from pymcdm.methods import TOPSIS

    topsis = TOPSIS()

    t0 = time.perf_counter_ns()
    rankings = topsis(matrix, weights, types)
    t1 = time.perf_counter_ns()

    elapsed_us = (t1 - t0) / 1000
    best_idx = int(np.argmax(rankings))

    return {
        "method": "pymcdm_topsis",
        "elapsed_us": round(elapsed_us, 1),
        "best_idx": best_idx,
        "best_score": round(float(rankings[best_idx]), 6),
        "top5_indices": [int(i) for i in np.argsort(rankings)[-5:][::-1]],
        "top5_scores": [round(float(rankings[i]), 6) for i in np.argsort(rankings)[-5:][::-1]],
        "all_scores": [round(float(s), 6) for s in rankings],
    }


# ---------------------------------------------------------------------------
# Method 2: pymoo HighTradeoffPoints (knee-point detection)
# ---------------------------------------------------------------------------

def bench_pymoo_knee(matrix: np.ndarray, types: np.ndarray) -> dict:
    """Benchmark pymoo knee-point detection on Pareto front."""
    from pymoo.mcdm.high_tradeoff import HighTradeoffPoints

    # pymoo expects minimization — flip maximization objectives
    # types: 1 = maximize (benefit), -1 = minimize (cost)
    flipped = matrix.copy()
    for j in range(matrix.shape[1]):
        if types[j] == 1:  # maximize → flip to minimize
            flipped[:, j] = -flipped[:, j]

    # Normalize to [0,1] for knee detection
    mins = flipped.min(axis=0)
    maxs = flipped.max(axis=0)
    denom = maxs - mins
    denom[denom == 0] = 1.0
    normalized = (flipped - mins) / denom

    t0 = time.perf_counter_ns()
    try:
        htp = HighTradeoffPoints()
        knee_indices = htp.do(normalized)
        t1 = time.perf_counter_ns()
        elapsed_us = (t1 - t0) / 1000

        return {
            "method": "pymoo_knee_point",
            "elapsed_us": round(elapsed_us, 1),
            "n_knee_points": len(knee_indices),
            "knee_indices": [int(i) for i in knee_indices],
        }
    except (ValueError, IndexError, RuntimeError) as e:
        t1 = time.perf_counter_ns()
        return {
            "method": "pymoo_knee_point",
            "elapsed_us": round((t1 - t0) / 1000, 1),
            "error": str(e),
            "n_knee_points": 0,
            "knee_indices": [],
        }


# ---------------------------------------------------------------------------
# Method 3: pymoo CompromiseProgramming
# ---------------------------------------------------------------------------

def bench_pymoo_pseudo_weights(matrix: np.ndarray, weights: np.ndarray, types: np.ndarray) -> dict:
    """Benchmark pymoo PseudoWeights decision-making."""
    from pymoo.mcdm.pseudo_weights import PseudoWeights

    # Flip for minimization
    flipped = matrix.copy()
    for j in range(matrix.shape[1]):
        if types[j] == 1:
            flipped[:, j] = -flipped[:, j]

    # Normalize
    mins = flipped.min(axis=0)
    maxs = flipped.max(axis=0)
    denom = maxs - mins
    denom[denom == 0] = 1.0
    normalized = (flipped - mins) / denom

    t0 = time.perf_counter_ns()
    try:
        pw = PseudoWeights(weights)
        idx = pw.do(normalized)
        t1 = time.perf_counter_ns()
        elapsed_us = (t1 - t0) / 1000

        return {
            "method": "pymoo_pseudo_weights",
            "elapsed_us": round(elapsed_us, 1),
            "best_idx": int(idx) if idx is not None else None,
        }
    except (ValueError, IndexError, RuntimeError, AttributeError) as e:
        t1 = time.perf_counter_ns()
        return {
            "method": "pymoo_pseudo_weights",
            "elapsed_us": round((t1 - t0) / 1000, 1),
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# Method 4: Pure NumPy TOPSIS (zero library overhead)
# ---------------------------------------------------------------------------

def bench_numpy_topsis(matrix: np.ndarray, weights: np.ndarray, types: np.ndarray) -> dict:
    """Benchmark pure NumPy TOPSIS implementation."""
    t0 = time.perf_counter_ns()

    # Step 1: Normalize (vector normalization)
    norms = np.sqrt((matrix ** 2).sum(axis=0))
    norms[norms == 0] = 1.0
    normalized = matrix / norms

    # Step 2: Weighted normalized
    weighted = normalized * weights

    # Step 3: Ideal and Nadir points
    ideal = np.where(types == 1, weighted.max(axis=0), weighted.min(axis=0))
    nadir = np.where(types == 1, weighted.min(axis=0), weighted.max(axis=0))

    # Step 4: Euclidean distances
    d_ideal = np.sqrt(((weighted - ideal) ** 2).sum(axis=1))
    d_nadir = np.sqrt(((weighted - nadir) ** 2).sum(axis=1))

    # Step 5: Closeness coefficient
    denom = d_ideal + d_nadir
    denom[denom == 0] = 1.0
    scores = d_nadir / denom

    t1 = time.perf_counter_ns()
    elapsed_us = (t1 - t0) / 1000
    best_idx = int(np.argmax(scores))

    return {
        "method": "numpy_topsis",
        "elapsed_us": round(elapsed_us, 1),
        "best_idx": best_idx,
        "best_score": round(float(scores[best_idx]), 6),
        "top5_indices": [int(i) for i in np.argsort(scores)[-5:][::-1]],
        "top5_scores": [round(float(scores[i]), 6) for i in np.argsort(scores)[-5:][::-1]],
        "ideal_point": [round(float(v), 6) for v in ideal],
        "nadir_point": [round(float(v), 6) for v in nadir],
        "all_scores": [round(float(s), 6) for s in scores],
    }


# ---------------------------------------------------------------------------
# Method 5: moocore hypervolume
# ---------------------------------------------------------------------------

def bench_moocore_hypervolume(matrix: np.ndarray, types: np.ndarray) -> dict:
    """Benchmark moocore hypervolume calculation."""
    try:
        import moocore
    except ImportError:
        return {"method": "moocore_hypervolume", "error": "moocore not installed", "elapsed_us": 0}

    # moocore expects minimization
    flipped = matrix.copy()
    for j in range(matrix.shape[1]):
        if types[j] == 1:
            flipped[:, j] = -flipped[:, j]

    # Reference point: worst value per objective + margin
    ref_point = flipped.max(axis=0) + 1.0

    t0 = time.perf_counter_ns()
    try:
        hv = moocore.hypervolume(flipped, ref=ref_point)
        t1 = time.perf_counter_ns()
        elapsed_us = (t1 - t0) / 1000

        return {
            "method": "moocore_hypervolume",
            "elapsed_us": round(elapsed_us, 1),
            "hypervolume": round(float(hv), 6),
            "ref_point": [round(float(v), 4) for v in ref_point],
        }
    except (ValueError, TypeError, RuntimeError) as e:
        t1 = time.perf_counter_ns()
        return {
            "method": "moocore_hypervolume",
            "elapsed_us": round((t1 - t0) / 1000, 1),
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# Scale benchmark
# ---------------------------------------------------------------------------

def run_scale_benchmark(n_strategies: int, n_metrics: int, n_repeats: int = 5) -> list[dict]:
    """Run all methods at given scale, repeated for stable timing."""
    matrix = generate_benchmark_matrix(n_strategies, n_metrics)
    weights = np.ones(n_metrics) / n_metrics
    types = np.ones(n_metrics)  # all maximize for benchmark

    results = []
    methods = [
        ("pymcdm_topsis", lambda: bench_pymcdm_topsis(matrix, weights, types)),
        ("numpy_topsis", lambda: bench_numpy_topsis(matrix, weights, types)),
    ]
    # moocore hypervolume is exponential in dimensions — only viable at <=3D
    if n_metrics <= 3:
        methods.append(("moocore_hypervolume", lambda: bench_moocore_hypervolume(matrix, types)))
    for method_name, func in methods:
        timings = []
        for _ in range(n_repeats):
            r = func()
            timings.append(r["elapsed_us"])

        results.append({
            "method": method_name,
            "n_strategies": n_strategies,
            "n_metrics": n_metrics,
            "n_repeats": n_repeats,
            "median_us": round(float(np.median(timings)), 1),
            "p95_us": round(float(np.percentile(timings, 95)), 1),
            "min_us": round(float(np.min(timings)), 1),
        })

    # pymoo knee-point only on smaller data (too slow at 50K)
    if n_strategies <= 10000:
        timings = []
        for _ in range(n_repeats):
            r = bench_pymoo_knee(matrix, types)
            timings.append(r["elapsed_us"])
        results.append({
            "method": "pymoo_knee_point",
            "n_strategies": n_strategies,
            "n_metrics": n_metrics,
            "n_repeats": n_repeats,
            "median_us": round(float(np.median(timings)), 1),
            "p95_us": round(float(np.percentile(timings, 95)), 1),
            "min_us": round(float(np.min(timings)), 1),
        })

    # pymoo PseudoWeights
    timings = []
    for _ in range(n_repeats):
        r = bench_pymoo_pseudo_weights(matrix, weights, types)
        timings.append(r["elapsed_us"])
    results.append({
        "method": "pymoo_pseudo_weights",
        "n_strategies": n_strategies,
        "n_metrics": n_metrics,
        "n_repeats": n_repeats,
        "median_us": round(float(np.median(timings)), 1),
        "p95_us": round(float(np.percentile(timings, 95)), 1),
        "min_us": round(float(np.min(timings)), 1),
    })

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    repo_root = Path(__file__).resolve().parent.parent
    output_dir = repo_root / "results" / "eval"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "mcdm_benchmark.jsonl"

    git_commit = _git_commit()
    timestamp = datetime.now(tz=UTC).isoformat()
    provenance = {
        "git_commit": git_commit,
        "timestamp": timestamp,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
    }

    telemetry = []

    # ===================================================================
    # Phase 1: Real Pareto front (76 solutions, 3 objectives)
    # ===================================================================
    print("=" * 70)
    print("MCDM Benchmark POC — Performance-First Evaluation")
    print("=" * 70)

    matrix, metric_names, labels = load_pareto_front(repo_root)
    n_solutions = matrix.shape[0]
    n_metrics = matrix.shape[1]
    print(f"\nLoaded Pareto front: {n_solutions} solutions x {n_metrics} metrics")
    print(f"Metrics: {metric_names}")

    # types: n_survivors=maximize(1), avg_quality=maximize(1), mean_cutoff=minimize(-1)
    types = np.array([1.0, 1.0, -1.0])
    weights = np.array([1.0 / 3, 1.0 / 3, 1.0 / 3])

    print("\n--- Phase 1: Real Pareto Front ---")

    # Method 1: pymcdm TOPSIS
    r1 = bench_pymcdm_topsis(matrix, weights, types)
    r1["phase"] = "real_pareto"
    r1["n_solutions"] = n_solutions
    r1["provenance"] = provenance
    telemetry.append(r1)
    best_label = labels[r1["best_idx"]]
    print(f"\n  pymcdm TOPSIS:  {r1['elapsed_us']:>10.1f} µs  →  best={best_label} (score={r1['best_score']:.4f})")
    print(f"    Top 5: {[labels[i] for i in r1['top5_indices']]}")

    # Method 2: NumPy TOPSIS
    r2 = bench_numpy_topsis(matrix, weights, types)
    r2["phase"] = "real_pareto"
    r2["n_solutions"] = n_solutions
    r2["provenance"] = provenance
    telemetry.append(r2)
    best_label = labels[r2["best_idx"]]
    print(f"  NumPy TOPSIS:   {r2['elapsed_us']:>10.1f} µs  →  best={best_label} (score={r2['best_score']:.4f})")
    print(f"    Top 5: {[labels[i] for i in r2['top5_indices']]}")
    print(f"    Ideal: {r2['ideal_point']}")
    print(f"    Nadir: {r2['nadir_point']}")

    # Method 3: pymoo knee-point
    r3 = bench_pymoo_knee(matrix, types)
    r3["phase"] = "real_pareto"
    r3["n_solutions"] = n_solutions
    r3["provenance"] = provenance
    telemetry.append(r3)
    knee_labels = [labels[i] for i in r3.get("knee_indices", [])]
    print(f"  pymoo Knee:     {r3['elapsed_us']:>10.1f} µs  →  {r3.get('n_knee_points', 0)} knee points")
    if knee_labels:
        print(f"    Knee points: {knee_labels}")
    if r3.get("error"):
        print(f"    ERROR: {r3['error']}")

    # Method 4: pymoo CompromiseProgramming
    r4 = bench_pymoo_pseudo_weights(matrix, weights, types)
    r4["phase"] = "real_pareto"
    r4["n_solutions"] = n_solutions
    r4["provenance"] = provenance
    telemetry.append(r4)
    if "best_idx" in r4:
        best_label = labels[r4["best_idx"]]
        print(f"  pymoo PseudoW:  {r4['elapsed_us']:>10.1f} µs  →  best={best_label}")
    else:
        print(f"  pymoo PseudoW:  {r4['elapsed_us']:>10.1f} µs  →  ERROR: {r4.get('error')}")

    # Method 5: moocore hypervolume
    r5 = bench_moocore_hypervolume(matrix, types)
    r5["phase"] = "real_pareto"
    r5["n_solutions"] = n_solutions
    r5["provenance"] = provenance
    telemetry.append(r5)
    if "hypervolume" in r5:
        print(f"  moocore HV:     {r5['elapsed_us']:>10.1f} µs  →  HV={r5['hypervolume']:.4f}")
    else:
        print(f"  moocore HV:     {r5['elapsed_us']:>10.1f} µs  →  ERROR: {r5.get('error')}")

    # Ranking agreement
    if r1.get("top5_indices") and r2.get("top5_indices"):
        overlap = set(r1["top5_indices"]) & set(r2["top5_indices"])
        print(f"\n  TOPSIS agreement (pymcdm vs NumPy): {len(overlap)}/5 top-5 overlap")
        if r3.get("knee_indices"):
            knee_in_top5 = set(r3["knee_indices"]) & set(r1["top5_indices"])
            print(f"  Knee points in TOPSIS top-5: {len(knee_in_top5)}/{len(r3['knee_indices'])}")

    # ===================================================================
    # Phase 2: Scale benchmark (generated data for perf measurement)
    # ===================================================================
    print("\n--- Phase 2: Scale Benchmark ---")
    print(f"{'Method':<25} {'N':>8} {'Metrics':>7} {'Median µs':>12} {'P95 µs':>12} {'Min µs':>12}")
    print("-" * 80)

    for n_strat in [76, 1000, 10000, 50000]:
        scale_results = run_scale_benchmark(n_strat, 11)  # 11 metrics like our real system
        for sr in scale_results:
            print(f"  {sr['method']:<23} {sr['n_strategies']:>8} {sr['n_metrics']:>7} "
                  f"{sr['median_us']:>12.1f} {sr['p95_us']:>12.1f} {sr['min_us']:>12.1f}")
            sr["phase"] = "scale_benchmark"
            sr["provenance"] = provenance
            telemetry.append(sr)
        print()

    # ===================================================================
    # Phase 3: Verdict
    # ===================================================================
    print("=" * 70)
    print("VERDICT")
    print("=" * 70)

    # Find fastest method at 50K scale
    scale_50k = [t for t in telemetry if t.get("phase") == "scale_benchmark" and t.get("n_strategies") == 50000]
    if scale_50k:
        fastest = min(scale_50k, key=lambda x: x.get("median_us", float("inf")))
        print(f"\n  Fastest at 50K strategies: {fastest['method']} ({fastest['median_us']:.1f} µs median)")

    # Check if TOPSIS rankings agree
    if r1.get("top5_indices") and r2.get("top5_indices"):
        if r1["top5_indices"] == r2["top5_indices"]:
            print("  TOPSIS implementations: IDENTICAL top-5 rankings")
        else:
            overlap_pct = len(set(r1["top5_indices"]) & set(r2["top5_indices"])) / 5 * 100
            print(f"  TOPSIS implementations: {overlap_pct:.0f}% top-5 overlap")

    verdict = "GO" if (r1.get("best_idx") is not None and r2.get("best_idx") is not None) else "NO-GO"
    print(f"\n  POC Verdict: {verdict}")
    print("=" * 70)

    # Write telemetry
    with open(output_file, "w") as f:
        for record in telemetry:
            f.write(json.dumps(record) + "\n")

    print(f"\nOutput: {output_file} ({len(telemetry)} records)")
    return 0 if verdict == "GO" else 1


if __name__ == "__main__":
    sys.exit(main())
