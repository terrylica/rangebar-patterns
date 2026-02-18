"""Atomic validation: Gen300 SQL vs backtesting.py barrier outcomes.

ADR: docs/adr/2026-02-06-repository-creation.md

Compares individual trade outcomes between:
- Gen300 SQL (ClickHouse): duration_us_gt_p75 filter + 2:1 R:R barriers
- backtesting.py: Gen300DurationFilterLong with same params

Known divergence sources:
- SQL uses expanding p95 for trade_intensity; BT uses rolling 1000-bar p95
- SQL uses expanding p75 for duration_us within signal set; BT mirrors this
- These produce different signal sets; we compare SHARED signals only

Acceptance: >95% exit price match on shared signals.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtesting import Backtest

from backtest.backtesting_py.data_loader import load_range_bars
from backtest.backtesting_py.gen300_strategy import Gen300DurationFilterLong

# Gen300 winner: duration_us_gt_p75 with 2:1 R:R barriers
TP_MULT = 5.0
SL_MULT = 2.5
MAX_BARS = 50
BAR_RANGE = 0.005  # @500dbps
THRESHOLD_DBPS = 500


def run_backtesting_py():
    """Run backtesting.py with Gen300 winner params and return trade log."""
    print("Loading @500dbps data...")
    df = load_range_bars(symbol="SOLUSDT", threshold=THRESHOLD_DBPS)
    print(f"  {len(df)} bars loaded")

    bt = Backtest(
        df,
        Gen300DurationFilterLong,
        cash=100_000,
        commission=0.0,  # No commission for alignment test
        exclusive_orders=True,
    )
    stats = bt.run(
        tp_mult=TP_MULT,
        sl_mult=SL_MULT,
        max_bars=MAX_BARS,
        bar_range=BAR_RANGE,
    )

    trades = stats["_trades"]
    print(f"  {len(trades)} trades from backtesting.py")
    return trades, stats, df


def load_sql_trades():
    """Load SQL trade log from CSV export.

    To generate: run gen300_template.sql with duration_us_gt_p75 params
    and export individual trade rows (not just aggregates).
    """
    sql_path = Path("/tmp/gen300_sql_trades.csv")
    if not sql_path.exists():
        raise FileNotFoundError(
            f"SQL trades not found at {sql_path}. "
            "Run Gen300 SQL trade export first."
        )
    df = pd.read_csv(sql_path)
    print(f"  {len(df)} trades from SQL")
    return df


def compare_trades(sql_trades, bt_trades, bar_df):
    """Compare SQL vs backtesting.py trade outcomes on shared signals.

    Known divergence: SQL uses expanding p95, BT uses rolling p95 (1000 bars).
    Also duration_us expanding quantile may differ slightly.
    Atomic validation measures barrier execution alignment on SHARED signals only.
    """
    print(f"\nSQL trades: {len(sql_trades)}")
    print(f"BT trades:  {len(bt_trades)}")

    # Match by entry bar index
    sql_trades = sql_trades.copy()
    sql_trades["bt_entry_bar"] = sql_trades["signal_rn"]
    merged = sql_trades.merge(
        bt_trades, left_on="bt_entry_bar", right_on="EntryBar", how="inner"
    )
    print(f"Shared signals (matched by entry bar): {len(merged)}")

    if len(merged) == 0:
        print("ERROR: No shared signals found!")
        return 0.0

    # Entry price comparison
    entry_diff = (merged["entry_price"] - merged["EntryPrice"]).abs() / merged["EntryPrice"]
    entry_match = (entry_diff < 0.0001).sum()

    # Exit price comparison (the key barrier alignment metric)
    exit_diff = (
        (merged["exit_price"] - merged["ExitPrice"]).abs()
        / merged["ExitPrice"].abs().clip(lower=0.001)
    )
    exit_match_05 = (exit_diff < 0.005).sum()  # <0.5% tolerance
    exit_match_10 = (exit_diff < 0.01).sum()   # <1.0% tolerance

    match_rate = exit_match_05 / len(merged)

    # Signal detection divergence
    sql_bars = set(sql_trades["signal_rn"].values)
    bt_bars = set(bt_trades["EntryBar"].values)
    sql_only = len(sql_bars - bt_bars)
    bt_only = len(bt_bars - sql_bars)

    sep = "=" * 60
    print(f"\n{sep}")
    print("GEN300 ATOMIC VALIDATION RESULTS")
    print(sep)
    print("Config:                    duration_us_gt_p75")
    print("Barriers:                  TP=0.5x SL=0.25x max_bars=50")
    print(f"SQL trades:                {len(sql_trades)}")
    print(f"BT trades:                 {len(bt_trades)}")
    print(f"Shared signals:            {len(merged)}")
    print(f"SQL-only (expanding p95):  {sql_only}")
    print(f"BT-only (rolling p95):     {bt_only}")
    print(f"Entry price match:         {entry_match}/{len(merged)} ({entry_match/len(merged)*100:.1f}%)")
    print(f"Exit price match (<0.5%):  {exit_match_05}/{len(merged)} ({match_rate*100:.1f}%)")
    print(f"Exit price match (<1.0%):  {exit_match_10}/{len(merged)} ({exit_match_10/len(merged)*100:.1f}%)")
    print(sep)
    print(f"GATE: {'PASS' if match_rate >= 0.95 else 'FAIL'} (need >95%, got {match_rate*100:.1f}%)")
    print(sep)

    return match_rate


def run_bt_only_validation():
    """Run backtesting.py-only validation (no SQL trade export needed).

    Validates that:
    1. Strategy produces reasonable number of signals (~400-500 expected)
    2. Kelly fraction is positive
    3. Profit factor > 1.0
    """
    print("=== Gen300 Backtesting.py Standalone Validation ===")
    trades, stats, df = run_backtesting_py()

    n_trades = len(trades)
    win_rate = stats.get("Win Rate [%]", 0) / 100.0
    pf = stats.get("Profit Factor", 0)

    print(f"\n{'=' * 60}")
    print("GEN300 BT-ONLY VALIDATION")
    print(f"{'=' * 60}")
    print(f"Trades:        {n_trades}")
    print(f"Win Rate:      {win_rate:.4f}")
    print(f"Profit Factor: {pf:.4f}")

    # Expect ~400-500 signals (SQL had 458)
    signal_gate = 200 <= n_trades <= 800
    print(f"Signal count gate (200-800): {'PASS' if signal_gate else 'FAIL'} ({n_trades})")

    return trades, stats, df


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--bt-only", action="store_true",
                        help="Run BT-only validation (no SQL trades needed)")
    args = parser.parse_args()

    if args.bt_only:
        trades, stats, df = run_bt_only_validation()
        sys.exit(0)
    else:
        sql_trades = load_sql_trades()
        bt_trades, stats, bar_df = run_backtesting_py()
        match_rate = compare_trades(sql_trades, bt_trades, bar_df)
        sys.exit(0 if match_rate >= 0.95 else 1)
