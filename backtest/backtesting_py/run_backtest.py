"""Run champion strategy backtest on SOL range bars.

ADR: docs/adr/2026-02-06-repository-creation.md

Usage: uv run -p 3.13 python backtest/backtesting_py/run_backtest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add backtest directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main() -> None:
    from backtesting import Backtest

    from backtest.backtesting_py.champion_strategy import ChampionMeanRevLong
    from backtest.backtesting_py.data_loader import load_range_bars

    print("Loading SOL@250dbps range bars from BigBlack ClickHouse (via SSH tunnel)...")
    df = load_range_bars(symbol="SOLUSDT", threshold=250)
    print(f"Loaded {len(df)} range bars ({df.index[0]} to {df.index[-1]})")

    bt = Backtest(
        df,
        ChampionMeanRevLong,
        cash=10_000,
        commission=0.002,
        exclusive_orders=True,
    )

    stats = bt.run()
    print("\n=== Champion Strategy Results ===")
    print(stats)
    print(f"\nWin Rate: {stats['Win Rate [%]']:.1f}%")
    print(f"Number of Trades: {stats['# Trades']}")


if __name__ == "__main__":
    main()
