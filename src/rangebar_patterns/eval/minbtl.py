"""Minimum Backtest Length (MinBTL) gate.

Computes the minimum number of trades needed for statistical significance
given the number of trials tested. Configs with fewer trades than MinBTL
are flagged as data-insufficient.

Formula from Bailey & Lopez de Prado (2014).

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""

from __future__ import annotations

import json
import math

from rangebar_patterns.config import N_TRIALS
from rangebar_patterns.eval._io import load_jsonl, results_dir


def compute_minbtl(sr: float, n_trials: int, skew: float, kurt: float) -> float:
    """Minimum Backtest Length in number of observations.

    MinBTL ~ (2 * log(N) / SR^2) * (1 - skew*SR/3 + ((kurt-1)/4)*SR^2)

    Returns float('inf') if SR is too close to zero.
    """
    if abs(sr) < 1e-8:
        return float("inf")

    log_n = math.log(n_trials)
    moment_adj = 1.0 - skew * sr / 3.0 + ((kurt - 1.0) / 4.0) * sr**2
    moment_adj = max(moment_adj, 0.1)

    return (2.0 * log_n / sr**2) * moment_adj


def main():
    rd = results_dir()
    input_file = rd / "moments.jsonl"
    output_file = rd / "minbtl_gate.jsonl"

    records = load_jsonl(input_file)
    print(f"Loaded {len(records)} configs from {input_file}")

    results = []
    for r in records:
        config_id = r["config_id"]
        n_trades = r.get("n_trades", 0)

        if r.get("error") or n_trades < 3:
            results.append({
                "config_id": config_id, "n_trades": n_trades,
                "observed_sr": None, "min_btl_required": None,
                "passes_gate": False, "headroom_ratio": 0.0,
                "kelly_fraction": r.get("kelly_fraction"),
            })
            continue

        mean = r["mean_return"]
        std = r["std_return"]
        skew = r.get("skew_return", 0.0) or 0.0
        kurt = r.get("kurt_return", 3.0) or 3.0

        sr = 0.0 if std is None or std <= 0 else mean / std
        min_btl = compute_minbtl(sr, N_TRIALS, skew, kurt)
        passes = n_trades >= min_btl if math.isfinite(min_btl) else False
        headroom = n_trades / min_btl if math.isfinite(min_btl) and min_btl > 0 else 0.0

        results.append({
            "config_id": config_id, "n_trades": n_trades,
            "observed_sr": round(sr, 6),
            "min_btl_required": round(min_btl, 1) if math.isfinite(min_btl) else None,
            "passes_gate": passes,
            "headroom_ratio": round(headroom, 4),
            "skew": round(skew, 4),
            "kurtosis": round(kurt, 4),
            "kelly_fraction": r.get("kelly_fraction"),
        })

    with open(output_file, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    passing = sum(1 for r in results if r["passes_gate"])
    pos_kelly_fail = sum(
        1 for r in results
        if r.get("kelly_fraction") is not None
        and r["kelly_fraction"] > 0
        and not r["passes_gate"]
    )
    print(f"\nResults: {len(results)} configs")
    print(f"  Pass MinBTL gate: {passing}")
    print(f"  Kelly>0 but FAIL MinBTL: {pos_kelly_fail}")
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()
