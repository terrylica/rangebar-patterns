"""Test Cornish-Fisher quantile expansion.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""

from scipy.stats import norm

from rangebar_patterns.eval.cornish_fisher import cf_expected_shortfall, cf_var, cornish_fisher_quantile


def test_gaussian_case():
    """For Gaussian (skew=0, kurt=3), CF quantile = standard normal quantile."""
    z_05 = norm.ppf(0.05)  # -1.6449
    cf_q = cornish_fisher_quantile(z_05, skew=0.0, kurt=3.0)
    assert abs(cf_q - z_05) < 1e-10


def test_negative_skew_shifts_left():
    """Negative skew should push the left tail quantile further left."""
    z_05 = norm.ppf(0.05)
    cf_normal = cornish_fisher_quantile(z_05, skew=0.0, kurt=3.0)
    cf_skewed = cornish_fisher_quantile(z_05, skew=-1.0, kurt=3.0)
    assert cf_skewed < cf_normal


def test_positive_kurtosis_changes_tail():
    """Excess kurtosis > 0 (kurt > 3) should change the CF quantile from Gaussian."""
    z_05 = norm.ppf(0.05)
    cf_normal = cornish_fisher_quantile(z_05, skew=0.0, kurt=3.0)
    cf_fat = cornish_fisher_quantile(z_05, skew=0.0, kurt=6.0)
    assert cf_fat != cf_normal


def test_cf_var_negative():
    result = cf_var(mean=0.001, std=0.02, skew=-0.5, kurt=4.0, alpha=0.05)
    assert result < 0  # VaR at 5% is negative (loss)


def test_cf_es_is_finite():
    es = cf_expected_shortfall(mean=0.001, std=0.02, skew=-0.5, kurt=4.0, alpha=0.05)
    assert es < 0  # ES should be a negative number (loss)
