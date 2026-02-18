"""Gen610: Multi-position backtesting.py validation of top 10 cross-asset configs.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/14

Validates the top 10 cross-asset survivor configs (from cross_asset.sh) using
backtesting.py with hedging=True, exclusive_orders=False (AP-16 compliant).

Uses the Gen510-optimal inverted barrier: TP=0.25x, SL=0.50x, max_bars=100.

Output: NDJSON to /tmp/gen610_backtest_validation.jsonl

Usage:
    uv run --python 3.13 python scripts/gen610_backtest_validation.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Top 10 cross-asset survivor configs from cross_asset.sh
# Format: (pattern, f1_name, f1_dir, f1_q, f2_name, f2_dir, f2_q)
TOP_10_CONFIGS = [
    ("2down", "aggression_ratio", "lt", 0.50, "intra_kyle_lambda", "gt", 0.50),
    ("2down", "duration_us", "lt", 0.50, "lookback_duration_us", "gt", 0.50),
    ("2down", "turnover_imbalance", "lt", 0.50, "lookback_duration_us", "gt", 0.50),
    ("2down", "ofi", "lt", 0.50, "lookback_duration_us", "gt", 0.50),
    ("2down", "aggression_ratio", "lt", 0.50, "intra_max_drawdown", "gt", 0.50),
    ("2down", "turnover_imbalance", "lt", 0.50, "intra_max_drawdown", "gt", 0.50),
    ("2down", "ofi", "lt", 0.50, "intra_max_drawdown", "gt", 0.50),
    ("2down", "turnover_imbalance", "lt", 0.50, "intra_garman_klass_vol", "gt", 0.50),
    ("2down", "ofi", "lt", 0.50, "intra_garman_klass_vol", "gt", 0.50),
    ("2down", "aggression_ratio", "lt", 0.50, "lookback_duration_us", "gt", 0.50),
]

# Asset/threshold combos to validate
ASSETS = [
    ("SOLUSDT", 750),
    ("SOLUSDT", 1000),
    ("BTCUSDT", 750),
    ("BTCUSDT", 1000),
    ("ETHUSDT", 750),
]

# Barrier: Gen510-optimal inverted
TP_MULT = 0.25
SL_MULT = 0.50
MAX_BARS = 100

LOG_FILE = Path("/tmp/gen610_backtest_validation.jsonl")


def _config_id(pattern, f1_name, f1_dir, f1_q, f2_name, f2_dir, f2_q):
    q1_str = f"p{int(f1_q * 100)}"
    q2_str = f"p{int(f2_q * 100)}"
    return f"{pattern}__{f1_name}_{f1_dir}_{q1_str}__{f2_name}_{f2_dir}_{q2_str}"


def _bar_range(threshold_dbps: int) -> float:
    return threshold_dbps / 100_000.0


def _extra_columns(f1_name: str, f2_name: str) -> list[str]:
    """Get the extra ClickHouse columns needed for the two features."""
    base_cols = {"trade_intensity", "kyle_lambda_proxy", "duration_us"}
    needed = set()
    for name in [f1_name, f2_name]:
        if name not in base_cols and name not in ("Open", "High", "Low", "Close", "Volume"):
            needed.add(name)
    return sorted(needed)


def run_single(
    pattern, f1_name, f1_dir, f1_q, f2_name, f2_dir, f2_q,
    symbol, threshold,
):
    """Run a single config on a single asset. Returns result dict."""
    from backtesting import Backtest

    from backtest.backtesting_py.data_loader import load_range_bars
    from backtest.backtesting_py.gen600_strategy import Gen600Strategy

    config_id = _config_id(pattern, f1_name, f1_dir, f1_q, f2_name, f2_dir, f2_q)
    bar_range = _bar_range(threshold)

    extras = _extra_columns(f1_name, f2_name)

    start_time = time.time()
    try:
        df = load_range_bars(
            symbol=symbol,
            threshold=threshold,
            end="2026-02-05",
            extra_columns=extras if extras else None,
        )
    except (ConnectionError, OSError, ValueError) as e:
        return {
            "config_id": config_id,
            "symbol": symbol,
            "threshold_dbps": threshold,
            "error": True,
            "error_message": f"Data load failed: {e}",
        }

    if len(df) < 2000:
        return {
            "config_id": config_id,
            "symbol": symbol,
            "threshold_dbps": threshold,
            "error": True,
            "error_message": f"Insufficient data: {len(df)} bars",
        }

    # Configure strategy
    Gen600Strategy.pattern = pattern
    Gen600Strategy.feature1_name = f1_name
    Gen600Strategy.feature1_direction = f1_dir
    Gen600Strategy.feature1_quantile = f1_q
    Gen600Strategy.feature2_name = f2_name
    Gen600Strategy.feature2_direction = f2_dir
    Gen600Strategy.feature2_quantile = f2_q
    Gen600Strategy.tp_mult = TP_MULT
    Gen600Strategy.sl_mult = SL_MULT
    Gen600Strategy.max_bars = MAX_BARS
    Gen600Strategy.bar_range = bar_range

    try:
        # Cash must be large enough for size=0.01 (1% equity) to cover 1 unit
        # BTC ~$100K needs cash >> $100K. $10M works for all assets.
        bt = Backtest(
            df,
            Gen600Strategy,
            cash=10_000_000,
            commission=0,
            hedging=True,
            exclusive_orders=False,
        )
        stats = bt.run()
    except (ValueError, TypeError, KeyError, IndexError, RuntimeError) as e:
        return {
            "config_id": config_id,
            "symbol": symbol,
            "threshold_dbps": threshold,
            "error": True,
            "error_message": f"Backtest failed: {e}",
        }

    duration_s = time.time() - start_time
    n_trades = stats["# Trades"]

    # Compute Kelly from trade returns
    trades = stats._trades
    if len(trades) > 0:
        returns = trades["ReturnPct"].values / 100.0
        wins = returns[returns > 0]
        losses = returns[returns <= 0]
        win_rate = len(wins) / len(returns) if len(returns) > 0 else 0
        avg_win = float(wins.mean()) if len(wins) > 0 else 0
        avg_loss = float(abs(losses.mean())) if len(losses) > 0 else 0
        kelly = win_rate - (1 - win_rate) / (avg_win / avg_loss) if avg_loss > 0 and avg_win > 0 else 0
        profit_factor = float(wins.sum() / abs(losses.sum())) if len(losses) > 0 and losses.sum() != 0 else float("inf")
        total_return = float(returns.sum())
    else:
        win_rate = 0
        avg_win = 0
        avg_loss = 0
        kelly = 0
        profit_factor = 0
        total_return = 0

    return {
        "config_id": config_id,
        "pattern": pattern,
        "feature1": f"{f1_name}_{f1_dir}_p{int(f1_q*100)}",
        "feature2": f"{f2_name}_{f2_dir}_p{int(f2_q*100)}",
        "symbol": symbol,
        "threshold_dbps": threshold,
        "barrier": {"tp_mult": TP_MULT, "sl_mult": SL_MULT, "max_bars": MAX_BARS},
        "error": False,
        "results": {
            "n_trades": int(n_trades),
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4) if profit_factor != float("inf") else None,
            "kelly_fraction": round(kelly, 4),
            "avg_win": round(avg_win, 6),
            "avg_loss": round(avg_loss, 6),
            "total_return": round(total_return, 6),
            "max_drawdown_pct": round(float(stats.get("Max. Drawdown [%]", 0)), 2),
            "equity_final": round(float(stats.get("Equity Final [$]", 0)), 2),
        },
        "timing": {"duration_s": round(duration_s, 1)},
    }


def main():
    print("=== Gen610: Backtesting.py Cross-Asset Validation ===")
    print(f"Configs: {len(TOP_10_CONFIGS)}")
    print(f"Assets: {len(ASSETS)}")
    print(f"Barrier: TP={TP_MULT}x SL={SL_MULT}x max_bars={MAX_BARS}")
    print(f"Total runs: {len(TOP_10_CONFIGS) * len(ASSETS)}")
    print()

    results = []
    with open(LOG_FILE, "w") as f:
        for i, config in enumerate(TOP_10_CONFIGS):
            pattern, f1_name, f1_dir, f1_q, f2_name, f2_dir, f2_q = config
            cid = _config_id(pattern, f1_name, f1_dir, f1_q, f2_name, f2_dir, f2_q)
            print(f"[{i+1}/{len(TOP_10_CONFIGS)}] {cid}")

            for symbol, threshold in ASSETS:
                print(f"  {symbol}@{threshold}: ", end="", flush=True)
                result = run_single(
                    pattern, f1_name, f1_dir, f1_q, f2_name, f2_dir, f2_q,
                    symbol, threshold,
                )
                results.append(result)
                f.write(json.dumps(result) + "\n")
                f.flush()

                if result.get("error"):
                    print(f"ERROR - {result.get('error_message', '')}")
                else:
                    r = result["results"]
                    print(f"{r['n_trades']} trades, Kelly={r['kelly_fraction']:+.4f}, "
                          f"PF={r['profit_factor']}, WR={r['win_rate']:.1%}")

            print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    valid = [r for r in results if not r.get("error")]
    errors = [r for r in results if r.get("error")]
    print(f"Valid: {len(valid)}, Errors: {len(errors)}")

    if not valid:
        print("No valid results.")
        return

    # Per-config cross-asset summary
    print(f"\n{'Config':<55s} {'N+':<4s} {'N':<4s} {'Avg Kelly':<10s}")
    print("-" * 75)

    from collections import defaultdict
    config_results = defaultdict(list)
    for r in valid:
        config_results[r["config_id"]].append(r)

    for cid in sorted(config_results):
        entries = config_results[cid]
        kellys = [e["results"]["kelly_fraction"] for e in entries]
        n_pos = sum(1 for k in kellys if k > 0)
        avg_k = sum(kellys) / len(kellys)
        print(f"{cid:<55s} {n_pos:<4d} {len(entries):<4d} {avg_k:+.4f}")

    # Gate check
    print("\n" + "=" * 80)
    print("GATE #124: >=7/10 configs maintain positive Kelly across >=3 assets")
    passing = 0
    for _cid, entries in config_results.items():
        kellys = [e["results"]["kelly_fraction"] for e in entries]
        n_pos = sum(1 for k in kellys if k > 0)
        if n_pos >= 3:
            passing += 1

    if passing >= 7:
        print(f"PASS: {passing}/10 configs positive on 3+ assets")
    else:
        print(f"FAIL: Only {passing}/10 configs positive on 3+ assets (need 7)")

    print(f"\nLog: {LOG_FILE}")


if __name__ == "__main__":
    main()
