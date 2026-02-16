"""Gen720: Two-segment SL time-decay barrier strategy for oracle validation.

Extends Gen600Strategy with phase-based SL tightening:
  Phase 1 (bars 1..phase1_bars): Wide SL (sl_mult)
  Phase 2 (bars phase1_bars+1..max_bars): Tight SL (sl_tight_mult)

No 2F feature filter — raw formation signals for maximum WFO data.

Oracle audit: 10-point check in plan (Checks #7, #9 ALIGNED).
  - trade.sl setter cancels old SL order, creates new one
  - New SL checked on NEXT bar (matches SQL segment 2 starting at phase1_bars + 1)
  - Initial SL set at buy() time for reprocess_orders treatment

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/28
"""

import numpy as np
from backtesting import Strategy

try:
    from gen600_strategy import (
        EXHAUSTION_PATTERNS,
        PATTERN_DETECTORS,
        _rolling_p75,
        _rolling_p95,
    )
except ModuleNotFoundError:
    from backtest.backtesting_py.gen600_strategy import (
        EXHAUSTION_PATTERNS,
        PATTERN_DETECTORS,
        _rolling_p75,
        _rolling_p95,
    )


class Gen720Strategy(Strategy):
    """Gen720: Two-segment SL time-decay barrier.

    Class parameters (set before Backtest.run()):
        pattern: Pattern name (same as Gen600)
        tp_mult: Take profit multiplier (default 0.25)
        sl_mult: Wide SL multiplier — used in phase 1 (default 0.50)
        sl_tight_mult: Tight SL multiplier — used in phase 2 (default 0.10)
        phase1_bars: Bars before SL transitions from wide to tight (default 5)
        max_bars: Time barrier (default 100)
        threshold_pct: Range bar threshold as decimal (e.g., 0.05 for @500dbps)
    """

    ti_window = 1000

    # Pattern
    pattern = "2down"

    # Barrier parameters (Gen510 optimal: tight TP, wide SL)
    tp_mult = 0.25
    sl_mult = 0.50       # Wide SL (phase 1)
    sl_tight_mult = 0.10  # Tight SL (phase 2)
    phase1_bars = 5
    max_bars = 100
    threshold_pct = 0.05  # @500dbps

    def init(self):
        opens = np.array(self.data.Open)
        closes = np.array(self.data.Close)
        direction = (closes > opens).astype(int)

        if self.pattern in EXHAUSTION_PATTERNS:
            mdd_arr = np.array(self.data.intra_max_drawdown, dtype=float)
            self.mdd_p75 = self.I(_rolling_p75, mdd_arr, self.ti_window)
            mdd_p75_arr = np.array(self.mdd_p75)

            is_signal = np.zeros(len(opens), dtype=bool)
            for i in range(len(opens)):
                if (direction[i] == 0
                        and not np.isnan(mdd_arr[i])
                        and not np.isnan(mdd_p75_arr[i])
                        and mdd_arr[i] > mdd_p75_arr[i]
                        and i > self.ti_window):
                    is_signal[i] = True
        else:
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

        self._is_signal = is_signal
        self._signal_timestamps = []
        self._trade_entry_bar = {}
        self._known_trades = set()
        self._sl_tightened = set()  # Track which trades have been tightened

    def next(self):
        if len(self.data) < 4:
            return

        current_bar = len(self.data) - 1

        # 1. Register newly filled trades
        for trade in self.trades:
            tid = id(trade)
            if tid not in self._known_trades:
                self._known_trades.add(tid)
                self._trade_entry_bar[tid] = current_bar
                # Set TP + initial wide SL from actual fill price
                # CRITICAL: Set at buy() registration for reprocess_orders treatment
                actual_entry = trade.entry_price
                if self.tp_mult > 0:
                    trade.tp = actual_entry * (1.0 + self.tp_mult * self.threshold_pct)
                if self.sl_mult > 0:
                    trade.sl = actual_entry * (1.0 - self.sl_mult * self.threshold_pct)

        # 2. Two-segment SL + time barrier for existing trades
        for trade in list(self.trades):
            tid = id(trade)
            entry_bar = self._trade_entry_bar.get(tid, current_bar)
            bars_held = current_bar - entry_bar

            # Phase 2 SL tightening: one-time, on the exact transition bar
            # Use == (not >=) to avoid re-creating SL orders every bar
            if (bars_held == self.phase1_bars
                    and tid not in self._sl_tightened
                    and self.sl_tight_mult < self.sl_mult):
                actual_entry = trade.entry_price
                trade.sl = actual_entry * (1.0 - self.sl_tight_mult * self.threshold_pct)
                self._sl_tightened.add(tid)

            # Time barrier
            if self.max_bars > 0 and bars_held >= self.max_bars:
                trade.close()
                self._trade_entry_bar.pop(tid, None)
                self._sl_tightened.discard(tid)

        # 3. Check for new signal entry (no 2F feature filter)
        bar_idx = current_bar
        if not self._is_signal[bar_idx]:
            return

        signal_ts_ms = int(self.data.index[-1].timestamp() * 1000)
        self._signal_timestamps.append(signal_ts_ms)

        # Entry with wide SL (phase 1)
        approx_entry = self.data.Close[-1]
        kwargs = {"size": 0.01}
        if self.tp_mult > 0:
            kwargs["tp"] = approx_entry * (1.0 + self.tp_mult * self.threshold_pct)
        if self.sl_mult > 0:
            kwargs["sl"] = approx_entry * (1.0 - self.sl_mult * self.threshold_pct)
        self.buy(**kwargs)
