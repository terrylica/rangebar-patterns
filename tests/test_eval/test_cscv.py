"""Test CSCV/PBO computation helpers.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""

import numpy as np

from rangebar_patterns.eval.cscv import compute_sharpe


def test_compute_sharpe_positive():
    returns = np.array([0.01, 0.02, -0.005, 0.015, 0.01])
    sr = compute_sharpe(returns)
    assert sr > 0


def test_compute_sharpe_negative():
    returns = np.array([-0.01, -0.02, 0.005, -0.015, -0.01])
    sr = compute_sharpe(returns)
    assert sr < 0


def test_compute_sharpe_zero_std():
    returns = np.array([0.01, 0.01, 0.01])
    sr = compute_sharpe(returns)
    assert sr == 0.0


def test_compute_sharpe_single_element():
    returns = np.array([0.05])
    sr = compute_sharpe(returns)
    assert sr == 0.0
