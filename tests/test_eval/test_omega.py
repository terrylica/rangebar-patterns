"""Test Omega Ratio computation.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""

from rangebar_patterns.eval.omega import compute_omega


def test_all_gains():
    result = compute_omega([0.1, 0.2, 0.3], threshold=0.0)
    assert result == float("inf")


def test_all_losses():
    result = compute_omega([-0.1, -0.2, -0.3], threshold=0.0)
    assert result == 0.0


def test_known_value():
    # gains: 0.1 + 0.03 = 0.13, losses: 0.05 -> ratio = 0.13/0.05 = 2.6
    result = compute_omega([0.1, -0.05, 0.03], threshold=0.0)
    assert abs(result - 2.6) < 1e-10


def test_balanced():
    # One gain of 0.1, one loss of 0.1 -> ratio = 1.0
    result = compute_omega([0.1, -0.1], threshold=0.0)
    assert abs(result - 1.0) < 1e-10


def test_nonzero_threshold():
    # With threshold=0.05: gains above 0.05 = [0.05], losses below 0.05 = [0.15]
    result = compute_omega([0.1, -0.1], threshold=0.05)
    assert abs(result - (0.05 / 0.15)) < 1e-10


def test_empty_returns():
    result = compute_omega([], threshold=0.0)
    assert result == 1.0
