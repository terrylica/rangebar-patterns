"""Tests for barrier_sim.py — pure-Python barrier simulator.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/27

Validates Gen720 2-segment SL semantics, AP-12 (SL wins ties),
AP-13 (gap-down execution), and barrier_id formatting.
"""

import numpy as np
import pytest

from rangebar_patterns.barrier_sim import BarrierConfig, simulate_barriers

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

ENTRY = 100.0
BAR_RANGE = 0.01  # 1%


def _default_cfg(**overrides) -> BarrierConfig:
    """Build a BarrierConfig with sensible defaults, overridable per-test."""
    defaults = dict(
        tp_mult=2.5,
        sl_mult=5.0,
        sl_tight_mult=1.0,
        phase1_bars=5,
        max_bars=10,
        bar_range=BAR_RANGE,
    )
    defaults.update(overrides)
    return BarrierConfig(**defaults)


def _flat_bars(n: int, price: float = ENTRY) -> tuple:
    """Generate n flat bars at a constant price."""
    opens = np.full(n, price)
    highs = np.full(n, price)
    lows = np.full(n, price)
    closes = np.full(n, price)
    return opens, highs, lows, closes


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTPHit:
    """Synthetic upward move triggers TP exit."""

    def test_tp_hit(self):
        cfg = _default_cfg(tp_mult=2.5, sl_mult=5.0, max_bars=10)
        tp_price = ENTRY * (1.0 + 2.5 * BAR_RANGE)  # 102.5

        # 20 bars: signal at bar 0, entry at bar 1 (open=100).
        # Bars 2..11 are the forward window.
        # Bar 4 high reaches TP.
        n = 20
        opens, highs, lows, closes = _flat_bars(n)
        # Gradual climb — bar 4 (fwd=3) breaches TP
        highs[2] = 100.5
        highs[3] = 101.5
        highs[4] = tp_price + 0.1  # TP breached on forward bar 3

        signals = np.array([0])
        df = simulate_barriers(opens, highs, lows, closes, signals, [cfg])

        assert len(df) == 1
        row = df.row(0, named=True)
        assert row["exit_type"] == "TP"
        assert row["exit_bar"] == 3
        assert row["return_pct"] == pytest.approx(
            (tp_price - ENTRY) / ENTRY, abs=1e-10
        )


class TestSLHit:
    """Synthetic downward move triggers SL exit."""

    def test_sl_hit(self):
        cfg = _default_cfg(tp_mult=2.5, sl_mult=5.0, max_bars=10)
        wide_sl = ENTRY * (1.0 - 5.0 * BAR_RANGE)  # 95.0

        n = 20
        opens, highs, lows, closes = _flat_bars(n)
        # Bar 3 (fwd=2) low drops below wide SL
        lows[3] = wide_sl - 0.5

        signals = np.array([0])
        df = simulate_barriers(opens, highs, lows, closes, signals, [cfg])

        assert len(df) == 1
        row = df.row(0, named=True)
        assert row["exit_type"] == "SL"
        assert row["exit_bar"] == 2
        # open is flat at 100, SL at 95 — exit at min(open=100, sl=95) = 95
        assert row["return_pct"] == pytest.approx(
            (wide_sl - ENTRY) / ENTRY, abs=1e-10
        )


class TestSLWinsSameBar:
    """AP-12: When both TP and SL are breached on the same bar, SL wins."""

    def test_sl_wins_same_bar(self):
        cfg = _default_cfg(tp_mult=2.5, sl_mult=5.0, max_bars=10)
        tp_price = ENTRY * (1.0 + 2.5 * BAR_RANGE)
        wide_sl = ENTRY * (1.0 - 5.0 * BAR_RANGE)

        n = 20
        opens, highs, lows, closes = _flat_bars(n)
        # Bar 2 (fwd=1): both TP and SL breached
        highs[2] = tp_price + 1.0
        lows[2] = wide_sl - 1.0

        signals = np.array([0])
        df = simulate_barriers(opens, highs, lows, closes, signals, [cfg])

        assert len(df) == 1
        row = df.row(0, named=True)
        assert row["exit_type"] == "SL"
        assert row["exit_bar"] == 1


class TestTimeExit:
    """Flat OHLCV leads to TIME exit after max_bars."""

    def test_time_exit(self):
        cfg = _default_cfg(tp_mult=2.5, sl_mult=5.0, max_bars=10)

        n = 20
        opens, highs, lows, closes = _flat_bars(n)
        # Set close of last forward bar (bar 11) to a specific value
        closes[11] = 100.3

        signals = np.array([0])
        df = simulate_barriers(opens, highs, lows, closes, signals, [cfg])

        assert len(df) == 1
        row = df.row(0, named=True)
        assert row["exit_type"] == "TIME"
        assert row["exit_bar"] == 10
        assert row["return_pct"] == pytest.approx(
            (100.3 - ENTRY) / ENTRY, abs=1e-10
        )


class TestTwoSegmentSL:
    """Phase 1 wide SL survives, then phase 2 tight SL triggers."""

    def test_two_segment_sl(self):
        # Wide SL at 5x = 95.0, tight SL at 1x = 99.0
        cfg = _default_cfg(
            tp_mult=2.5, sl_mult=5.0, sl_tight_mult=1.0,
            phase1_bars=3, max_bars=10,
        )
        tight_sl = ENTRY * (1.0 - 1.0 * BAR_RANGE)  # 99.0

        n = 20
        opens, highs, lows, closes = _flat_bars(n)

        # Phase 1 bars (fwd 1-3, bars 2-4): dip below tight SL but above wide SL.
        # This should NOT trigger SL because we're in phase 1 (wide SL active).
        lows[2] = 98.5   # fwd=1: below tight (99) but above wide (95) -> no SL
        lows[3] = 98.0   # fwd=2: same
        lows[4] = 97.5   # fwd=3: same

        # Phase 2 bar (fwd=4, bar 5): dip below tight SL -> triggers
        lows[5] = tight_sl - 0.5  # fwd=4: below tight SL, now in phase 2

        signals = np.array([0])
        df = simulate_barriers(opens, highs, lows, closes, signals, [cfg])

        assert len(df) == 1
        row = df.row(0, named=True)
        assert row["exit_type"] == "SL"
        assert row["exit_bar"] == 4  # First bar in phase 2
        # Exit at min(open=100, tight_sl=99) = 99
        assert row["return_pct"] == pytest.approx(
            (tight_sl - ENTRY) / ENTRY, abs=1e-10
        )


class TestGapDownExecution:
    """AP-13: Open below SL means exit_price = open, not sl_price."""

    def test_gap_down_execution(self):
        cfg = _default_cfg(tp_mult=2.5, sl_mult=5.0, max_bars=10)

        n = 20
        opens, highs, lows, closes = _flat_bars(n)
        # Bar 2 (fwd=1): gap-down open at 93.0 — below SL of 95.0
        opens[2] = 93.0
        highs[2] = 93.5
        lows[2] = 92.0
        closes[2] = 92.5

        signals = np.array([0])
        df = simulate_barriers(opens, highs, lows, closes, signals, [cfg])

        assert len(df) == 1
        row = df.row(0, named=True)
        assert row["exit_type"] == "SL"
        assert row["exit_bar"] == 1
        # AP-13: exit at min(open=93, sl=95) = 93 (worse than SL)
        assert row["return_pct"] == pytest.approx(
            (93.0 - ENTRY) / ENTRY, abs=1e-10
        )


class TestBarrierIdFormat:
    """Verify barrier_id property produces Gen720 format strings."""

    def test_basic_format(self):
        cfg = BarrierConfig(
            tp_mult=2.5, sl_mult=5.0, sl_tight_mult=1.0,
            phase1_bars=5, max_bars=100, bar_range=0.0075,
        )
        assert cfg.barrier_id == "p5_slt010_mb100"

    def test_fractional_tight_mult(self):
        cfg = BarrierConfig(
            tp_mult=2.5, sl_mult=5.0, sl_tight_mult=7.5,
            phase1_bars=3, max_bars=50, bar_range=0.01,
        )
        assert cfg.barrier_id == "p3_slt075_mb50"

    def test_zero_tight_mult(self):
        cfg = BarrierConfig(
            tp_mult=2.5, sl_mult=5.0, sl_tight_mult=0.0,
            phase1_bars=5, max_bars=200, bar_range=0.01,
        )
        assert cfg.barrier_id == "p5_slt000_mb200"

    def test_small_tight_mult(self):
        cfg = BarrierConfig(
            tp_mult=2.5, sl_mult=5.0, sl_tight_mult=0.5,
            phase1_bars=7, max_bars=75, bar_range=0.01,
        )
        assert cfg.barrier_id == "p7_slt005_mb75"


class TestEdgeCases:
    """Edge cases: signal near end of data, multiple signals, empty."""

    def test_signal_at_last_bar_skipped(self):
        """Signal at the last bar cannot enter — no results."""
        cfg = _default_cfg(max_bars=5)
        n = 10
        opens, highs, lows, closes = _flat_bars(n)
        signals = np.array([9])  # last bar
        df = simulate_barriers(opens, highs, lows, closes, signals, [cfg])
        assert len(df) == 0

    def test_incomplete_forward_window_skipped(self):
        """Signal with insufficient forward bars is INCOMPLETE — skipped."""
        cfg = _default_cfg(max_bars=10)
        n = 10  # entry at bar 1, need bars up to 11 — only 10 available
        opens, highs, lows, closes = _flat_bars(n)
        signals = np.array([0])
        df = simulate_barriers(opens, highs, lows, closes, signals, [cfg])
        assert len(df) == 0

    def test_multiple_signals_multiple_configs(self):
        """Two signals x two configs = four result rows."""
        cfg1 = _default_cfg(tp_mult=2.5, sl_mult=5.0, max_bars=5, phase1_bars=2)
        cfg2 = _default_cfg(tp_mult=3.0, sl_mult=5.0, max_bars=5, phase1_bars=2)
        n = 30
        opens, highs, lows, closes = _flat_bars(n)
        signals = np.array([0, 10])
        df = simulate_barriers(opens, highs, lows, closes, signals, [cfg1, cfg2])
        # Both signals have enough room, both configs apply
        assert len(df) == 4
        # signal_idx values should be 0 and 1 (not the raw bar indices)
        assert set(df["signal_idx"].to_list()) == {0, 1}

    def test_empty_signals(self):
        """No signals produces empty DataFrame with correct schema."""
        cfg = _default_cfg()
        n = 20
        opens, highs, lows, closes = _flat_bars(n)
        signals = np.array([], dtype=np.int64)
        df = simulate_barriers(opens, highs, lows, closes, signals, [cfg])
        assert len(df) == 0
        assert df.columns == ["signal_idx", "barrier_id", "return_pct", "exit_type", "exit_bar"]
