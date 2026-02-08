"""Test E-value and GROW computation.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""

from rangebar_patterns.eval.evalues import compute_evalues


def test_positive_kelly_positive_returns():
    returns = [0.01] * 100
    result = compute_evalues(returns, kelly=0.1)
    assert result["final_evalue"] > 1.0
    assert result["grow_criterion"] > 0
    assert result["kelly_used"] == 0.05  # half-Kelly


def test_negative_kelly_uses_min_bet():
    returns = [0.01, -0.01] * 50
    result = compute_evalues(returns, kelly=-0.5)
    assert result["kelly_used"] == 0.001  # MIN_BET


def test_empty_returns():
    result = compute_evalues([], kelly=0.1)
    assert result["final_evalue"] == 1.0  # exp(0)
    assert result["grow_criterion"] == 0.0


def test_rejection_tracking():
    # Very large positive returns with high Kelly to ensure E crosses threshold
    returns = [0.1] * 500
    result = compute_evalues(returns, kelly=1.0)
    assert result["rejects_null_at_005"] is True
    assert result["first_rejection_trade"] is not None
    assert result["first_rejection_trade"] > 0


def test_no_rejection_weak_signal():
    returns = [0.001, -0.001] * 50
    result = compute_evalues(returns, kelly=0.01)
    assert result["rejects_null_at_005"] is False
