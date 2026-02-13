"""Gen600: Parameterized multi-pattern + dual feature filter strategy.

ADR: docs/adr/2026-02-06-repository-creation.md
GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/14

Based on champion_strategy.py barrier/exit logic.
Supports all 22 Gen600 pattern types with any 2-feature filter combination.

POC config: udd__volume_per_trade_lt_p50__lookback_price_range_lt_p50
  Pattern: UP-DOWN-DOWN (3-bar reversal)
  Filter 1: volume_per_trade < rolling p50 (within signal set)
  Filter 2: lookback_price_range < rolling p50 (within signal set)
  Barrier: symmetric (TP=0.50x, SL=0.50x, max_bars=50)

Reference: sql/gen600_udd_template.sql
AP-15: Current row IS the last pattern bar.
"""

import numpy as np
from backtesting import Strategy


def _rolling_p95(x, window=1000):
    """Compute rolling p95 of trade_intensity with fixed window."""
    result = np.empty(len(x))
    for i in range(len(x)):
        start = max(0, i + 1 - window)
        result[i] = np.percentile(x[start : i + 1], 95)
    return result


def _rolling_quantile_on_signals(feature_arr, is_signal_arr, quantile_pct, window=1000):
    """Compute rolling quantile of a feature over SIGNAL bars only.

    Mirrors SQL: quantileExactExclusive(pct)(feature) OVER (
        ORDER BY timestamp_ms ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
    ) — but computed over the signal set, not all bars.

    Args:
        feature_arr: Feature values for ALL bars.
        is_signal_arr: Boolean mask of which bars are champion signals.
        quantile_pct: Quantile level (e.g., 0.50 for median).
        window: Number of prior signals to include (default 1000).

    Returns array of quantile thresholds (NaN for non-signal or insufficient history).
    """
    result = np.full(len(feature_arr), np.nan)
    signal_values = []
    for i in range(len(feature_arr)):
        if is_signal_arr[i]:
            if len(signal_values) > 0:
                window_data = signal_values[-window:]
                result[i] = np.percentile(window_data, quantile_pct * 100)
            # Only append non-NaN values (matches SQL quantileExactExclusive NULL handling)
            if not np.isnan(feature_arr[i]):
                signal_values.append(feature_arr[i])
    return result


# Pattern detection functions — each returns a boolean mask
def _detect_2down(direction):
    """2 consecutive DOWN bars: dir[i-1]=0, dir[i]=0."""
    mask = np.zeros(len(direction), dtype=bool)
    for i in range(1, len(direction)):
        mask[i] = direction[i - 1] == 0 and direction[i] == 0
    return mask


def _detect_udd(direction):
    """UP-DOWN-DOWN: dir[i-2]=1, dir[i-1]=0, dir[i]=0."""
    mask = np.zeros(len(direction), dtype=bool)
    for i in range(2, len(direction)):
        mask[i] = direction[i - 2] == 1 and direction[i - 1] == 0 and direction[i] == 0
    return mask


def _detect_dud(direction):
    """DOWN-UP-DOWN: dir[i-2]=0, dir[i-1]=1, dir[i]=0."""
    mask = np.zeros(len(direction), dtype=bool)
    for i in range(2, len(direction)):
        mask[i] = direction[i - 2] == 0 and direction[i - 1] == 1 and direction[i] == 0
    return mask


def _detect_3down(direction):
    """3 consecutive DOWN: dir[i-2]=0, dir[i-1]=0, dir[i]=0."""
    mask = np.zeros(len(direction), dtype=bool)
    for i in range(2, len(direction)):
        mask[i] = direction[i - 2] == 0 and direction[i - 1] == 0 and direction[i] == 0
    return mask


def _rolling_p75(x, window=1000):
    """Compute rolling p75 with fixed window (matches SQL ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING)."""
    result = np.empty(len(x))
    for i in range(len(x)):
        start = max(0, i + 1 - window)
        # Use values PRECEDING current bar (exclude current)
        if i > 0:
            window_data = x[start:i]
            # Filter NaN (intra_max_drawdown is Nullable)
            clean = window_data[~np.isnan(window_data)]
            result[i] = np.percentile(clean, 75) if len(clean) > 0 else np.nan
        else:
            result[i] = np.nan
    return result


PATTERN_DETECTORS = {
    "2down": _detect_2down,
    "udd": _detect_udd,
    "dud": _detect_dud,
    "3down": _detect_3down,
}

# Exhaustion patterns use different champion gates (no TI/kyle)
EXHAUSTION_PATTERNS = {"exh_l", "exh_l_ng"}


class Gen600Strategy(Strategy):
    """Gen600: Parameterized pattern + dual feature filter + triple barrier.

    Class parameters (set before Backtest.run()):
        pattern: Pattern name (e.g., "udd", "2down", "3down", "dud")
        feature1_name: Column name for feature 1 (e.g., "volume_per_trade")
        feature1_direction: "lt" or "gt"
        feature1_quantile: Quantile level (e.g., 0.50)
        feature2_name: Column name for feature 2 (e.g., "lookback_price_range")
        feature2_direction: "lt" or "gt"
        feature2_quantile: Quantile level (e.g., 0.50)
        tp_mult, sl_mult, max_bars, threshold_pct: Barrier params
    """

    ti_window = 1000

    # Pattern
    pattern = "udd"

    # Feature filters
    feature1_name = "volume_per_trade"
    feature1_direction = "lt"  # "lt" or "gt"
    feature1_quantile = 0.50
    feature2_name = "lookback_price_range"
    feature2_direction = "lt"
    feature2_quantile = 0.50

    # Barrier parameters
    tp_mult = 0.50
    sl_mult = 0.50
    max_bars = 50
    threshold_pct = 0.10  # @1000dbps = 0.10

    def init(self):
        opens = np.array(self.data.Open)
        closes = np.array(self.data.Close)

        # Compute direction: 1 = UP, 0 = DOWN
        direction = (closes > opens).astype(int)

        if self.pattern in EXHAUSTION_PATTERNS:
            # Exhaustion patterns: DOWN bar + intra_max_drawdown > p75_rolling
            mdd_arr = np.array(self.data.intra_max_drawdown, dtype=float)
            self.mdd_p75 = self.I(_rolling_p75, mdd_arr, self.ti_window)
            mdd_p75_arr = np.array(self.mdd_p75)

            is_signal = np.zeros(len(opens), dtype=bool)
            for i in range(len(opens)):
                if (direction[i] == 0  # DOWN bar
                        and not np.isnan(mdd_arr[i])
                        and not np.isnan(mdd_p75_arr[i])
                        and mdd_arr[i] > mdd_p75_arr[i]
                        and i > self.ti_window):
                    is_signal[i] = True
        else:
            # Standard patterns: pattern_mask + TI > p95 + kyle > 0
            ti = self.data.trade_intensity
            self.ti_p95 = self.I(_rolling_p95, ti, self.ti_window)
            ti_arr = np.array(self.data.trade_intensity)
            kyle_arr = np.array(self.data.kyle_lambda_proxy)
            ti_p95_arr = np.array(self.ti_p95)

            detector = PATTERN_DETECTORS.get(self.pattern)
            if detector is None:
                available = list(PATTERN_DETECTORS.keys()) + list(EXHAUSTION_PATTERNS)
                raise ValueError(f"Unknown pattern: {self.pattern}. Available: {available}")
            pattern_mask = detector(direction)

            is_signal = np.zeros(len(opens), dtype=bool)
            for i in range(len(opens)):
                if (pattern_mask[i]
                        and ti_arr[i] > ti_p95_arr[i]
                        and kyle_arr[i] > 0
                        and i > self.ti_window):
                    is_signal[i] = True

        # Feature 1: rolling quantile over signal set
        f1_arr = self._get_feature_array(self.feature1_name, opens, closes)
        self._f1_quantile = _rolling_quantile_on_signals(
            f1_arr, is_signal, self.feature1_quantile,
        )
        self._f1_values = f1_arr

        # Feature 2: rolling quantile over signal set
        f2_arr = self._get_feature_array(self.feature2_name, opens, closes)
        self._f2_quantile = _rolling_quantile_on_signals(
            f2_arr, is_signal, self.feature2_quantile,
        )
        self._f2_values = f2_arr

        self._is_champion_signal = is_signal
        self._direction = direction
        self._signal_timestamps = []  # signal_bar_timestamp_ms for oracle matching
        # Per-trade time barrier: id(trade) -> entry_bar_index
        self._trade_entry_bar = {}
        self._known_trades = set()

    def _get_feature_array(self, name, opens, closes):
        """Get feature values, computing derived features if needed."""
        if name == "opposite_wick_pct":
            highs = np.array(self.data.High)
            lows = np.array(self.data.Low)
            result = np.empty(len(opens))
            for i in range(len(opens)):
                hl_range = highs[i] - lows[i]
                if hl_range == 0:
                    result[i] = np.nan
                elif closes[i] <= opens[i]:  # DOWN bar: upper wick
                    result[i] = (highs[i] - opens[i]) / hl_range
                else:  # UP bar: lower wick
                    result[i] = (opens[i] - lows[i]) / hl_range
            return result
        return np.array(getattr(self.data, name))

    def _check_feature(self, idx, values, quantile, direction):
        """Check if feature passes the quantile filter at bar idx."""
        q = quantile[idx]
        v = values[idx]
        if np.isnan(q) or np.isnan(v):
            return False
        if direction == "lt":
            return v < q
        return v > q

    def next(self):
        if len(self.data) < 4:
            return

        current_bar = len(self.data) - 1

        # Multi-position management (hedging=True, exclusive_orders=False):
        # Each signal opens an independent position with its own barriers.

        # 1. Register newly filled trades (appeared since last bar)
        for trade in self.trades:
            tid = id(trade)
            if tid not in self._known_trades:
                self._known_trades.add(tid)
                self._trade_entry_bar[tid] = current_bar
                # Set exact TP/SL from actual fill price
                actual_entry = trade.entry_price
                if self.tp_mult > 0:
                    trade.tp = actual_entry * (1.0 + self.tp_mult * self.threshold_pct)
                if self.sl_mult > 0:
                    trade.sl = actual_entry * (1.0 - self.sl_mult * self.threshold_pct)

        # 2. Check time barrier for each open trade
        for trade in list(self.trades):
            tid = id(trade)
            entry_bar = self._trade_entry_bar.get(tid, current_bar)
            bars_held = current_bar - entry_bar
            if self.max_bars > 0 and bars_held >= self.max_bars:
                trade.close()
                self._trade_entry_bar.pop(tid, None)

        # 3. Check for new signal entry
        bar_idx = current_bar

        if not self._is_champion_signal[bar_idx]:
            return

        # Check feature filters
        f1_pass = self._check_feature(
            bar_idx, self._f1_values, self._f1_quantile, self.feature1_direction,
        )
        f2_pass = self._check_feature(
            bar_idx, self._f2_values, self._f2_quantile, self.feature2_direction,
        )
        if not f1_pass or not f2_pass:
            return

        # Record signal bar timestamp for oracle matching
        signal_ts_ms = int(self.data.index[-1].timestamp() * 1000)
        self._signal_timestamps.append(signal_ts_ms)

        # Entry — hedging mode allows multiple concurrent positions.
        # Use fixed small size (1% equity) to avoid margin exhaustion with overlaps.
        approx_entry = self.data.Close[-1]
        kwargs = {"size": 0.01}
        if self.tp_mult > 0:
            kwargs["tp"] = approx_entry * (1.0 + self.tp_mult * self.threshold_pct)
        if self.sl_mult > 0:
            kwargs["sl"] = approx_entry * (1.0 - self.sl_mult * self.threshold_pct)
        self.buy(**kwargs)
