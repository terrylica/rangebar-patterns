"""Conditional Drawdown at Risk (CDaR) computation.

Computes CDaR(alpha) = mean of worst (1-alpha) fraction of the drawdown curve.
Detects clustered loss sequences that SL alone misses. Used in TAMRS as the
denominator of the SL/CDaR ratio: min(1, |SL_emp| / CDaR).

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/16
"""

from __future__ import annotations

import json

import numpy as np

from rangebar_patterns.config import CDAR_ALPHA, MIN_TRADES_CDAR, SL_EMP
from rangebar_patterns.eval._io import load_jsonl, results_dir


def compute_cdar(returns: list[float], alpha: float = CDAR_ALPHA) -> float | None:
    """Mean of worst (1-alpha) fraction of drawdown curve. None if n < MIN_TRADES_CDAR."""
    arr = np.asarray(returns, dtype=float)
    if len(arr) < MIN_TRADES_CDAR:
        return None
    cum_returns = np.cumsum(arr)
    running_max = np.maximum.accumulate(cum_returns)
    drawdowns = running_max - cum_returns  # >= 0
    sorted_dd = np.sort(drawdowns)[::-1]
    n_tail = max(1, int(len(sorted_dd) * (1 - alpha)))
    return float(np.mean(sorted_dd[:n_tail]))


def main():
    rd = results_dir()
    input_file = rd / "trade_returns.jsonl"
    output_file = rd / "cdar_rankings.jsonl"

    trade_data = load_jsonl(input_file)
    print(f"Loaded {len(trade_data)} configs from {input_file}")

    results = []
    n_valid = 0
    for d in trade_data:
        config_id = d["config_id"]
        n_trades = d.get("n_trades", 0)
        returns = d.get("returns", [])

        cd = compute_cdar(returns)
        if cd is not None:
            n_valid += 1
            arr = np.asarray(returns, dtype=float)
            cum_returns = np.cumsum(arr)
            running_max = np.maximum.accumulate(cum_returns)
            max_dd = float(np.max(running_max - cum_returns))
            sl_cdar = min(1.0, SL_EMP / cd) if cd > 1e-12 else 1.0
        else:
            max_dd = None
            sl_cdar = None

        results.append({
            "config_id": config_id,
            "n_trades": n_trades,
            "cdar_095": round(cd, 6) if cd is not None else None,
            "max_drawdown": round(max_dd, 6) if max_dd is not None else None,
            "sl_emp": SL_EMP,
            "sl_cdar_ratio": round(sl_cdar, 6) if sl_cdar is not None else None,
        })

    with open(output_file, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    valid_values = [r["cdar_095"] for r in results if r["cdar_095"] is not None]
    print(f"\nResults: {len(results)} configs, {n_valid} valid")
    if valid_values:
        print(f"  CDaR range: [{min(valid_values):.6f}, {max(valid_values):.6f}]")
        print(f"  CDaR median: {np.median(valid_values):.6f}")
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()
