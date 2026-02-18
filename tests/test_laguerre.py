"""Test laguerre.py -- ATR-Adaptive Laguerre RSI regime classification.

Verifies compute_laguerre_regimes returns correct shapes, dtypes, and
regime label values from synthetic OHLCV data.
"""

import numpy as np
import pandas as pd
import pytest

from rangebar_patterns.laguerre import LaguerreRegimeConfig, compute_laguerre_regimes


def _make_synthetic_ohlcv(n: int = 100, seed: int = 42) -> pd.DataFrame:
    """Create a synthetic OHLCV DataFrame with Title-case columns and DatetimeIndex.

    Generates a random walk price series and constructs plausible OHLC bars.
    """
    rng = np.random.default_rng(seed)
    # Random walk for close prices, starting at 100
    returns = rng.normal(0, 0.01, size=n)
    close = 100.0 * np.exp(np.cumsum(returns))

    # Construct OHLC from close with small intra-bar noise
    noise = rng.uniform(0.001, 0.005, size=n)
    high = close * (1 + noise)
    low = close * (1 - noise)
    # Open is previous close (shifted), first bar starts at 100
    open_ = np.roll(close, 1)
    open_[0] = 100.0

    volume = rng.uniform(100, 10000, size=n)

    index = pd.date_range("2024-01-01", periods=n, freq="h")
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=index,
    )


def test_output_shape_and_dtype():
    """RSI and regime arrays have correct length and dtype."""
    df = _make_synthetic_ohlcv(n=100)
    config = LaguerreRegimeConfig()
    rsi, regimes = compute_laguerre_regimes(df, config)

    assert rsi.shape == (100,)
    assert regimes.shape == (100,)
    assert rsi.dtype == np.float64
    assert regimes.dtype == np.int64


def test_rsi_range():
    """RSI values are in [0, 1]."""
    df = _make_synthetic_ohlcv(n=100)
    config = LaguerreRegimeConfig()
    rsi, _ = compute_laguerre_regimes(df, config)

    assert np.all(rsi >= 0.0)
    assert np.all(rsi <= 1.0)


def test_regime_labels_valid():
    """All regime labels are 0, 1, or 2."""
    df = _make_synthetic_ohlcv(n=100)
    config = LaguerreRegimeConfig()
    _, regimes = compute_laguerre_regimes(df, config)

    assert set(np.unique(regimes)).issubset({0, 1, 2})


def test_regime_classification_logic():
    """Regime labels are consistent with RSI values and config thresholds."""
    df = _make_synthetic_ohlcv(n=100)
    config = LaguerreRegimeConfig(level_up=0.85, level_down=0.15)
    rsi, regimes = compute_laguerre_regimes(df, config)

    bearish_mask = rsi < config.level_down
    bullish_mask = rsi > config.level_up
    neutral_mask = ~bearish_mask & ~bullish_mask

    np.testing.assert_array_equal(regimes[bearish_mask], 0)
    np.testing.assert_array_equal(regimes[bullish_mask], 2)
    np.testing.assert_array_equal(regimes[neutral_mask], 1)


def test_custom_config():
    """Non-default config params are accepted and produce valid output."""
    df = _make_synthetic_ohlcv(n=100)
    config = LaguerreRegimeConfig(
        atr_period=10,
        smoothing_period=3,
        level_up=0.70,
        level_down=0.30,
        adaptive_offset=0.5,
    )
    rsi, regimes = compute_laguerre_regimes(df, config)

    assert rsi.shape == (100,)
    assert set(np.unique(regimes)).issubset({0, 1, 2})


def test_config_frozen():
    """LaguerreRegimeConfig is immutable."""
    config = LaguerreRegimeConfig()
    with pytest.raises(AttributeError):
        config.atr_period = 20  # type: ignore[misc]


def test_larger_dataset():
    """Works with a larger dataset (500 bars)."""
    df = _make_synthetic_ohlcv(n=500, seed=99)
    config = LaguerreRegimeConfig()
    rsi, regimes = compute_laguerre_regimes(df, config)

    assert rsi.shape == (500,)
    assert regimes.shape == (500,)
    # With 500 bars of random walk, we expect at least 2 distinct regime labels
    assert len(np.unique(regimes)) >= 2
