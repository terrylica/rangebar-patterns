"""Test MinBTL gate computation.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""

import math

from rangebar_patterns.eval.minbtl import compute_minbtl


def test_zero_sr_returns_inf():
    result = compute_minbtl(0.0, 1008, 0.0, 3.0)
    assert result == float("inf")


def test_near_zero_sr_returns_inf():
    result = compute_minbtl(1e-9, 1008, 0.0, 3.0)
    assert result == float("inf")


def test_strong_sr_returns_finite():
    result = compute_minbtl(1.0, 1008, 0.0, 3.0)
    assert math.isfinite(result)
    assert result > 0


def test_higher_sr_needs_fewer_trades():
    btl_low = compute_minbtl(0.5, 1008, 0.0, 3.0)
    btl_high = compute_minbtl(1.0, 1008, 0.0, 3.0)
    assert btl_high < btl_low


def test_more_trials_needs_more_trades():
    btl_100 = compute_minbtl(0.5, 100, 0.0, 3.0)
    btl_1000 = compute_minbtl(0.5, 1000, 0.0, 3.0)
    assert btl_1000 > btl_100
