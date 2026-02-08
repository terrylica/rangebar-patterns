"""Omega Ratio computation.

Computes Omega(L=0) = sum(max(r-L,0)) / sum(max(L-r,0)) for each config
using full per-trade return arrays. Omega considers the entire return
distribution, not just the first two moments.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""

from __future__ import annotations

import json

import numpy as np

from rangebar_patterns.eval._io import load_jsonl, results_dir


def compute_omega(returns: list[float], threshold: float = 0.0) -> float:
    """Discrete empirical Omega Ratio at threshold L."""
    arr = np.array(returns)
    gains = np.maximum(arr - threshold, 0.0).sum()
    losses = np.maximum(threshold - arr, 0.0).sum()
    if losses == 0:
        return float("inf") if gains > 0 else 1.0
    return float(gains / losses)


def main():
    rd = results_dir()
    input_file = rd / "trade_returns.jsonl"
    moments_file = rd / "moments.jsonl"
    output_file = rd / "omega_rankings.jsonl"

    trade_data = {r["config_id"]: r for r in load_jsonl(input_file)}
    kelly_map = {r["config_id"]: r.get("kelly_fraction") for r in load_jsonl(moments_file)}

    print(f"Loaded {len(trade_data)} configs from {input_file}")

    results = []
    for config_id, data in trade_data.items():
        n_trades = data.get("n_trades", 0)
        returns = data.get("returns", [])

        if data.get("error") or n_trades < 3 or len(returns) < 3:
            results.append({
                "config_id": config_id,
                "n_trades": n_trades,
                "omega_L0": None,
                "gain_loss_ratio": None,
                "kelly_fraction": kelly_map.get(config_id),
            })
            continue

        omega = compute_omega(returns, threshold=0.0)

        arr = np.array(returns)
        total_gains = arr[arr > 0].sum()
        total_losses = abs(arr[arr < 0].sum())
        gl_ratio = float(total_gains / total_losses) if total_losses > 0 else float("inf")

        results.append({
            "config_id": config_id,
            "n_trades": n_trades,
            "omega_L0": round(omega, 6) if omega != float("inf") else None,
            "omega_is_inf": omega == float("inf"),
            "gain_loss_ratio": round(gl_ratio, 6) if gl_ratio != float("inf") else None,
            "kelly_fraction": kelly_map.get(config_id),
        })

    # Compute ranks for Omega vs Kelly comparison
    valid = [(i, r) for i, r in enumerate(results) if r.get("omega_L0") is not None]
    valid_kelly = [(i, r) for i, r in enumerate(results) if r.get("kelly_fraction") is not None]

    omega_sorted = sorted(valid, key=lambda x: x[1]["omega_L0"], reverse=True)
    kelly_sorted = sorted(valid_kelly, key=lambda x: x[1]["kelly_fraction"], reverse=True)

    omega_ranks = {idx: rank + 1 for rank, (idx, _) in enumerate(omega_sorted)}
    kelly_ranks = {idx: rank + 1 for rank, (idx, _) in enumerate(kelly_sorted)}

    for i, r in enumerate(results):
        r["omega_rank"] = omega_ranks.get(i)
        r["kelly_rank"] = kelly_ranks.get(i)

    # Spearman rank correlation between Omega and Kelly
    common = [i for i in range(len(results)) if i in omega_ranks and i in kelly_ranks]
    if len(common) > 2:
        o_ranks = np.array([omega_ranks[i] for i in common], dtype=float)
        k_ranks = np.array([kelly_ranks[i] for i in common], dtype=float)
        n = len(common)
        d2 = ((o_ranks - k_ranks) ** 2).sum()
        spearman = 1.0 - 6.0 * d2 / (n * (n**2 - 1))
    else:
        spearman = None

    with open(output_file, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    omega_gt1 = sum(1 for r in results if r.get("omega_L0") is not None and r["omega_L0"] > 1.0)
    print(f"\nResults: {len(results)} configs")
    print(f"  Omega > 1.0 (positive EV): {omega_gt1}")
    print(f"  Spearman(Omega, Kelly): {spearman:.4f}" if spearman else "  Spearman: N/A")
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()
