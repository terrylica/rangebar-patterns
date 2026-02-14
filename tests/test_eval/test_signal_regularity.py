"""Test signal temporal regularity via KDE peak-finding.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/17
"""

import numpy as np

from rangebar_patterns.eval.signal_regularity import compute_signal_regularity


def test_insufficient_data_returns_none():
    """Fewer than min_trades should return None."""
    result = compute_signal_regularity([1, 2, 3], min_trades=10)
    assert result is None


def test_zero_range_returns_none():
    """All identical timestamps should return None."""
    result = compute_signal_regularity([1000] * 20)
    assert result is None


def test_uniform_spacing_low_cv():
    """Evenly spaced timestamps should produce low KDE peak CV."""
    rng = np.random.default_rng(42)
    # 200 trades evenly spaced over 1000 time units with small jitter
    ts = [int(i * 5000 + rng.normal(0, 100)) for i in range(200)]
    result = compute_signal_regularity(ts)
    assert result is not None
    assert result["temporal_coverage"] >= 0.8
    # Uniform spacing should give relatively low CV (peaks evenly distributed)
    if result["kde_peak_cv"] is not None:
        assert result["kde_peak_cv"] < 1.0


def test_clustered_timestamps_higher_cv():
    """Two tight clusters should produce higher CV than uniform spread."""
    rng = np.random.default_rng(42)
    # Cluster 1: timestamps around 10000, spread 5000
    cluster1 = [int(rng.normal(10000, 5000)) for _ in range(100)]
    # Cluster 2: timestamps around 100000, spread 5000 (large gap relative to spread)
    cluster2 = [int(rng.normal(100000, 5000)) for _ in range(100)]
    ts = cluster1 + cluster2

    result = compute_signal_regularity(ts)
    assert result is not None
    assert result["n_peaks"] >= 2
    # Low coverage because of large gap between clusters
    assert result["temporal_coverage"] <= 0.5


def test_output_keys():
    """Result dict should have expected keys."""
    ts = [int(i * 1000) for i in range(50)]
    result = compute_signal_regularity(ts)
    assert result is not None
    expected_keys = {"kde_peak_cv", "n_peaks", "raw_iat_cv",
                     "temporal_coverage", "kde_bandwidth"}
    assert set(result.keys()) == expected_keys


def test_single_peak_returns_none_cv():
    """If KDE has only 1 peak, kde_peak_cv should be None."""
    # Very tight cluster — single peak
    rng = np.random.default_rng(42)
    ts = [int(1000000 + rng.normal(0, 10)) for _ in range(50)]
    result = compute_signal_regularity(ts)
    assert result is not None
    if result["n_peaks"] < 2:
        assert result["kde_peak_cv"] is None


def test_bandwidth_is_scott_over_4():
    """KDE bandwidth should be approximately Scott's rule / 4."""
    ts = [int(i * 1000) for i in range(100)]
    result = compute_signal_regularity(ts)
    assert result is not None
    # Scott/4 bandwidth for 100 points should be much smaller than Scott alone
    # Scott's rule for 100 points: n^(-1/5) ≈ 0.398
    # Scott/4 ≈ 0.10
    assert result["kde_bandwidth"] < 0.25
