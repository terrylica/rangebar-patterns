"""Agent 8: E-values and GROW criterion.

Sequential E-value computation: E_T = prod(1 + f * r_t) where f = half-Kelly.
GROW = mean(log(1 + f * r_t)). Identifies configs where E > 1/alpha = 20.

E-values are the proper hypothesis testing framework for Kelly — they are
mathematically isomorphic (GROW maximizes the same objective as Kelly).

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

RESULTS_DIR = Path(__file__).resolve().parent / "results"
INPUT_FILE = RESULTS_DIR / "trade_returns.jsonl"
MOMENTS_FILE = RESULTS_DIR / "moments.jsonl"
OUTPUT_FILE = RESULTS_DIR / "evalues.jsonl"

ALPHA = 0.05  # Significance level
E_THRESHOLD = 1.0 / ALPHA  # = 20.0
MIN_BET = 0.001  # Minimum bet fraction for negative-Kelly configs
MAX_EVALUE = 1e10  # Cap to prevent overflow


def compute_evalues(returns: list[float], kelly: float) -> dict:
    """Compute sequential E-values using half-Kelly bet sizing."""
    # Use half-Kelly for conservative bet sizing
    f = max(kelly / 2.0, MIN_BET) if kelly > 0 else MIN_BET

    arr = np.array(returns)
    # E_t = prod(1 + f * r_i) for i=1..t
    # Compute in log-space to avoid overflow
    log_factors = np.log1p(f * arr)
    cumulative_log = np.cumsum(log_factors)

    # Cap at MAX_EVALUE in log-space
    max_log = np.log(MAX_EVALUE)
    cumulative_log = np.minimum(cumulative_log, max_log)

    final_log_evalue = cumulative_log[-1] if len(cumulative_log) > 0 else 0.0
    max_log_evalue = cumulative_log.max() if len(cumulative_log) > 0 else 0.0

    final_evalue = float(np.exp(final_log_evalue))
    max_evalue = float(np.exp(max_log_evalue))

    # GROW criterion = mean(log(1 + f * r_t))
    grow = float(log_factors.mean()) if len(log_factors) > 0 else 0.0

    # Find first rejection point (if any)
    rejection_indices = np.where(cumulative_log >= np.log(E_THRESHOLD))[0]
    first_rejection = int(rejection_indices[0]) + 1 if len(rejection_indices) > 0 else None

    return {
        "final_evalue": round(final_evalue, 6),
        "max_evalue": round(max_evalue, 6),
        "grow_criterion": round(grow, 8),
        "rejects_null_at_005": max_evalue >= E_THRESHOLD,
        "first_rejection_trade": first_rejection,
        "kelly_used": round(f, 6),
    }


def main():
    # Load trade returns from Agent 2
    trade_data = []
    with open(INPUT_FILE) as f:
        for line in f:
            trade_data.append(json.loads(line))

    # Load moments for Kelly fraction
    kelly_map = {}
    with open(MOMENTS_FILE) as f:
        for line in f:
            r = json.loads(line)
            kelly_map[r["config_id"]] = r.get("kelly_fraction", 0.0) or 0.0

    print(f"Loaded {len(trade_data)} configs from {INPUT_FILE}")

    results = []
    for d in trade_data:
        config_id = d["config_id"]
        n_trades = d.get("n_trades", 0)
        returns = d.get("returns", [])
        kelly = kelly_map.get(config_id, 0.0)

        if d.get("error") or n_trades < 3 or len(returns) < 3:
            results.append({
                "config_id": config_id,
                "n_trades": n_trades,
                "final_evalue": None,
                "max_evalue": None,
                "grow_criterion": None,
                "rejects_null_at_005": False,
                "first_rejection_trade": None,
                "kelly_used": None,
                "kelly_fraction": kelly,
            })
            continue

        ev = compute_evalues(returns, kelly)
        ev["config_id"] = config_id
        ev["n_trades"] = n_trades
        ev["kelly_fraction"] = kelly
        results.append(ev)

    with open(OUTPUT_FILE, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    rejecters = sum(1 for r in results if r.get("rejects_null_at_005"))
    pos_grow = sum(1 for r in results if r.get("grow_criterion") is not None and r["grow_criterion"] > 0)
    print(f"\nResults: {len(results)} configs")
    print(f"  Reject null at alpha=0.05 (E >= {E_THRESHOLD}): {rejecters}")
    print(f"  Positive GROW: {pos_grow}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
