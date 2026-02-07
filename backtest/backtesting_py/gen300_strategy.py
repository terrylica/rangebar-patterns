"""Gen300: Champion + duration_us > p75 expanding filter -> LONG.

ADR: docs/adr/2026-02-06-repository-creation.md

Based on champion_strategy.py (2DOWN + ti>p95_rolling + kyle>0).
Adds: duration_us of prior bar > expanding p75 within signal set.

Winner config from Gen300 sweep: Kelly = +0.029, PF = 1.11, 458 signals.
Note: does NOT pass Bonferroni correction (z=0.925, need 3.08).

Exit modes:
  - Gen300 default: Fixed TP=0.5x + SL=0.25x + max_bars=50 (2:1 R:R)

Reference: sql/gen300_template.sql
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


def _rolling_p75_on_signals(duration_arr, is_signal_arr, window=1000):
    """Compute rolling p75 of duration_us over SIGNAL bars only (no lookahead).

    This mirrors the SQL approach: quantile is computed over champion signals
    only, not all bars. Uses prior signals within a rolling window of `window`
    signals (ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING equivalent).
    """
    result = np.full(len(duration_arr), np.nan)
    signal_durations = []
    for i in range(len(duration_arr)):
        if is_signal_arr[i]:
            # Threshold from prior signals within rolling window
            if len(signal_durations) > 0:
                window_data = signal_durations[-window:]
                result[i] = np.percentile(window_data, 75)
            signal_durations.append(duration_arr[i])
    return result


class Gen300DurationFilterLong(Strategy):
    """Gen300: Champion + duration_us > rolling p75 (signal-relative).

    Entry: 2 consecutive DOWN bars AND trade_intensity > rolling p95 (1000 bars)
           AND kyle_lambda_proxy > 0 AND duration_us_lag1 > rolling p75 (1000 signals)
    Exit: Fixed TP=0.5x, SL=0.25x, max_bars=50 (2:1 R:R at @500dbps)
    Direction: LONG only
    """

    ti_window = 1000  # Rolling window size for trade_intensity p95

    # Barrier parameters (threshold-relative multipliers)
    # Set to 0 to disable that barrier. threshold_pct must be set for barriers.
    tp_mult = 0.0     # TP = entry * (1 + tp_mult * threshold_pct)
    sl_mult = 0.0     # Fixed SL = entry * (1 - sl_mult * threshold_pct)
    trail_mult = 0.0  # Trailing SL = running_max * (1 - trail_mult * threshold_pct)
    max_bars = 0       # Time barrier: exit after N bars (0 = disabled)
    threshold_pct = 0.025  # @250dbps = 0.025, @500dbps = 0.05

    def init(self):
        ti = self.data.trade_intensity
        self.ti_p95 = self.I(_rolling_p95, ti, self.ti_window)

        # Pre-identify champion signal bars for expanding p75 computation
        # We need to mark which bars are champion signals to compute
        # duration_us expanding p75 within the signal set (not all bars)
        duration = np.array(self.data.duration_us)
        opens = np.array(self.data.Open)
        closes = np.array(self.data.Close)
        ti_arr = np.array(self.data.trade_intensity)
        kyle_arr = np.array(self.data.kyle_lambda_proxy)
        ti_p95_arr = np.array(self.ti_p95)

        # Mark champion signal bars (same logic as next(), but vectorized)
        is_down = closes < opens
        is_signal = np.zeros(len(duration), dtype=bool)
        for i in range(2, len(duration)):
            if (is_down[i-1] and is_down[i]
                    and ti_arr[i] > ti_p95_arr[i]
                    and kyle_arr[i] > 0
                    and i > self.ti_window):
                is_signal[i] = True

        # Compute expanding p75 of duration_us over signal bars only
        # Uses lag-1 duration (prior bar's value, matching SQL lagInFrame)
        duration_lag1 = np.empty(len(duration))
        duration_lag1[0] = np.nan
        duration_lag1[1:] = duration[:-1]
        self._duration_p75_signal = _rolling_p75_on_signals(duration_lag1, is_signal)
        self._duration_lag1 = duration_lag1
        self._is_champion_signal = is_signal

        self._bars_in_trade = 0
        self._peak_price = 0.0
        self._needs_barrier_setup = False

    def next(self):
        if len(self.data) < 3:
            return

        # Manage open position: barrier setup + time barrier
        if self.position:
            self._bars_in_trade += 1

            # First bar after entry: set TP/SL based on ACTUAL entry price
            if self._needs_barrier_setup and self.trades:
                actual_entry = self.trades[-1].entry_price
                self._peak_price = actual_entry
                if self.tp_mult > 0:
                    self.trades[-1].tp = actual_entry * (1.0 + self.tp_mult * self.threshold_pct)
                if self.sl_mult > 0:
                    self.trades[-1].sl = actual_entry * (1.0 - self.sl_mult * self.threshold_pct)
                self._needs_barrier_setup = False

            # Time barrier: close after max_bars
            if self.max_bars > 0 and self._bars_in_trade >= self.max_bars:
                self.position.close()
                self._bars_in_trade = 0
                self._peak_price = 0.0
                return

            # Check if position was closed by SL/TP (handled by backtesting.py)
            if not self.position:
                self._bars_in_trade = 0
                self._peak_price = 0.0
            return

        # 2 consecutive DOWN bars
        prev_down = self.data.Close[-2] < self.data.Open[-2]
        curr_down = self.data.Close[-1] < self.data.Open[-1]
        two_down = prev_down and curr_down

        # trade_intensity > rolling p95
        ti_high = self.data.trade_intensity[-1] > self.ti_p95[-1]

        # kyle_lambda > 0
        kyle_pos = self.data.kyle_lambda_proxy[-1] > 0

        # Gen300 duration filter: prior bar's duration_us > expanding p75 (signal-relative)
        bar_idx = len(self.data) - 1
        dur_threshold = self._duration_p75_signal[bar_idx]
        dur_value = self._duration_lag1[bar_idx]
        duration_pass = (not np.isnan(dur_threshold)
                         and not np.isnan(dur_value)
                         and dur_value > dur_threshold)

        # Signal: LONG only with duration filter
        if two_down and ti_high and kyle_pos and duration_pass:
            approx_entry = self.data.Close[-1]
            kwargs = {}
            if self.tp_mult > 0:
                kwargs['tp'] = approx_entry * (1.0 + self.tp_mult * self.threshold_pct)
            if self.sl_mult > 0:
                kwargs['sl'] = approx_entry * (1.0 - self.sl_mult * self.threshold_pct)
            self.buy(**kwargs)
            self._bars_in_trade = 0
            self._peak_price = 0.0
            self._needs_barrier_setup = (self.tp_mult > 0 or self.sl_mult > 0)
