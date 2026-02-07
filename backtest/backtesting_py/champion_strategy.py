"""Champion pattern: 2DOWN + ti>p95_rolling + kyle>0 -> LONG.

ADR: docs/adr/2026-02-06-repository-creation.md

Long-only. No shorts (they lose on SOL).

Exit modes:
  - Default (tp_mult=0, sl_mult=0): Exit after 1 bar (original)
  - Gen200 (tp_mult>0, sl_mult>0): Fixed TP + fixed SL + time barrier
  - Gen201 (tp_mult>0, trail_mult>0): Fixed TP + trailing SL + time barrier
  - Gen202 (all three >0): Fixed TP + trailing SL + time barrier (combined)

Reference: sql/gen111_true_nolookahead.sql, gen200, gen201, gen202
GitHub Issues: #3 (Gen200), #4 (Gen201), #5 (Gen202), #7 (backtest align)
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


class ChampionMeanRevLong(Strategy):
    """Champion mean-reversion long strategy on range bars.

    Entry: 2 consecutive DOWN bars AND trade_intensity > rolling p95 (1000 bars)
           AND kyle_lambda_proxy > 0
    Exit: Configurable via class params (see below)
    Direction: LONG only (shorts lose on SOL)
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
        self._bars_in_trade = 0
        self._peak_price = 0.0
        self._needs_barrier_setup = False

    def next(self):
        if len(self.data) < 3:
            return

        # Manage open position: barrier setup + trailing stop ratchet + time barrier
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
                elif self.trail_mult > 0:
                    self.trades[-1].sl = actual_entry * (1.0 - self.trail_mult * self.threshold_pct)
                self._needs_barrier_setup = False

            # Trailing stop: ratchet SL upward
            if self.trail_mult > 0:
                current_high = self.data.High[-1]
                if current_high > self._peak_price:
                    self._peak_price = current_high
                    new_sl = self._peak_price * (1.0 - self.trail_mult * self.threshold_pct)
                    for trade in self.trades:
                        if trade.sl is None or new_sl > trade.sl:
                            trade.sl = new_sl

            # Time barrier: close after max_bars
            if self.max_bars > 0 and self._bars_in_trade >= self.max_bars:
                self.position.close()
                self._bars_in_trade = 0
                self._peak_price = 0.0
                return

            # Original 1-bar exit (when no barriers configured)
            if self.tp_mult == 0 and self.sl_mult == 0 and self.trail_mult == 0 and self.max_bars == 0:
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

        # Signal: LONG only
        # Set approximate SL/TP at buy time (signal close), corrected on first next()
        if two_down and ti_high and kyle_pos:
            approx_entry = self.data.Close[-1]
            kwargs = {}
            if self.tp_mult > 0:
                kwargs['tp'] = approx_entry * (1.0 + self.tp_mult * self.threshold_pct)
            if self.sl_mult > 0:
                kwargs['sl'] = approx_entry * (1.0 - self.sl_mult * self.threshold_pct)
            elif self.trail_mult > 0:
                kwargs['sl'] = approx_entry * (1.0 - self.trail_mult * self.threshold_pct)
            self.buy(**kwargs)
            self._bars_in_trade = 0
            self._peak_price = 0.0
            self._needs_barrier_setup = (self.tp_mult > 0 or self.sl_mult > 0 or self.trail_mult > 0)
