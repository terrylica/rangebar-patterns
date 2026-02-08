"""Agent 3: Deflated Sharpe Ratio (DSR) and Probabilistic Sharpe Ratio (PSR).

Implements Bailey & López de Prado (2014) formulas for multiple-testing
correction of Sharpe Ratios. Uses moment statistics from layer1_sql_moments.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import norm

RESULTS_DIR = Path(__file__).resolve().parent / "results"
INPUT_FILE = RESULTS_DIR / "moments.jsonl"
OUTPUT_FILE = RESULTS_DIR / "dsr_rankings.jsonl"

N_TRIALS = 1008  # Number of configs tested (gen500 2-feature grid)
EULER_GAMMA = 0.5772156649  # Euler-Mascheroni constant


def expected_max_sr(n_trials: int, var_sr: float) -> float:
    """Expected maximum Sharpe Ratio under null (all strategies have SR=0).

    From False Strategy Theorem (Bailey & López de Prado 2014).
    """
    if n_trials <= 1:
        return 0.0
    z1 = norm.ppf(1.0 - 1.0 / n_trials)
    z2 = norm.ppf(1.0 - 1.0 / (n_trials * math.e))
    return math.sqrt(var_sr) * ((1 - EULER_GAMMA) * z1 + EULER_GAMMA * z2)


def sr_standard_error(sr: float, n: int, skew: float, kurt: float) -> float:
    """Standard error of Sharpe Ratio estimator accounting for non-normality.

    Formula: sqrt((1 + 0.5*SR^2 - skew*SR + ((kurt-3)/4)*SR^2) / n)
    """
    if n <= 1:
        return float("inf")
    inner = 1.0 + 0.5 * sr**2 - skew * sr + ((kurt - 3.0) / 4.0) * sr**2
    inner = max(inner, 1e-10)  # Guard against negative (extreme kurtosis)
    return math.sqrt(inner / n)


def compute_psr(sr: float, sr_star: float, se: float) -> float:
    """Probabilistic Sharpe Ratio: P(true SR > sr_star)."""
    if se <= 0 or not math.isfinite(se):
        return 0.0
    z = (sr - sr_star) / se
    return float(norm.cdf(z))


def main():
    # Load moments from Agent 1
    records = []
    with open(INPUT_FILE) as f:
        for line in f:
            records.append(json.loads(line))

    print(f"Loaded {len(records)} configs from {INPUT_FILE}")

    # Compute SR variance across all configs (for expected_max_sr)
    valid_srs = []
    for r in records:
        if r.get("error") or r.get("n_trades", 0) < 3:
            continue
        std = r.get("std_return")
        mean = r.get("mean_return")
        if std and std > 0 and mean is not None:
            valid_srs.append(mean / std)

    var_sr = float(np.var(valid_srs)) if valid_srs else 1.0
    sr_max_null = expected_max_sr(N_TRIALS, var_sr)
    print(f"Expected max SR under null (N={N_TRIALS}): {sr_max_null:.4f}")
    print(f"SR variance across configs: {var_sr:.6f}")

    results = []
    for r in records:
        config_id = r["config_id"]
        n_trades = r.get("n_trades", 0)

        if r.get("error") or n_trades < 3:
            results.append({
                "config_id": config_id,
                "n_trades": n_trades,
                "sharpe_ratio": None,
                "psr_vs_zero": None,
                "dsr": None,
                "dsr_passes": False,
                "expected_max_sr_null": sr_max_null,
                "kelly_fraction": r.get("kelly_fraction"),
                "insufficient_data": True,
            })
            continue

        mean = r["mean_return"]
        std = r["std_return"]
        skew = r.get("skew_return", 0.0) or 0.0
        kurt = r.get("kurt_return", 3.0) or 3.0
        kelly = r.get("kelly_fraction")

        sr = 0.0 if std is None or std <= 0 else mean / std

        se = sr_standard_error(sr, n_trades, skew, kurt)

        # PSR: test against SR* = 0
        psr_zero = compute_psr(sr, 0.0, se)

        # DSR: test against SR* = expected_max_sr under null
        dsr = compute_psr(sr, sr_max_null, se)

        results.append({
            "config_id": config_id,
            "n_trades": n_trades,
            "sharpe_ratio": round(sr, 6),
            "psr_vs_zero": round(psr_zero, 6),
            "dsr": round(dsr, 6),
            "dsr_passes": dsr > 0.95,
            "expected_max_sr_null": round(sr_max_null, 6),
            "kelly_fraction": kelly,
            "skew": round(skew, 4),
            "kurtosis": round(kurt, 4),
            "insufficient_data": False,
        })

    # Write results
    with open(OUTPUT_FILE, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # Summary
    passing = sum(1 for r in results if r.get("dsr_passes"))
    pos_kelly = sum(1 for r in results if r.get("kelly_fraction") is not None and r["kelly_fraction"] > 0)
    print(f"\nResults: {len(results)} configs")
    print(f"  DSR > 0.95 (pass): {passing}")
    print(f"  Kelly > 0: {pos_kelly}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
