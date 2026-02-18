"""Pure-Python barrier simulator for programmatic sweep evaluation.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/27

Implements Gen720 2-segment stop-loss semantics:
- Phase 1 (bars 1..phase1_bars): wide SL protects against early noise
- Phase 2 (bars phase1_bars+1..max_bars): tight SL locks in mean-reversion gains

Anti-patterns enforced:
- AP-12: SL wins same-bar ties (conservative — if both TP and SL breach on
  the same bar, SL is taken because we cannot know intra-bar sequencing)
- AP-13: Gap-down SL execution uses min(open, sl_price), not sl_price itself
  (open below SL means the limit order fills at the worse price)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl


@dataclass(frozen=True)
class BarrierConfig:
    """Frozen barrier configuration for a single sweep cell.

    All multipliers are in bar-widths (e.g., tp_mult=2.5 means TP at 2.5x
    the bar range from entry).
    """

    tp_mult: float
    sl_mult: float
    sl_tight_mult: float
    phase1_bars: int
    max_bars: int
    bar_range: float

    @property
    def barrier_id(self) -> str:
        """Gen720 format: p{phase1}_slt{tight*10:03d}_mb{max_bars}."""
        return f"p{self.phase1_bars}_slt{int(self.sl_tight_mult * 10):03d}_mb{self.max_bars}"


def simulate_barriers(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    signal_indices: np.ndarray,
    barrier_configs: list[BarrierConfig],
) -> pl.DataFrame:
    """Simulate barrier exits for every (signal, config) combination.

    Parameters
    ----------
    opens, highs, lows, closes:
        1-D float arrays of bar OHLC data, all same length.
    signal_indices:
        1-D int array of bar indices where signals fire.  Entry is at
        opens[i+1] (next bar open after signal bar).
    barrier_configs:
        List of BarrierConfig to evaluate per signal.

    Returns
    -------
    pl.DataFrame with columns:
        signal_idx  (int)   — position in signal_indices, 0-based
        barrier_id  (str)   — from BarrierConfig.barrier_id
        return_pct  (float) — (exit_price - entry_price) / entry_price
        exit_type   (str)   — "TP", "SL", or "TIME"
        exit_bar    (int)   — forward bar number where exit occurred, 1-based
    """
    n_bars = len(opens)
    result_signal_idx: list[int] = []
    result_barrier_id: list[str] = []
    result_return_pct: list[float] = []
    result_exit_type: list[str] = []
    result_exit_bar: list[int] = []

    for sig_pos, sig_i in enumerate(signal_indices):
        entry_bar = sig_i + 1
        if entry_bar >= n_bars:
            continue

        entry_price = opens[entry_bar]

        for cfg in barrier_configs:
            # Forward bars span entry_bar+1 .. entry_bar+max_bars
            last_fwd = entry_bar + cfg.max_bars
            if last_fwd >= n_bars:
                # Not enough forward data — INCOMPLETE, skip
                continue

            tp_price = entry_price * (1.0 + cfg.tp_mult * cfg.bar_range)
            wide_sl_price = entry_price * (1.0 - cfg.sl_mult * cfg.bar_range)
            tight_sl_price = entry_price * (1.0 - cfg.sl_tight_mult * cfg.bar_range)

            exit_type: str | None = None
            exit_price = 0.0
            exit_bar = 0

            for fwd in range(1, cfg.max_bars + 1):
                bar_idx = entry_bar + fwd
                h = highs[bar_idx]
                lo = lows[bar_idx]
                o = opens[bar_idx]

                sl_price = wide_sl_price if fwd <= cfg.phase1_bars else tight_sl_price

                tp_hit = h >= tp_price
                sl_hit = lo <= sl_price

                if sl_hit:
                    # AP-12: SL wins same-bar ties
                    # AP-13: gap-down execution
                    exit_type = "SL"
                    exit_price = min(o, sl_price)
                    exit_bar = fwd
                    break
                if tp_hit:
                    exit_type = "TP"
                    exit_price = tp_price
                    exit_bar = fwd
                    break

            if exit_type is None:
                # TIME exit — close of the last forward bar
                exit_type = "TIME"
                exit_price = closes[last_fwd]
                exit_bar = cfg.max_bars

            return_pct = (exit_price - entry_price) / entry_price

            result_signal_idx.append(sig_pos)
            result_barrier_id.append(cfg.barrier_id)
            result_return_pct.append(return_pct)
            result_exit_type.append(exit_type)
            result_exit_bar.append(exit_bar)

    return pl.DataFrame({
        "signal_idx": result_signal_idx,
        "barrier_id": result_barrier_id,
        "return_pct": result_return_pct,
        "exit_type": result_exit_type,
        "exit_bar": result_exit_bar,
    })
