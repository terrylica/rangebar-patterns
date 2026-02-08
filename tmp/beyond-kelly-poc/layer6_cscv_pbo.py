"""Agent 7: Combinatorial Symmetric Cross-Validation (CSCV) and PBO.

Implements CSCV with S=8 blocks to estimate Probability of Backtest
Overfitting (PBO). For each of C(8,4)=70 train/test splits, finds the
best config by Sharpe on train data and measures its OOS rank.

PBO = fraction of splits where the IS-winner underperforms the OOS median.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path

import numpy as np

RESULTS_DIR = Path(__file__).resolve().parent / "results"
INPUT_FILE = RESULTS_DIR / "trade_returns.jsonl"
OUTPUT_FILE = RESULTS_DIR / "cscv_pbo.jsonl"

N_SPLITS = 8  # Number of time blocks


def compute_sharpe(returns: np.ndarray) -> float:
    """Sharpe ratio of a return array. Returns 0 for empty/constant arrays."""
    if len(returns) < 2:
        return 0.0
    std = returns.std(ddof=1)
    if std < 1e-12:
        return 0.0
    return float(returns.mean() / std)


def main():
    # Load trade returns from Agent 2
    all_data = []
    with open(INPUT_FILE) as f:
        for line in f:
            all_data.append(json.loads(line))

    print(f"Loaded {len(all_data)} configs from {INPUT_FILE}")

    # Collect all timestamps to define time blocks
    all_timestamps = set()
    for d in all_data:
        if d.get("timestamps_ms"):
            all_timestamps.update(d["timestamps_ms"])

    if not all_timestamps:
        print("ERROR: No timestamps found in data")
        return

    sorted_ts = sorted(all_timestamps)
    ts_min, ts_max = sorted_ts[0], sorted_ts[-1]
    block_size = (ts_max - ts_min) / N_SPLITS
    print(f"Time range: {ts_min} to {ts_max}")
    print(f"Block size: {block_size:.0f} ms ({block_size / 86400000:.1f} days)")

    # Pre-compute per-config, per-block returns
    config_ids = [d["config_id"] for d in all_data]
    n_configs = len(config_ids)

    # block_returns[config_idx][block_idx] = numpy array of returns in that block
    block_returns = []
    for d in all_data:
        returns = d.get("returns", [])
        timestamps = d.get("timestamps_ms", [])
        blocks = [[] for _ in range(N_SPLITS)]

        for r, ts in zip(returns, timestamps, strict=True):
            # Find which block this trade belongs to
            block_idx = min(int((ts - ts_min) / block_size), N_SPLITS - 1)
            blocks[block_idx].append(r)

        block_returns.append([np.array(b) for b in blocks])

    # Generate all C(8,4) = 70 train/test splits
    all_blocks = list(range(N_SPLITS))
    splits = list(combinations(all_blocks, N_SPLITS // 2))
    print(f"Generated {len(splits)} combinatorial splits")

    # For each split, compute IS and OOS Sharpe for all configs
    oos_ranks_of_is_winner = []
    is_winner_configs = []

    for train_blocks in splits:
        test_blocks = [b for b in all_blocks if b not in train_blocks]

        # Compute IS Sharpe for all configs
        is_sharpes = np.zeros(n_configs)
        for cfg_idx in range(n_configs):
            train_rets = np.concatenate(
                [block_returns[cfg_idx][b] for b in train_blocks
                 if len(block_returns[cfg_idx][b]) > 0]
            ) if any(len(block_returns[cfg_idx][b]) > 0 for b in train_blocks) else np.array([])
            is_sharpes[cfg_idx] = compute_sharpe(train_rets)

        # Find IS winner
        is_winner_idx = int(np.argmax(is_sharpes))
        is_winner_configs.append(config_ids[is_winner_idx])

        # Compute OOS Sharpe for all configs
        oos_sharpes = np.zeros(n_configs)
        for cfg_idx in range(n_configs):
            test_rets = np.concatenate(
                [block_returns[cfg_idx][b] for b in test_blocks
                 if len(block_returns[cfg_idx][b]) > 0]
            ) if any(len(block_returns[cfg_idx][b]) > 0 for b in test_blocks) else np.array([])
            oos_sharpes[cfg_idx] = compute_sharpe(test_rets)

        # Rank the IS winner's OOS performance relative to all configs
        is_winner_oos = oos_sharpes[is_winner_idx]
        # Rank = fraction of configs that IS winner beats OOS
        rank_pct = float(np.mean(oos_sharpes <= is_winner_oos))
        oos_ranks_of_is_winner.append(rank_pct)

    # PBO = fraction where IS winner is below median OOS (rank < 0.5)
    pbo = float(np.mean(np.array(oos_ranks_of_is_winner) < 0.5))

    # Most common IS winner
    from collections import Counter
    winner_counts = Counter(is_winner_configs)
    most_common_winner = winner_counts.most_common(1)[0]

    result = {
        "n_configs": n_configs,
        "n_splits": N_SPLITS,
        "n_combinations": len(splits),
        "pbo": round(pbo, 4),
        "pbo_interpretation": (
            "ROBUST" if pbo < 0.05
            else "MARGINAL" if pbo < 0.5
            else "OVERFIT"
        ),
        "mean_oos_rank": round(float(np.mean(oos_ranks_of_is_winner)), 4),
        "std_oos_rank": round(float(np.std(oos_ranks_of_is_winner)), 4),
        "most_common_is_winner": most_common_winner[0],
        "most_common_is_winner_count": most_common_winner[1],
        "oos_rank_distribution": [round(x, 4) for x in sorted(oos_ranks_of_is_winner)],
    }

    with open(OUTPUT_FILE, "w") as f:
        f.write(json.dumps(result) + "\n")

    print(f"\nPBO = {pbo:.4f} ({result['pbo_interpretation']})")
    print(f"Mean OOS rank of IS winner: {result['mean_oos_rank']:.4f}")
    print(f"Most common IS winner: {most_common_winner[0]} ({most_common_winner[1]}/{len(splits)} splits)")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
