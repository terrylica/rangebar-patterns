"""Rachev Ratio computation.

Computes Rachev(alpha) = CVaR(upper alpha) / CVaR(lower alpha) for each config
using full per-trade return arrays. Measures tail asymmetry: healthy strategies
have balanced tails (~1.0), penny-pickers have heavy left tails (~0.38).

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/16
"""

from __future__ import annotations

import json

import numpy as np

from rangebar_patterns.config import MIN_TRADES_RACHEV, RACHEV_ALPHA
from rangebar_patterns.eval._io import load_jsonl, results_dir


def compute_rachev(returns: list[float], alpha: float = RACHEV_ALPHA) -> float | None:
    """CVaR(upper alpha) / CVaR(lower alpha). None if n < MIN_TRADES_RACHEV."""
    arr = np.asarray(returns, dtype=float)
    if len(arr) < MIN_TRADES_RACHEV:
        return None
    n_tail = max(1, int(len(arr) * alpha))
    sorted_ret = np.sort(arr)
    cvar_upper = float(np.mean(sorted_ret[-n_tail:]))
    cvar_lower_abs = float(np.abs(np.mean(sorted_ret[:n_tail])))
    if cvar_lower_abs < 1e-12:
        return None
    return cvar_upper / cvar_lower_abs


def main():
    rd = results_dir()
    input_file = rd / "trade_returns.jsonl"
    output_file = rd / "rachev_rankings.jsonl"

    trade_data = load_jsonl(input_file)
    print(f"Loaded {len(trade_data)} configs from {input_file}")

    results = []
    n_valid = 0
    for d in trade_data:
        config_id = d["config_id"]
        n_trades = d.get("n_trades", 0)
        returns = d.get("returns", [])

        rr = compute_rachev(returns)
        if rr is not None:
            n_valid += 1
            arr = np.asarray(returns, dtype=float)
            n_tail = max(1, int(len(arr) * RACHEV_ALPHA))
            sorted_ret = np.sort(arr)
            cvar_upper = float(np.mean(sorted_ret[-n_tail:]))
            cvar_lower = float(np.mean(sorted_ret[:n_tail]))
        else:
            cvar_upper = None
            cvar_lower = None

        results.append({
            "config_id": config_id,
            "n_trades": n_trades,
            "rachev_ratio": round(rr, 6) if rr is not None else None,
            "cvar_upper_05": round(cvar_upper, 6) if cvar_upper is not None else None,
            "cvar_lower_05": round(cvar_lower, 6) if cvar_lower is not None else None,
            "alpha": RACHEV_ALPHA,
        })

    with open(output_file, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    valid_values = [r["rachev_ratio"] for r in results if r["rachev_ratio"] is not None]
    print(f"\nResults: {len(results)} configs, {n_valid} valid")
    if valid_values:
        print(f"  Rachev range: [{min(valid_values):.4f}, {max(valid_values):.4f}]")
        print(f"  Rachev median: {np.median(valid_values):.4f}")
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()
