"""Test DSR and PSR computation.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""

import math

from rangebar_patterns.eval.dsr import compute_psr, expected_max_sr, sr_standard_error


def test_expected_max_sr_n1():
    assert expected_max_sr(1, 1.0) == 0.0


def test_expected_max_sr_1008():
    result = expected_max_sr(1008, 1.0)
    # Bailey & Lopez de Prado: ~3.26 for 1008 trials
    assert 3.2 < result < 3.3


def test_sr_standard_error_n1():
    assert sr_standard_error(0.5, 1, 0.0, 3.0) == float("inf")


def test_sr_standard_error_normal():
    # For Gaussian (skew=0, kurt=3), SE = sqrt((1 + 0.5*SR^2) / n)
    se = sr_standard_error(0.0, 100, 0.0, 3.0)
    expected = math.sqrt(1.0 / 100)
    assert abs(se - expected) < 1e-10


def test_psr_zero_sr():
    # SR=0, SR*=0 -> PSR should be 0.5
    se = sr_standard_error(0.0, 100, 0.0, 3.0)
    psr = compute_psr(0.0, 0.0, se)
    assert abs(psr - 0.5) < 1e-6


def test_psr_high_sr():
    # Very high SR should give PSR close to 1.0
    se = sr_standard_error(5.0, 1000, 0.0, 3.0)
    psr = compute_psr(5.0, 0.0, se)
    assert psr > 0.99


def test_psr_invalid_se():
    assert compute_psr(1.0, 0.0, 0.0) == 0.0
    assert compute_psr(1.0, 0.0, float("inf")) == 0.0
