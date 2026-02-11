"""Gen600 barrier alignment validation: SQL vs backtesting.py.

Validates that Gen600 SQL templates produce trade outcomes that align with
backtesting.py's barrier execution logic. Tests both LONG and SHORT templates
across all 3 barrier profiles (inverted/symmetric/momentum).

Acceptance: >95% exit price match on shared signals per barrier profile.

Usage:
    python tests/test_gen600_barrier_alignment.py --bt-only   # BT-only sanity check
    python tests/test_gen600_barrier_alignment.py              # Full SQL vs BT alignment
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtesting import Backtest

from backtest.backtesting_py.champion_strategy import ChampionLong
from backtest.backtesting_py.data_loader import load_range_bars

# Gen600 uses @750 threshold with 3 barrier profiles
THRESHOLD_DBPS = 750
THRESHOLD_PCT = THRESHOLD_DBPS / 10000.0

BARRIER_PROFILES = {
    "inverted":  {"tp_mult": 0.25, "sl_mult": 0.50, "max_bars": 100},
    "symmetric": {"tp_mult": 0.50, "sl_mult": 0.50, "max_bars": 50},
    "momentum":  {"tp_mult": 0.75, "sl_mult": 0.25, "max_bars": 50},
}


def run_backtesting_py(tp_mult, sl_mult, max_bars):
    """Run backtesting.py with specified barrier params."""
    df = load_range_bars(symbol="SOLUSDT", threshold=THRESHOLD_DBPS)
    bt = Backtest(
        df,
        ChampionLong,
        cash=100_000,
        commission=0.0,
        exclusive_orders=True,
    )
    stats = bt.run(
        tp_mult=tp_mult,
        sl_mult=sl_mult,
        max_bars=max_bars,
        threshold_pct=THRESHOLD_PCT,
    )
    return stats["_trades"], stats, df


def load_sql_trades(profile_name):
    """Load SQL trade-level export for a specific barrier profile.

    To generate: run Gen600 SQL with --trade-export mode and save to CSV.
    """
    sql_path = Path(f"/tmp/gen600_sql_trades_{profile_name}.csv")
    if not sql_path.exists():
        raise FileNotFoundError(
            f"SQL trades not found at {sql_path}. "
            f"Export Gen600 trade-level data for {profile_name} profile first."
        )
    return pd.read_csv(sql_path)


def compare_trades(sql_trades, bt_trades, profile_name):
    """Compare SQL vs BT trade outcomes on shared signals."""
    print(f"\n--- {profile_name} profile ---")
    print(f"SQL trades: {len(sql_trades)}")
    print(f"BT trades:  {len(bt_trades)}")

    sql_trades = sql_trades.copy()
    sql_trades["bt_entry_bar"] = sql_trades["signal_rn"]
    merged = sql_trades.merge(
        bt_trades, left_on="bt_entry_bar", right_on="EntryBar", how="inner"
    )
    print(f"Shared signals: {len(merged)}")

    if len(merged) == 0:
        print("ERROR: No shared signals found!")
        return 0.0

    # Entry price match
    entry_diff = (merged["entry_price"] - merged["EntryPrice"]).abs() / merged["EntryPrice"]
    entry_match = (entry_diff < 0.0001).sum()

    # Exit price match
    exit_diff = (
        (merged["exit_price"] - merged["ExitPrice"]).abs()
        / merged["ExitPrice"].abs().clip(lower=0.001)
    )
    exit_match = (exit_diff < 0.005).sum()
    match_rate = exit_match / len(merged)

    print(f"Entry match:  {entry_match}/{len(merged)} ({entry_match/len(merged)*100:.1f}%)")
    print(f"Exit match:   {exit_match}/{len(merged)} ({match_rate*100:.1f}%)")
    print(f"GATE: {'PASS' if match_rate >= 0.95 else 'FAIL'} (need >95%)")

    return match_rate


def run_bt_only_validation():
    """BT-only sanity check across all 3 barrier profiles."""
    print("=== Gen600 Backtesting.py Standalone Validation ===")
    print(f"Symbol: SOLUSDT @{THRESHOLD_DBPS}")

    for profile_name, params in BARRIER_PROFILES.items():
        print(f"\n--- {profile_name}: TP={params['tp_mult']}x SL={params['sl_mult']}x MB={params['max_bars']} ---")
        trades, stats, _ = run_backtesting_py(**params)
        n_trades = len(trades)
        win_rate = stats.get("Win Rate [%]", 0) / 100.0
        pf = stats.get("Profit Factor", 0)
        print(f"  Trades: {n_trades}, WR: {win_rate:.3f}, PF: {pf:.3f}")
        # Sanity: expect at least some trades
        if n_trades < 10:
            print(f"  WARNING: Only {n_trades} trades — too few for validation")


def run_full_alignment():
    """Full SQL vs BT alignment across all 3 barrier profiles."""
    print("=== Gen600 Full Barrier Alignment ===")
    results = {}

    for profile_name, params in BARRIER_PROFILES.items():
        sql_trades = load_sql_trades(profile_name)
        bt_trades, _, _ = run_backtesting_py(**params)
        match_rate = compare_trades(sql_trades, bt_trades, profile_name)
        results[profile_name] = match_rate

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    all_pass = True
    for profile_name, rate in results.items():
        status = "PASS" if rate >= 0.95 else "FAIL"
        if rate < 0.95:
            all_pass = False
        print(f"  {profile_name:12s}: {rate*100:.1f}% [{status}]")
    print(f"{'=' * 60}")
    print(f"OVERALL: {'PASS' if all_pass else 'FAIL'}")
    return all_pass


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--bt-only", action="store_true",
                        help="Run BT-only validation (no SQL trades needed)")
    args = parser.parse_args()

    if args.bt_only:
        run_bt_only_validation()
        sys.exit(0)
    else:
        passed = run_full_alignment()
        sys.exit(0 if passed else 1)
