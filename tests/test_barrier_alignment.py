"""Atomic validation: Gen200 SQL vs backtesting.py barrier outcomes.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/6

Compares individual trade outcomes between:
- Gen200 SQL (ClickHouse): signal timestamp, entry price, exit type, exit price, bars held
- backtesting.py: same strategy params on same data

Acceptance: >95% match on shared signals.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtesting import Backtest

from backtest.backtesting_py.champion_strategy import ChampionMeanRevLong
from backtest.backtesting_py.data_loader import load_range_bars

# Fixed params for atomic validation
TP_MULT = 1.0
SL_MULT = 0.5
MAX_BARS = 10
THRESHOLD_PCT = 0.05  # @500dbps
THRESHOLD_DBPS = 500


def run_backtesting_py():
    """Run backtesting.py with barrier params and return trade log."""
    print("Loading @500dbps data...")
    df = load_range_bars(symbol="SOLUSDT", threshold=THRESHOLD_DBPS)
    print(f"  {len(df)} bars loaded")

    bt = Backtest(
        df,
        ChampionMeanRevLong,
        cash=100_000,
        commission=0.0,  # No commission for alignment test
        exclusive_orders=True,
    )
    stats = bt.run(
        tp_mult=TP_MULT,
        sl_mult=SL_MULT,
        max_bars=MAX_BARS,
        threshold_pct=THRESHOLD_PCT,
    )

    trades = stats["_trades"]
    print(f"  {len(trades)} trades from backtesting.py")
    return trades, df


def load_sql_trades():
    """Load SQL trade log from CSV export."""
    sql_path = Path("/tmp/gen200_sql_trades.csv")
    if not sql_path.exists():
        raise FileNotFoundError(
            f"SQL trades not found at {sql_path}. Run Gen200 SQL export first."
        )
    df = pd.read_csv(sql_path)
    print(f"  {len(df)} trades from SQL")
    return df


def compare_trades(sql_trades, bt_trades, bar_df):
    """Compare SQL vs backtesting.py trade outcomes on shared signals.

    Matching strategy: join on entry bar index.
    SQL signal_rn (1-indexed row number) maps to BT EntryBar (0-indexed) via:
      BT EntryBar = SQL signal_rn  (fill at bar signal_rn, which is 0-indexed = 1-indexed row)

    Known divergence: SQL uses expanding p95, BT uses rolling p95 (1000 bars).
    This produces different signal sets (~50 common out of ~1800 each).
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
    print("ATOMIC VALIDATION RESULTS")
    print(sep)
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


if __name__ == "__main__":
    sql_trades = load_sql_trades()
    bt_trades, bar_df = run_backtesting_py()
    match_rate = compare_trades(sql_trades, bt_trades, bar_df)
    sys.exit(0 if match_rate >= 0.95 else 1)
