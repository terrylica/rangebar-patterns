"""Combinatorial Symmetric Cross-Validation (CSCV) and PBO.

Implements CSCV with S blocks (default 8) to estimate Probability of Backtest
Overfitting (PBO). For each of C(S,S/2) train/test splits, finds the
best config by the selected ranker (TAMRS or Sharpe) on train data and
measures its OOS rank.

PBO = fraction of splits where the IS-winner underperforms the OOS median.

Ranker controlled by RBP_CSCV_RANKER (mise env): "tamrs" (default) or "sharpe".
Splits controlled by RBP_CSCV_SPLITS (mise env): default 8 -> C(8,4)=70 combos.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/16
"""

from __future__ import annotations

import json
from collections import Counter
from itertools import combinations

import numpy as np

from rangebar_patterns.config import CSCV_RANKER, CSCV_SPLITS, SL_EMP
from rangebar_patterns.eval._io import load_jsonl, results_dir

N_SPLITS = CSCV_SPLITS


def compute_sharpe(returns: np.ndarray) -> float:
    """Sharpe ratio of a return array. Returns 0 for empty/constant arrays."""
    if len(returns) < 2:
        return 0.0
    std = returns.std(ddof=1)
    if std < 1e-12:
        return 0.0
    return float(returns.mean() / std)


def compute_tamrs_for_block(
    returns: np.ndarray, sl_emp: float, ou_ratio: float,
) -> float:
    """TAMRS ranker for CSCV block evaluation.

    Computes Rachev * min(1, |SL|/CDaR) * ou_ratio for a single block.
    Returns 0.0 if insufficient trades for stable Rachev/CDaR.
    """
    from rangebar_patterns.eval.cdar import compute_cdar
    from rangebar_patterns.eval.rachev import compute_rachev

    rr = compute_rachev(returns.tolist())
    cd = compute_cdar(returns.tolist())
    if rr is None or cd is None:
        return 0.0
    sl_cdar = min(1.0, sl_emp / cd) if cd > 1e-12 else 1.0
    return rr * sl_cdar * ou_ratio


def _get_ranker_fn(ranker: str, ou_ratio: float):
    """Return rank_fn based on ranker selection.

    rank_fn: (np.ndarray) -> float  -- scores a block of returns
    Both rankers return a float (higher = better).

    ou_ratio can be per-config (caller sets it) or global fallback.
    """
    if ranker == "tamrs":
        def _tamrs_fn(rets: np.ndarray) -> float:
            return compute_tamrs_for_block(rets, SL_EMP, ou_ratio)
        return _tamrs_fn
    return compute_sharpe


def main():
    rd = results_dir()
    input_file = rd / "trade_returns.jsonl"
    output_file = rd / "cscv_pbo.jsonl"

    all_data = load_jsonl(input_file)
    print(f"Loaded {len(all_data)} configs from {input_file}")
    print(f"Ranker: {CSCV_RANKER} (RBP_CSCV_RANKER)")

    # Load OU calibration for TAMRS ranker (per-config or global)
    ou_per_config: dict[str, float] = {}
    ou_fallback = 1.0
    if CSCV_RANKER == "tamrs":
        ou_file = rd / "ou_calibration.jsonl"
        if ou_file.exists():
            ou_records = load_jsonl(ou_file)
            if ou_records:
                summary = ou_records[0]
                if summary.get("method") == "rolling":
                    for rec in ou_records[1:]:
                        cid = rec.get("config_id")
                        if cid and rec.get("ou_barrier_ratio") is not None:
                            ou_per_config[cid] = rec["ou_barrier_ratio"]
                    print(f"OU method: rolling ({len(ou_per_config)} per-config ratios)")
                elif summary.get("mean_reverting"):
                    ou_fallback = summary.get("ou_barrier_ratio", 1.0)
                    print(f"OU method: full_history (global ratio={ou_fallback})")
                else:
                    print("WARNING: OU not mean-reverting, using ou_ratio=1.0")
        else:
            print("WARNING: ou_calibration.jsonl not found, using ou_ratio=1.0")

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

    config_ids = [d["config_id"] for d in all_data]
    n_configs = len(config_ids)

    # block_returns[config_idx][block_idx] = numpy array of returns in that block
    block_returns = []
    for d in all_data:
        returns = d.get("returns", [])
        timestamps = d.get("timestamps_ms", [])
        blocks = [[] for _ in range(N_SPLITS)]
        for r, ts in zip(returns, timestamps, strict=True):
            block_idx = min(int((ts - ts_min) / block_size), N_SPLITS - 1)
            blocks[block_idx].append(r)
        block_returns.append([np.array(b) for b in blocks])

    # Build per-config ranker functions
    rank_fns = []
    for cid in config_ids:
        ou_ratio = ou_per_config.get(cid, ou_fallback)
        rank_fns.append(_get_ranker_fn(CSCV_RANKER, ou_ratio))

    all_blocks = list(range(N_SPLITS))
    splits = list(combinations(all_blocks, N_SPLITS // 2))
    print(f"Generated {len(splits)} combinatorial splits")

    oos_ranks_of_is_winner = []
    is_winner_configs = []

    for train_blocks in splits:
        test_blocks = [b for b in all_blocks if b not in train_blocks]

        is_scores = np.zeros(n_configs)
        for cfg_idx in range(n_configs):
            train_rets = np.concatenate(
                [block_returns[cfg_idx][b] for b in train_blocks
                 if len(block_returns[cfg_idx][b]) > 0]
            ) if any(len(block_returns[cfg_idx][b]) > 0 for b in train_blocks) else np.array([])
            is_scores[cfg_idx] = rank_fns[cfg_idx](train_rets)

        is_winner_idx = int(np.argmax(is_scores))
        is_winner_configs.append(config_ids[is_winner_idx])

        oos_scores = np.zeros(n_configs)
        for cfg_idx in range(n_configs):
            test_rets = np.concatenate(
                [block_returns[cfg_idx][b] for b in test_blocks
                 if len(block_returns[cfg_idx][b]) > 0]
            ) if any(len(block_returns[cfg_idx][b]) > 0 for b in test_blocks) else np.array([])
            oos_scores[cfg_idx] = rank_fns[cfg_idx](test_rets)

        is_winner_oos = oos_scores[is_winner_idx]
        rank_pct = float(np.mean(oos_scores <= is_winner_oos))
        oos_ranks_of_is_winner.append(rank_pct)

    pbo = float(np.mean(np.array(oos_ranks_of_is_winner) < 0.5))

    winner_counts = Counter(is_winner_configs)
    most_common_winner = winner_counts.most_common(1)[0]

    result = {
        "n_configs": n_configs,
        "n_splits": N_SPLITS,
        "n_combinations": len(splits),
        "ranker": CSCV_RANKER,
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

    with open(output_file, "w") as f:
        f.write(json.dumps(result) + "\n")

    print(f"\nPBO = {pbo:.4f} ({result['pbo_interpretation']})")
    print(f"Ranker: {CSCV_RANKER}")
    print(f"Mean OOS rank of IS winner: {result['mean_oos_rank']:.4f}")
    print(f"Most common IS winner: {most_common_winner[0]} ({most_common_winner[1]}/{len(splits)} splits)")
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()
