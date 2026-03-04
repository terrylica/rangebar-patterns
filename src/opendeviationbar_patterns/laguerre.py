"""ATR-Adaptive Laguerre RSI wrapper for range bar regime conditioning.

Wraps the atr-adaptive-laguerre package to classify range bar data into
volatility regimes (bearish / neutral / bullish) based on the ATR-Adaptive
Laguerre RSI indicator.  Range bars have irregular timestamps, making the
ATR-adaptive gamma especially useful -- it adjusts filter responsiveness
to the bar-local volatility environment.

Usage:
    config = LaguerreRegimeConfig()
    rsi, regimes = compute_laguerre_regimes(df, config)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from atr_adaptive_laguerre import ATRAdaptiveLaguerreRSI, ATRAdaptiveLaguerreRSIConfig


@dataclass(frozen=True)
class LaguerreRegimeConfig:
    """Configuration for ATR-Adaptive Laguerre RSI regime classification.

    Attributes:
        atr_period: ATR lookback period for adaptive gamma calculation.
        smoothing_period: Price smoothing period before Laguerre filter.
        level_up: RSI threshold above which regime is bullish (2).
        level_down: RSI threshold below which regime is bearish (0).
        adaptive_offset: Offset added to adaptive coefficient for period scaling.
    """

    atr_period: int = 14
    smoothing_period: int = 5
    level_up: float = 0.85
    level_down: float = 0.15
    adaptive_offset: float = 0.75


def compute_laguerre_regimes(
    df: pd.DataFrame,
    config: LaguerreRegimeConfig,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute ATR-Adaptive Laguerre RSI and classify into regimes.

    Takes a pandas DataFrame with Title-case OHLCV columns (Open, High, Low,
    Close, Volume) and a DatetimeIndex -- the format produced by data_loader.py --
    and returns RSI values plus regime labels.

    Regime classification:
        0 = bearish  (RSI < level_down)
        1 = neutral  (level_down <= RSI <= level_up)
        2 = bullish  (RSI > level_up)

    Args:
        df: OHLCV DataFrame with Title-case columns and DatetimeIndex.
        config: Laguerre RSI and regime threshold parameters.

    Returns:
        Tuple of (rsi_values, regime_labels) as numpy arrays, both of length
        len(df).  rsi_values are float64 in [0, 1]; regime_labels are int64
        in {0, 1, 2}.

    Raises:
        ValueError: If df is missing required columns or has insufficient rows.
        TypeError: If df is not a pd.DataFrame.
    """
    # Convert Title-case columns to lowercase for the atr-adaptive-laguerre package
    rename_map = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    }
    laguerre_df = df.rename(columns=rename_map)

    # Build config and indicator
    alr_config = ATRAdaptiveLaguerreRSIConfig.single_interval(
        atr_period=config.atr_period,
        smoothing_period=config.smoothing_period,
        adaptive_offset=config.adaptive_offset,
    )
    indicator = ATRAdaptiveLaguerreRSI(alr_config)

    # Compute RSI values (pd.Series, range [0, 1])
    rsi_series = indicator.fit_transform(laguerre_df)
    rsi_values = rsi_series.to_numpy(dtype=np.float64)

    # Classify regimes: 0=bearish, 1=neutral, 2=bullish
    regime_labels = np.ones(len(rsi_values), dtype=np.int64)  # default neutral
    regime_labels[rsi_values < config.level_down] = 0
    regime_labels[rsi_values > config.level_up] = 2

    return rsi_values, regime_labels
