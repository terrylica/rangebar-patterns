"""Gen800: Reconstruct top config via backtesting.py with hedging.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/28

Runs the #1 ranked config through backtesting.py with hedging=True to produce:
1. JSONL trade log (every trade with entry/exit times, prices, return, exit type)
2. Interactive HTML equity curve plot (via backtesting.py Bokeh)

The hedging mode allows overlapping positions — each signal opens independently,
matching the SQL barrier evaluation semantics (AP-16). This is critical because
range bar signals can fire while earlier positions are still open.

SQL alignment:
  - AP-15: Signal timing — current bar IS last pattern bar
  - AP-16: hedging=True, exclusive_orders=False for multi-position
  - AP-17: Bar counting — SL tightens at phase1_bars-1, time exit at max_bars-1

Usage:
    uv run -p 3.13 python scripts/gen800_reconstruct.py
    uv run -p 3.13 python scripts/gen800_reconstruct.py \
        --config-id atr32_up85_dn10_ao50__wl1d__bullish_only__p7_slt035_mb10
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from backtesting import Backtest, Strategy

# Ensure project root on path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
bt_path = str(Path(__file__).resolve().parent.parent / "backtest" / "backtesting_py")
if bt_path not in sys.path:
    sys.path.insert(0, bt_path)

from backtest.backtesting_py.data_loader import load_range_bars  # noqa: E402
from backtest.backtesting_py.gen600_strategy import (  # noqa: E402
    PURE_PRICEACTION_PATTERNS,
    WICKLESS_DETECTORS,
    _compute_opposite_wick_pct,
)
from rangebar_patterns.laguerre import LaguerreRegimeConfig, compute_laguerre_regimes  # noqa: E402

RESULTS_DIR = Path("results/eval/gen800")
SYMBOL = "SOLUSDT"
THRESHOLD = 750
BAR_RANGE = THRESHOLD / 100_000.0  # 0.0075


def parse_config_id(config_id: str) -> dict:
    """Parse Gen800 config_id into components.

    Format: atr{N}_up{NN}_dn{NN}_ao{NN}__{pattern}__{gate}__{barrier_id}
    """
    parts = config_id.split("__")
    laguerre_id = parts[0]
    pattern = parts[1]
    gate = parts[2]
    barrier_id = parts[3]

    # Parse laguerre: atr32_up85_dn10_ao50
    import re

    lm = re.match(r"atr(\d+)_up(\d+)_dn(\d+)_ao(\d+)", laguerre_id)
    if not lm:
        raise ValueError(f"Cannot parse laguerre_id: {laguerre_id}")

    # Parse barrier: p7_slt035_mb10
    bm = re.match(r"p(\d+)_slt(\d+)_mb(\d+)", barrier_id)
    if not bm:
        raise ValueError(f"Cannot parse barrier_id: {barrier_id}")

    return {
        "atr_period": int(lm.group(1)),
        "level_up": int(lm.group(2)) / 100.0,
        "level_down": int(lm.group(3)) / 100.0,
        "adaptive_offset": int(lm.group(4)) / 100.0,
        "pattern": pattern,
        "regime_gate": gate,
        "phase1_bars": int(bm.group(1)),
        "sl_tight_mult": int(bm.group(2)) / 10.0,
        "max_bars": int(bm.group(3)),
    }


class Gen800Strategy(Strategy):
    """Gen800: Regime-conditioned pattern strategy with 2-segment SL.

    Extends Gen720 barrier mechanics with Laguerre RSI regime gating.
    Uses hedging=True for overlapping positions (matches SQL semantics).
    """

    # Laguerre regime params (set externally)
    regime_labels: np.ndarray = np.array([])
    regime_gate: str = "bullish_only"

    # Pattern
    pattern: str = "wl1d"

    # Barrier params (2-segment SL from Gen720)
    tp_mult: float = 2.5
    sl_mult: float = 5.0
    sl_tight_mult: float = 3.5
    phase1_bars: int = 7
    max_bars: int = 10
    bar_range: float = BAR_RANGE

    # Warmup
    warmup_bars: int = 42  # max(atr_period, 20) + 10

    def init(self):
        opens = np.array(self.data.Open)
        closes = np.array(self.data.Close)
        highs = np.array(self.data.High)
        lows = np.array(self.data.Low)
        direction = (closes > opens).astype(int)

        # Pattern detection
        if self.pattern in PURE_PRICEACTION_PATTERNS:
            wick_pct = _compute_opposite_wick_pct(opens, highs, lows, closes)
            detector = WICKLESS_DETECTORS.get(self.pattern)
            if detector is None:
                raise ValueError(f"Unknown wickless pattern: {self.pattern}")
            pattern_mask = detector(direction, wick_pct)
        else:
            from backtest.backtesting_py.gen600_strategy import PATTERN_DETECTORS

            detector = PATTERN_DETECTORS.get(self.pattern)
            if detector is None:
                raise ValueError(f"Unknown pattern: {self.pattern}")
            pattern_mask = detector(direction)

        # Regime gate
        regimes = self.regime_labels
        if self.regime_gate == "bullish_only":
            regime_mask = regimes == 2
        elif self.regime_gate == "not_bearish":
            regime_mask = regimes >= 1
        else:  # any_regime
            regime_mask = np.ones(len(regimes), dtype=bool)

        # Combined signal
        is_signal = pattern_mask & regime_mask
        is_signal[: self.warmup_bars] = False
        self._is_signal = is_signal

        # Tracking
        self._trade_entry_bar = {}
        self._known_trades = set()
        self._sl_tightened = set()

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
                actual_entry = trade.entry_price
                if self.tp_mult > 0:
                    trade.tp = actual_entry * (1.0 + self.tp_mult * self.bar_range)
                if self.sl_mult > 0:
                    trade.sl = actual_entry * (1.0 - self.sl_mult * self.bar_range)

        # 2. Two-segment SL + time barrier
        for trade in list(self.trades):
            tid = id(trade)
            entry_bar = self._trade_entry_bar.get(tid, current_bar)
            bars_held = current_bar - entry_bar

            # Phase 2 SL transition (AP-17 aligned)
            if (
                bars_held == self.phase1_bars - 1
                and tid not in self._sl_tightened
                and self.sl_tight_mult != self.sl_mult
            ):
                actual_entry = trade.entry_price
                trade.sl = actual_entry * (
                    1.0 - self.sl_tight_mult * self.bar_range
                )
                self._sl_tightened.add(tid)

            # Time barrier (AP-17 aligned)
            if self.max_bars > 0 and bars_held >= self.max_bars - 1:
                trade.close()
                self._trade_entry_bar.pop(tid, None)
                self._sl_tightened.discard(tid)

        # 3. New signal entry
        bar_idx = current_bar
        if not self._is_signal[bar_idx]:
            return

        approx_entry = self.data.Close[-1]
        kwargs = {"size": 0.01}
        if self.tp_mult > 0:
            kwargs["tp"] = approx_entry * (1.0 + self.tp_mult * self.bar_range)
        if self.sl_mult > 0:
            kwargs["sl"] = approx_entry * (1.0 - self.sl_mult * self.bar_range)
        self.buy(**kwargs)


def _plot_tall(bt, filename: str, timestamps=None, panel_height: int = 200):
    """Generate backtesting.py plot with equal-height panels, gray HLC bars.

    Customizations over default backtesting.py plot:
    1. All sub-figures set to equal height (panel_height px each)
    2. OHLC candlestick bodies hidden, replaced with gray HLC tick bars
    3. Trade markers keep original red/green coloring
    4. X-axis shows real timestamps at regular bar intervals
    """
    import backtesting._plotting as _bp
    from bokeh.models import Segment, VBar

    GRAY = "#999999"

    # Force ALL figures to the same height by patching _figure
    orig_figure = _bp._figure

    def equal_height_figure(*args, **kwargs):
        kwargs["height"] = panel_height
        return orig_figure(*args, **kwargs)

    orig_indicator_height = _bp._INDICATOR_HEIGHT
    _bp._INDICATOR_HEIGHT = panel_height
    _bp._figure = equal_height_figure

    try:
        fig = bt.plot(
            filename=filename,
            open_browser=False,
            plot_drawdown=True,
            plot_volume=True,
        )
    finally:
        _bp._INDICATOR_HEIGHT = orig_indicator_height
        _bp._figure = orig_figure

    if fig is None:
        return

    # Collect all sub-figures from the gridplot
    children = []
    if hasattr(fig, "children"):
        for row in fig.children:
            if hasattr(row, "__iter__"):
                for child in row:
                    if child is not None:
                        children.append(child)
            elif row is not None:
                children.append(row)

    # Find the OHLC figure (the one with VBar renderers = candlesticks)
    fig_ohlc = None
    for child in children:
        for renderer in getattr(child, "renderers", []):
            if isinstance(getattr(renderer, "glyph", None), VBar):
                fig_ohlc = child
                break
        if fig_ohlc:
            break

    if fig_ohlc is None:
        return

    # Replace candlestick vbars with gray HLC tick bars
    source = None
    for renderer in list(fig_ohlc.renderers):
        glyph = getattr(renderer, "glyph", None)
        if isinstance(glyph, VBar):
            source = renderer.data_source
            renderer.visible = False  # Hide candlestick body

    if source is not None:
        tick_w = 0.35
        source.data["open_x0"] = [x - tick_w for x in source.data["index"]]
        source.data["open_x1"] = list(source.data["index"])
        source.data["close_x0"] = list(source.data["index"])
        source.data["close_x1"] = [x + tick_w for x in source.data["index"]]

        # Open tick (left horizontal)
        fig_ohlc.segment(
            x0="open_x0", y0="Open", x1="open_x1", y1="Open",
            source=source, color=GRAY, line_width=1.0,
        )
        # Close tick (right horizontal)
        fig_ohlc.segment(
            x0="close_x0", y0="Close", x1="close_x1", y1="Close",
            source=source, color=GRAY, line_width=1.0,
        )

    # Gray out only the HL vertical segment (first Segment renderer = OHLC HL line)
    # Trade position lines are MultiLine, not Segment, so this is safe
    for renderer in fig_ohlc.renderers:
        glyph = getattr(renderer, "glyph", None)
        if isinstance(glyph, Segment) and hasattr(glyph, "line_color"):
            # Only gray the original HL segment (color="black"), not our new ticks
            if glyph.line_color == "black":
                glyph.line_color = GRAY

    # Add timestamp labels to x-axis if timestamps provided
    if timestamps is not None:
        from bokeh.models import CustomJSTickFormatter, FixedTicker

        n_bars = len(timestamps)
        # ~20 evenly spaced ticks across the full range
        step = max(1, n_bars // 20)
        tick_positions = list(range(0, n_bars, step))

        # Build JS lookup: bar_index → "YYYY-MM-DD HH:MM"
        ts_map = {}
        for pos in tick_positions:
            if pos < n_bars:
                ts_map[pos] = str(timestamps[pos])[:16]  # "YYYY-MM-DD HH:MM"

        js_map = "var m = {" + ",".join(f"{k}:'{v}'" for k, v in ts_map.items()) + "};"
        js_code = js_map + " return m[tick] || '';"

        formatter = CustomJSTickFormatter(code=js_code)
        ticker = FixedTicker(ticks=tick_positions)

        for child in children:
            if hasattr(child, "xaxis"):
                child.xaxis[0].ticker = ticker
                child.xaxis[0].formatter = formatter
                child.xaxis[0].major_label_orientation = 0.7  # ~40 degrees

    # Re-save with modifications
    from bokeh.io import output_file as bokeh_output_file
    from bokeh.io import save as bokeh_save

    bokeh_output_file(filename)
    bokeh_save(fig)


def main():
    parser = argparse.ArgumentParser(description="Gen800 trade reconstruction")
    parser.add_argument(
        "--config-id",
        default="atr32_up85_dn10_ao50__wl1d__bullish_only__p7_slt035_mb10",
        help="Config ID to reconstruct",
    )
    args = parser.parse_args()

    cfg = parse_config_id(args.config_id)
    print(f"Reconstructing: {args.config_id}")
    print(
        f"  Laguerre: atr={cfg['atr_period']} up={cfg['level_up']}"
        f" dn={cfg['level_down']} ao={cfg['adaptive_offset']}"
    )
    print(f"  Pattern: {cfg['pattern']}, Gate: {cfg['regime_gate']}")
    print(f"  Barrier: phase1={cfg['phase1_bars']} sl_tight={cfg['sl_tight_mult']} max_bars={cfg['max_bars']}")

    # 1. Load data
    print(f"\nLoading {SYMBOL} @{THRESHOLD}dbps...")
    df = load_range_bars(symbol=SYMBOL, threshold=THRESHOLD)
    print(f"  {len(df)} bars ({df.index[0]} to {df.index[-1]})")

    # 2. Compute Laguerre regimes (needs DatetimeIndex)
    print("Computing Laguerre regimes...")
    laguerre_cfg = LaguerreRegimeConfig(
        atr_period=cfg["atr_period"],
        smoothing_period=5,
        level_up=cfg["level_up"],
        level_down=cfg["level_down"],
        adaptive_offset=cfg["adaptive_offset"],
    )
    _rsi, regimes = compute_laguerre_regimes(df, laguerre_cfg)
    regime_counts = {
        "bearish": int(np.sum(regimes == 0)),
        "neutral": int(np.sum(regimes == 1)),
        "bullish": int(np.sum(regimes == 2)),
    }
    print(f"  Regimes: {regime_counts}")

    # 3. Convert to sequential integer index for range bar plotting.
    # backtesting.py with DatetimeIndex resamples bars into temporal candles
    # (e.g. 8h), destroying range bar structure. With integer index, each
    # range bar gets equal visual width regardless of formation time.
    timestamps = df.index.copy()  # Preserve for JSONL output
    df = df.reset_index(drop=True)  # RangeIndex: 0, 1, 2, ...

    # 4. Set strategy params and run backtest
    Gen800Strategy.regime_labels = regimes
    Gen800Strategy.regime_gate = cfg["regime_gate"]
    Gen800Strategy.pattern = cfg["pattern"]
    Gen800Strategy.tp_mult = 2.5  # Fixed from Gen720
    Gen800Strategy.sl_mult = 5.0  # Fixed from Gen720
    Gen800Strategy.sl_tight_mult = cfg["sl_tight_mult"]
    Gen800Strategy.phase1_bars = cfg["phase1_bars"]
    Gen800Strategy.max_bars = cfg["max_bars"]
    Gen800Strategy.bar_range = BAR_RANGE
    Gen800Strategy.warmup_bars = max(cfg["atr_period"], 20) + 10

    print("\nRunning backtest (hedging=True)...")
    bt = Backtest(
        df,
        Gen800Strategy,
        cash=100_000,
        commission=0,
        hedging=True,
        exclusive_orders=False,
    )
    stats = bt.run()

    # 4. Extract trades
    trades_df = stats._trades.sort_values("EntryTime").reset_index(drop=True)
    n_trades = len(trades_df)
    print("\n=== Results (hedging mode) ===")
    print(f"  Trades: {n_trades}")
    print(f"  Win Rate: {stats['Win Rate [%]']:.1f}%")
    print(f"  Return: {stats['Return [%]']:.2f}%")
    print(f"  Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")

    # 5. Write JSONL trade log
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_id = args.config_id.replace("__", "_")
    jsonl_path = RESULTS_DIR / f"trades_{safe_id}.jsonl"

    returns = []
    with open(jsonl_path, "w") as f:
        for i, trade in trades_df.iterrows():
            ret_pct = float(trade["ReturnPct"])
            returns.append(ret_pct)
            entry_bar = int(trade["EntryBar"])
            exit_bar = int(trade["ExitBar"])
            # Map bar indices back to real timestamps
            entry_ts = str(timestamps[entry_bar]) if entry_bar < len(timestamps) else "N/A"
            exit_ts = str(timestamps[exit_bar]) if exit_bar < len(timestamps) else "N/A"
            row = {
                "trade_n": int(i) + 1,
                "entry_time": entry_ts,
                "exit_time": exit_ts,
                "entry_price": float(trade["EntryPrice"]),
                "exit_price": float(trade["ExitPrice"]),
                "return_pct": round(ret_pct, 6),
                "size": float(trade["Size"]),
                "entry_bar": entry_bar,
                "exit_bar": exit_bar,
                "duration_bars": exit_bar - entry_bar,
            }
            f.write(json.dumps(row) + "\n")

    print(f"\n  Trade log: {jsonl_path} ({n_trades} trades)")

    # 6. Compute stagnation metrics on the hedged equity curve
    returns_arr = np.array(returns)
    cum = np.cumsum(returns_arr)
    running_max = np.maximum.accumulate(cum)
    drawdowns = running_max - cum
    underwater = drawdowns > 1e-12
    uw_ratio = float(np.mean(underwater))

    if np.any(underwater):
        changes = np.diff(underwater.astype(int), prepend=0, append=0)
        starts = np.where(changes == 1)[0]
        ends = np.where(changes == -1)[0]
        durations = ends - starts
        max_uw = int(np.max(durations))

        # Timestamp of worst stagnation (map bar indices back to timestamps)
        longest_idx = np.argmax(durations)
        stag_start_trade = starts[longest_idx]
        stag_end_trade = ends[longest_idx] - 1
        stag_start_bar = int(trades_df.iloc[stag_start_trade]["EntryBar"])
        stag_end_bar = int(trades_df.iloc[stag_end_trade]["ExitBar"])
        stag_start_time = str(timestamps[stag_start_bar]) if stag_start_bar < len(timestamps) else "N/A"
        stag_end_time = str(timestamps[stag_end_bar]) if stag_end_bar < len(timestamps) else "N/A"
    else:
        max_uw = 0
        stag_start_time = "N/A"
        stag_end_time = "N/A"

    print("\n=== Stagnation (hedged equity) ===")
    print(f"  Underwater ratio: {uw_ratio:.3f}")
    print(f"  Max underwater trades: {max_uw}")
    print(f"  Worst stagnation: {stag_start_time} → {stag_end_time}")

    # 7. Write summary JSON
    summary = {
        "config_id": args.config_id,
        "symbol": SYMBOL,
        "threshold": THRESHOLD,
        "n_bars": len(df),
        "n_trades": n_trades,
        "hedging": True,
        "win_rate": round(float(stats["Win Rate [%]"]) / 100, 4),
        "total_return_pct": round(float(stats["Return [%]"]), 4),
        "max_drawdown_pct": round(float(stats["Max. Drawdown [%]"]), 4),
        "profit_factor": round(float(stats.get("Profit Factor", 0)), 4),
        "underwater_ratio": round(uw_ratio, 4),
        "max_underwater_trades": max_uw,
        "worst_stagnation_start": stag_start_time,
        "worst_stagnation_end": stag_end_time,
        "regime_distribution": regime_counts,
        "laguerre_config": {
            "atr_period": cfg["atr_period"],
            "level_up": cfg["level_up"],
            "level_down": cfg["level_down"],
            "adaptive_offset": cfg["adaptive_offset"],
        },
        "barrier_config": {
            "tp_mult": 2.5,
            "sl_mult": 5.0,
            "sl_tight_mult": cfg["sl_tight_mult"],
            "phase1_bars": cfg["phase1_bars"],
            "max_bars": cfg["max_bars"],
        },
    }
    summary_path = RESULTS_DIR / f"summary_{safe_id}.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Summary: {summary_path}")

    # 8. Generate HTML plot with tall canvas
    plot_path = RESULTS_DIR / f"equity_{safe_id}.html"
    _plot_tall(bt, str(plot_path), timestamps=timestamps)
    print(f"  Equity plot: {plot_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
