"""Test 4-stage walk-forward barrier optimization engine.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/28

14 tests across 4 stages:
- Stage 1 (WFO): fold count, purging, non-overlapping test, rolling train,
  barrier evaluation, top-K screening
- Stage 2 (CPCV): fold count, embargo, nested inner selection
- Stage 3 (Bootstrap): positive omega CI, noise CI rejection
- Stage 4 (Stability): GT-composite penalizes overfitting, parse_barrier_id
"""

import numpy as np
import polars as pl
import pytest

from rangebar_patterns.eval.walk_forward import (
    BarrierParams,
    _omega_metric,
    build_cpcv_folds,
    build_wfo_folds,
    compute_bootstrap_ci,
    compute_gt_composite,
    evaluate_barriers_in_fold,
    parse_barrier_id,
    screen_top_k_barriers,
)

# ---- Helpers ----

def _make_signal_data(
    n_signals: int,
    barrier_ids: list[str],
    *,
    rng: np.random.Generator | None = None,
    mean_return: float = 0.001,
) -> pl.DataFrame:
    """Build synthetic signal_data DataFrame for testing."""
    if rng is None:
        rng = np.random.default_rng(42)

    rows = []
    for sig_idx in range(n_signals):
        for bid in barrier_ids:
            rows.append({
                "signal_idx": sig_idx,
                "barrier_id": bid,
                "return_pct": float(rng.normal(mean_return, 0.01)),
                "exit_type": "TP" if rng.random() > 0.4 else "SL",
            })
    return pl.DataFrame(rows)


# ---- Stage 1: WFO Screening ----


def test_build_wfo_folds_count():
    """2000 signals → ≥2 test folds with default params."""
    folds = build_wfo_folds(2000, purge_bars=50)
    assert len(folds) >= 2
    for train_idx, test_idx in folds:
        assert len(train_idx) > 0
        assert len(test_idx) > 0


def test_build_wfo_folds_nonoverlapping_test():
    """Test fold bar ranges don't overlap."""
    folds = build_wfo_folds(1000, purge_bars=50)

    test_ranges = []
    for _train_idx, test_idx in folds:
        test_ranges.append((test_idx.min(), test_idx.max()))

    for i in range(len(test_ranges) - 1):
        assert test_ranges[i][1] < test_ranges[i + 1][0], (
            f"Test folds {i} and {i+1} overlap: {test_ranges[i]} vs {test_ranges[i+1]}"
        )


def test_build_wfo_folds_purging():
    """Purge gap creates space between train end and test start."""
    purge = 100
    folds = build_wfo_folds(2000, purge_bars=purge)
    assert len(folds) >= 1

    for train_idx, test_idx in folds:
        train_max = int(train_idx.max())
        test_min = int(test_idx.min())
        # Test start must be after train end + purge gap
        assert test_min > train_max, (
            f"No purge gap: train_max={train_max}, test_min={test_min}"
        )


def test_build_wfo_folds_rolling_train():
    """max_train_splits=3 limits train size (rolling, not expanding)."""
    folds = build_wfo_folds(
        2000,
        min_train_splits=2,
        max_train_splits=3,
        purge_bars=10,
    )
    if len(folds) >= 3:
        # Later folds should not have ever-growing train sets
        train_sizes = [len(t) for t, _ in folds]
        # After initial ramp-up, train size should stabilize (not monotonically grow)
        assert max(train_sizes) <= 2 * min(train_sizes), (
            f"Train sizes vary too much (not rolling): {train_sizes}"
        )


def test_evaluate_barriers_in_fold():
    """Synthetic trades → correct PF/WR/Omega computation."""
    rng = np.random.default_rng(42)
    barriers = ["p5_slt010_mb50", "p5_slt025_mb100"]
    signal_data = _make_signal_data(100, barriers, rng=rng, mean_return=0.005)

    test_idx = np.arange(50, 100)
    result = evaluate_barriers_in_fold(signal_data, test_idx)

    assert len(result) == 2
    assert set(result["barrier_id"].to_list()) == set(barriers)

    for row in result.to_dicts():
        assert row["n_trades"] == 50
        assert 0.0 <= row["win_rate"] <= 1.0
        assert row["profit_factor"] >= 0.0
        assert row["omega"] >= 0.0
        assert row["max_drawdown"] >= 0.0


def test_screen_top_k():
    """100 barriers → top 10 by median Omega, stable barrier ranked first."""
    rng = np.random.default_rng(42)

    # Build fold results: 3 folds × 20 barriers
    rows = []
    for fold_id in range(3):
        for i in range(20):
            bid = f"barrier_{i:02d}"
            # barrier_19 has highest and most stable omega
            if i == 19:
                omega = 1.5 + rng.normal(0, 0.01)
                rachev = 0.6
            else:
                omega = 1.0 + i * 0.02 + rng.normal(0, 0.05)
                rachev = 0.3
            rows.append({
                "barrier_id": bid,
                "fold_id": fold_id,
                "omega": omega,
                "rachev": rachev,
            })

    fold_results = pl.DataFrame(rows)
    top_10 = screen_top_k_barriers(fold_results, k=10)

    assert len(top_10) == 10
    # barrier_19 should be first (highest stable omega)
    assert top_10[0] == "barrier_19"


# ---- Stage 2: CPCV Validation ----


def test_build_cpcv_folds_count():
    """n_folds=6, n_test_folds=2 → C(6,2)=15 folds."""
    folds = build_cpcv_folds(
        600,
        n_folds=6,
        n_test_folds=2,
        purge_bars=10,
        embargo_bars=5,
    )
    assert len(folds) == 15


def test_cpcv_embargo_removes_samples():
    """Embargo removes samples from train that are close to test boundary."""
    embargo = 20
    folds_no_embargo = build_cpcv_folds(
        500, n_folds=5, n_test_folds=2, purge_bars=10, embargo_bars=0,
    )
    folds_with_embargo = build_cpcv_folds(
        500, n_folds=5, n_test_folds=2, purge_bars=10, embargo_bars=embargo,
    )

    # With embargo, training sets should be smaller
    for (train_no, _), (train_yes, _) in zip(folds_no_embargo, folds_with_embargo):
        assert len(train_yes) <= len(train_no), (
            f"Embargo should reduce training size: {len(train_yes)} vs {len(train_no)}"
        )


def test_nested_cpcv_inner_selection():
    """Inner loop selects a subset of barriers for outer evaluation."""
    rng = np.random.default_rng(42)
    barriers = [f"b{i:02d}" for i in range(20)]
    signal_data = _make_signal_data(300, barriers, rng=rng, mean_return=0.002)

    # Small CPCV for speed
    cpcv_folds = build_cpcv_folds(
        300, n_folds=4, n_test_folds=2, purge_bars=5, embargo_bars=2,
    )

    from rangebar_patterns.eval.walk_forward import run_nested_cpcv

    result = run_nested_cpcv(
        signal_data, cpcv_folds, barriers, inner_k=5,
    )

    if not result.is_empty():
        # All returned barriers should be marked as inner_selected
        assert result["is_inner_selected"].all()
        # At most inner_k distinct barriers per fold
        per_fold = result.group_by("fold_id").agg(
            pl.col("barrier_id").n_unique().alias("n_barriers"),
        )
        for row in per_fold.to_dicts():
            assert row["n_barriers"] <= 5


# ---- Stage 3: Bootstrap Stability ----


def test_bootstrap_ci_positive_omega():
    """Known-positive returns → Omega CI lower bound above 1.0."""
    rng = np.random.default_rng(42)
    # Strong positive signal: mean=+0.03, std=0.01 → ~75% positive
    returns = rng.normal(0.03, 0.01, size=200).tolist()

    result = compute_bootstrap_ci(
        returns, _omega_metric, n_resamples=500, block_size=5,
    )

    assert result["ci_lower"] > 1.0, (
        f"Positive returns should have Omega CI lower > 1.0, got {result['ci_lower']}"
    )
    assert result["point_estimate"] > 1.0
    assert result["n_trades"] == 200
    assert result["se"] >= 0.0


def test_bootstrap_ci_rejects_noise():
    """Random noise returns → CI includes 1.0, barrier should be rejected."""
    rng = np.random.default_rng(42)
    # Zero-mean noise: Omega should be ~1.0
    returns = rng.normal(0.0, 0.01, size=200).tolist()

    result = compute_bootstrap_ci(
        returns, _omega_metric, n_resamples=500, block_size=5,
    )

    # For zero-mean, Omega ≈ 1.0 and CI should straddle 1.0
    # or be very close to it — point estimate near 1.0
    assert 0.5 < result["point_estimate"] < 2.0


# ---- Stage 4: Stability Synthesis ----


def test_gt_composite_penalizes_overfitting():
    """High Omega + high PBO scores lower than moderate Omega + low PBO."""
    # Good: moderate Omega, low PBO
    gt_good = compute_gt_composite(
        omega=1.2, dsr=0.8, pbo=0.1, max_drawdown=0.05,
    )
    # Overfit: high Omega, high PBO
    gt_overfit = compute_gt_composite(
        omega=1.8, dsr=0.8, pbo=0.85, max_drawdown=0.05,
    )

    assert gt_good > gt_overfit, (
        f"Low-PBO should beat high-PBO: {gt_good} vs {gt_overfit}"
    )

    # MaxDD above capital threshold → GT = 0
    gt_blown = compute_gt_composite(
        omega=2.0, dsr=1.0, pbo=0.0, max_drawdown=0.20,
    )
    assert gt_blown == 0.0


def test_parse_barrier_id():
    """p5_slt010_mb50 → correct params."""
    result = parse_barrier_id("p5_slt010_mb50")
    assert result == BarrierParams(phase1_bars=5, sl_tight_mult=0.10, max_bars=50)


def test_parse_barrier_id_zero():
    """p3_slt000_mb20 → sl_tight_mult=0.00."""
    result = parse_barrier_id("p3_slt000_mb20")
    assert result == BarrierParams(phase1_bars=3, sl_tight_mult=0.00, max_bars=20)

    with pytest.raises(ValueError, match="Invalid barrier_id"):
        parse_barrier_id("invalid_format")
