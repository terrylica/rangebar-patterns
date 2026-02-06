"""Champion pattern: 2DOWN + ti>p95_expanding + kyle>0 -> LONG.

ADR: docs/adr/2026-02-06-repository-creation.md

Long-only. No shorts (they lose on SOL).
Hold for 1 bar, then exit.

Reference: sql/gen111_true_nolookahead.sql
"""

import numpy as np
from backtesting import Strategy


class ChampionMeanRevLong(Strategy):
    """Champion mean-reversion long strategy on range bars.

    Entry: 2 consecutive DOWN bars AND trade_intensity > expanding p95
           AND kyle_lambda_proxy > 0
    Exit: After 1 bar (unconditional)
    Direction: LONG only (shorts lose on SOL)
    """

    def init(self):
        # Pre-compute expanding p95 of trade_intensity
        ti = self.data.trade_intensity
        self.ti_p95 = self.I(
            lambda x: np.array([
                np.percentile(x[: i + 1], 95) if i >= 1 else x[0]
                for i in range(len(x))
            ]),
            ti,
        )

    def next(self):
        # Need at least 3 bars for 2-bar lookback
        if len(self.data) < 3:
            return

        # 2 consecutive DOWN bars
        prev_down = self.data.Close[-2] < self.data.Open[-2]
        curr_down = self.data.Close[-1] < self.data.Open[-1]
        two_down = prev_down and curr_down

        # trade_intensity > expanding p95
        ti_high = self.data.trade_intensity[-1] > self.ti_p95[-1]

        # kyle_lambda > 0
        kyle_pos = self.data.kyle_lambda_proxy[-1] > 0

        # Signal: LONG only
        if two_down and ti_high and kyle_pos and not self.position:
            self.buy()
        elif self.position:
            self.position.close()  # Exit after 1 bar
