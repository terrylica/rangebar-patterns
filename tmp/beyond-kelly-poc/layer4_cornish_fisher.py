"""Agent 5: Cornish-Fisher Expected Shortfall.

Computes tail-risk-adjusted VaR and ES using the Cornish-Fisher expansion,
which corrects Gaussian quantiles for skewness and kurtosis.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""

from __future__ import annotations

import json
from pathlib import Path

from scipy.stats import norm

RESULTS_DIR = Path(__file__).resolve().parent / "results"
INPUT_FILE = RESULTS_DIR / "moments.jsonl"
OUTPUT_FILE = RESULTS_DIR / "cornish_fisher.jsonl"


def cornish_fisher_quantile(z_alpha: float, skew: float, kurt: float) -> float:
    """Cornish-Fisher adjusted quantile.

    z_CF = z_a + (1/6)(z^2-1)S + (1/24)(z^3-3z)(K-3) - (1/36)(2z^3-5z)S^2
    """
    z2 = z_alpha**2
    z3 = z_alpha**3
    cf = (
        z_alpha
        + (1.0 / 6.0) * (z2 - 1.0) * skew
        + (1.0 / 24.0) * (z3 - 3.0 * z_alpha) * (kurt - 3.0)
        - (1.0 / 36.0) * (2.0 * z3 - 5.0 * z_alpha) * skew**2
    )
    return cf


def cf_var(mean: float, std: float, skew: float, kurt: float, alpha: float) -> float:
    """Cornish-Fisher Value at Risk."""
    z_alpha = norm.ppf(alpha)
    z_cf = cornish_fisher_quantile(z_alpha, skew, kurt)
    return mean + z_cf * std


def gaussian_var(mean: float, std: float, alpha: float) -> float:
    """Standard Gaussian VaR."""
    return mean + norm.ppf(alpha) * std


def cf_expected_shortfall(
    mean: float, std: float, skew: float, kurt: float, alpha: float,
) -> float:
    """Cornish-Fisher Expected Shortfall (approximate).

    ES ≈ mean - std * φ(z_cf) / Φ(z_cf) adjusted for higher moments.
    Simplified: use CF VaR as anchor, scale by Gaussian ES/VaR ratio.
    """
    z_alpha = norm.ppf(alpha)
    z_cf = cornish_fisher_quantile(z_alpha, skew, kurt)

    # Gaussian ES = mean - std * phi(z_a) / a
    phi_z = norm.pdf(z_cf)
    gauss_es = mean - std * phi_z / alpha
    return gauss_es


def main():
    records = []
    with open(INPUT_FILE) as f:
        for line in f:
            records.append(json.loads(line))

    print(f"Loaded {len(records)} configs from {INPUT_FILE}")

    results = []
    for r in records:
        config_id = r["config_id"]
        n_trades = r.get("n_trades", 0)

        if r.get("error") or n_trades < 3:
            results.append({
                "config_id": config_id,
                "n_trades": n_trades,
                "cf_var_01": None, "cf_var_05": None,
                "cf_es_01": None, "cf_es_05": None,
                "gaussian_var_05": None, "gaussian_es_05": None,
                "tail_risk_ratio": None,
                "mean_over_cf_es_05": None,
                "kelly_fraction": r.get("kelly_fraction"),
            })
            continue

        mean = r["mean_return"]
        std = r["std_return"]
        skew = r.get("skew_return", 0.0) or 0.0
        kurt = r.get("kurt_return", 3.0) or 3.0

        if std is None or std <= 0:
            results.append({
                "config_id": config_id,
                "n_trades": n_trades,
                "cf_var_01": None, "cf_var_05": None,
                "cf_es_01": None, "cf_es_05": None,
                "gaussian_var_05": None, "gaussian_es_05": None,
                "tail_risk_ratio": None,
                "mean_over_cf_es_05": None,
                "kelly_fraction": r.get("kelly_fraction"),
            })
            continue

        cv01 = cf_var(mean, std, skew, kurt, 0.01)
        cv05 = cf_var(mean, std, skew, kurt, 0.05)
        ce01 = cf_expected_shortfall(mean, std, skew, kurt, 0.01)
        ce05 = cf_expected_shortfall(mean, std, skew, kurt, 0.05)
        gv05 = gaussian_var(mean, std, 0.05)
        ge05 = mean - std * norm.pdf(norm.ppf(0.05)) / 0.05

        # Tail risk ratio: CF ES / Gaussian ES (>1 = fatter tails)
        tail_ratio = ce05 / ge05 if ge05 != 0 else None
        # Risk-adjusted metric: mean / |CF ES|
        mean_over_es = mean / abs(ce05) if ce05 != 0 else None

        results.append({
            "config_id": config_id,
            "n_trades": n_trades,
            "cf_var_01": round(cv01, 8),
            "cf_var_05": round(cv05, 8),
            "cf_es_01": round(ce01, 8),
            "cf_es_05": round(ce05, 8),
            "gaussian_var_05": round(gv05, 8),
            "gaussian_es_05": round(ge05, 8),
            "tail_risk_ratio": round(tail_ratio, 4) if tail_ratio is not None else None,
            "mean_over_cf_es_05": round(mean_over_es, 6) if mean_over_es is not None else None,
            "kelly_fraction": r.get("kelly_fraction"),
        })

    with open(OUTPUT_FILE, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # Summary
    high_tail = sum(
        1 for r in results
        if r.get("tail_risk_ratio") is not None and r["tail_risk_ratio"] > 1.2
    )
    print(f"\nResults: {len(results)} configs")
    print(f"  High tail risk (ratio > 1.2): {high_tail}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
