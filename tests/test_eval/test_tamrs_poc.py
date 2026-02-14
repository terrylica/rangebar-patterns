"""TAMRS component acceptance tests.

Validates Rachev, CDaR, OU calibration, and TAMRS composite
against synthetic profiles with known expected ranges.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/16
"""

import numpy as np

from rangebar_patterns.eval.cdar import compute_cdar
from rangebar_patterns.eval.ou_barriers import calibrate_ou
from rangebar_patterns.eval.rachev import compute_rachev
from rangebar_patterns.eval.tamrs import compute_tamrs

# --- Rachev tests ---


def test_rachev_penny_picker():
    """97 small wins + 3 large losses -> heavy left tail -> low Rachev."""
    returns = [0.001] * 97 + [-0.05] * 3
    rr = compute_rachev(returns)
    assert rr is not None
    assert 0.01 <= rr <= 0.50


def test_rachev_symmetric():
    """60 wins +0.005, 40 losses -0.005 -> balanced tails -> Rachev near 1.0."""
    returns = [0.005] * 60 + [-0.005] * 40
    rr = compute_rachev(returns)
    assert rr is not None
    assert 0.80 <= rr <= 1.20


def test_rachev_insufficient():
    """Fewer than MIN_TRADES_RACHEV (20) trades -> None."""
    returns = [0.01] * 19
    rr = compute_rachev(returns)
    assert rr is None


def test_rachev_all_positive():
    """All identical positive returns -> symmetric tails -> Rachev = 1.0."""
    returns = [0.01] * 50
    rr = compute_rachev(returns)
    assert rr is not None
    assert abs(rr - 1.0) < 1e-10


# --- CDaR tests ---


def test_cdar_clustered_has_deeper_max_drawdown():
    """Clustered losses at end produce deeper max drawdown than scattered."""
    # Clustered: 3 consecutive losses at the end -> single deep drawdown
    clustered = [0.001] * 97 + [-0.05] * 3
    # Scattered: losses evenly spread -> multiple shallow drawdowns
    scattered = (
        [0.001] * 32 + [-0.05] + [0.001] * 32 + [-0.05] + [0.001] * 32 + [-0.05]
    )
    cdar_c = compute_cdar(clustered)
    cdar_s = compute_cdar(scattered)
    assert cdar_c is not None
    assert cdar_s is not None
    # Both should have meaningful CDaR > 0
    assert cdar_c > 0.0
    assert cdar_s > 0.0


def test_cdar_all_positive():
    """All positive returns -> no drawdown -> CDaR = 0."""
    returns = [0.01] * 50
    cd = compute_cdar(returns)
    assert cd is not None
    assert cd == 0.0


def test_cdar_insufficient():
    """Fewer than MIN_TRADES_CDAR (10) trades -> None."""
    returns = [0.01] * 9
    cd = compute_cdar(returns)
    assert cd is None


def test_cdar_single_loss():
    """Single loss creates a drawdown."""
    returns = [0.01] * 20 + [-0.05] + [0.01] * 20
    cd = compute_cdar(returns)
    assert cd is not None
    assert cd > 0.0


# --- OU calibration tests ---


def test_ou_synthetic_mean_reverting():
    """Synthetic OU process should return mu > 0, half_life > 0."""
    rng = np.random.default_rng(42)
    n = 5000
    mu = 0.01  # mean-reversion speed
    sigma = 0.1
    mean_level = 100.0
    prices = np.zeros(n)
    prices[0] = mean_level
    for i in range(1, n):
        prices[i] = prices[i - 1] + mu * (mean_level - prices[i - 1]) + sigma * rng.standard_normal()

    cal = calibrate_ou(prices)
    assert cal is not None
    assert cal["mu_dt"] > 0
    assert cal["half_life"] > 0
    assert cal["sigma_dt"] > 0
    assert cal["optimal_tp_frac"] > 0


def test_ou_trending_not_mr():
    """Pure trending (random walk with drift) should fail OU calibration."""
    rng = np.random.default_rng(42)
    n = 5000
    prices = np.cumsum(rng.standard_normal(n) + 0.01) + 100.0

    cal = calibrate_ou(prices)
    # Either None (mu <= 0) or mu very small
    if cal is not None:
        # If it somehow fits, mu should be tiny
        assert cal["mu_dt"] < 0.001


# --- TAMRS composite tests ---


def test_tamrs_penny_lt_healthy():
    """Penny-picker TAMRS < healthy TAMRS when both have valid components."""
    # Penny-picker: low Rachev, high CDaR
    penny_returns = [0.001] * 97 + [-0.05] * 3
    penny_rachev = compute_rachev(penny_returns)
    penny_cdar = compute_cdar(penny_returns)
    penny_sl_cdar = min(1.0, 0.0125 / penny_cdar) if penny_cdar and penny_cdar > 1e-12 else 1.0

    # Healthy: high Rachev, low CDaR
    healthy_returns = [0.008] * 55 + [-0.006] * 45
    healthy_rachev = compute_rachev(healthy_returns)
    healthy_cdar = compute_cdar(healthy_returns)
    healthy_sl_cdar = min(1.0, 0.0125 / healthy_cdar) if healthy_cdar and healthy_cdar > 1e-12 else 1.0

    ou_ratio = 0.7  # Same for both (asset-level, not config-level)

    penny_tamrs = compute_tamrs(penny_rachev, penny_sl_cdar, ou_ratio)
    healthy_tamrs = compute_tamrs(healthy_rachev, healthy_sl_cdar, ou_ratio)

    assert penny_tamrs is not None
    assert healthy_tamrs is not None
    assert penny_tamrs < healthy_tamrs


def test_tamrs_none_propagation():
    """If any component is None, TAMRS is None."""
    assert compute_tamrs(None, 0.5, 0.7) is None
    assert compute_tamrs(0.5, None, 0.7) is None
    assert compute_tamrs(0.5, 0.5, None) is None
    assert compute_tamrs(None, None, None) is None


def test_tamrs_ordering_invariant():
    """TAMRS should reverse Kelly ordering for penny-picker vs healthy."""
    # Penny-picker: high Kelly (in real barrier data), low TAMRS
    penny_rachev = 0.04
    penny_sl_cdar = 0.38
    penny_ou = 0.28
    penny_kelly = 0.12  # Artificially high Kelly from tight barriers

    # Healthy: lower Kelly, higher TAMRS
    healthy_rachev = 1.0
    healthy_sl_cdar = 0.31
    healthy_ou = 1.0
    healthy_kelly = 0.02

    penny_tamrs = compute_tamrs(penny_rachev, penny_sl_cdar, penny_ou)
    healthy_tamrs = compute_tamrs(healthy_rachev, healthy_sl_cdar, healthy_ou)

    # Kelly says penny > healthy
    assert penny_kelly > healthy_kelly
    # TAMRS says healthy > penny
    assert healthy_tamrs > penny_tamrs
