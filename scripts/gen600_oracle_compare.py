"""Gen600 Oracle: 5-gate trade-by-trade comparison of SQL vs backtesting.py.

ADR: docs/adr/2026-02-06-repository-creation.md
GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/14

Usage:
    # Default (udd config):
    uv run --python 3.13 python scripts/gen600_oracle_compare.py \
        --sql-tsv /tmp/sql_udd_solusdt_1000_trades.tsv \
        --symbol SOLUSDT --threshold 1000

    # Any config (fully parameterized):
    uv run --python 3.13 python scripts/gen600_oracle_compare.py \
        --sql-tsv /tmp/sql_exh_l_solusdt_750_trades.tsv \
        --symbol SOLUSDT --threshold 750 \
        --pattern exh_l \
        --feature1 opposite_wick_pct --dir1 lt --q1 0.50 \
        --feature2 intra_garman_klass_vol --dir2 gt --q2 0.50 \
        --tp-mult 0.25 --sl-mult 0.50 --max-bars 100 \
        --extra-columns intra_max_drawdown,intra_garman_klass_vol

Gates:
    1. Signal count: |N_SQL - N_PY| / max(N_SQL, N_PY) < 5%
    2. Timestamp match: >95% of signals have identical timestamp_ms
    3. Entry price match: >95% of matched signals have <0.01% price difference
    4. Exit type match: >90% of matched signals have same exit type (TP/SL/TIME)
    5. Kelly fraction: |Kelly_SQL - Kelly_PY| < 0.02 absolute

Copied from: scripts/verify_ap15_compare.py (3-gate AP-15 oracle)
"""

import argparse
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_sql_tsv(path):
    """Load SQL TSV output, skip noise lines before header."""
    rows = []
    with open(path) as f:
        header_line = None
        for line in f:
            if line.startswith("timestamp_ms"):
                header_line = line
                break
        if header_line is None:
            return rows
        header = header_line.strip().split("\t")
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split("\t")
            if len(fields) == len(header):
                rows.append(dict(zip(header, fields, strict=True)))
    return rows


def run_backtesting_py(symbol, threshold, end_ts_ms, *, config):
    """Run Gen600Strategy via backtesting.py and extract per-trade data.

    Args:
        config: dict with keys: pattern, feature1_name, feature1_direction,
            feature1_quantile, feature2_name, feature2_direction, feature2_quantile,
            tp_mult, sl_mult, max_bars, extra_columns

    Returns list of dicts with: timestamp_ms, entry_price, exit_type, exit_price, pnl_pct
    """
    import pandas as pd
    from backtesting import Backtest

    from backtest.backtesting_py.data_loader import load_range_bars
    from backtest.backtesting_py.gen600_strategy import Gen600Strategy

    end_date = pd.Timestamp(end_ts_ms, unit="ms").strftime("%Y-%m-%d")

    bar_range = threshold / 100_000.0
    tp_mult = config["tp_mult"]
    sl_mult = config["sl_mult"]

    bar_count = config.get("bar_count")
    align_end_ts_ms = config.get("end_ts_ms")
    align_msg = ""
    if align_end_ts_ms:
        align_msg += f" end_ts={align_end_ts_ms}"
    if bar_count:
        align_msg += f" bar_count={bar_count}"

    print(f"Loading {symbol}@{threshold} range bars (start=2017-01-01, end={end_date})...{align_msg}")
    df = load_range_bars(
        symbol=symbol,
        threshold=threshold,
        start="2017-01-01",
        end=end_date,
        extra_columns=config.get("extra_columns"),
        end_ts_ms=align_end_ts_ms,
        bar_count=bar_count,
    )
    print(f"  Loaded {len(df)} bars ({df.index[0]} to {df.index[-1]})")

    Gen600Strategy.pattern = config["pattern"]
    Gen600Strategy.feature1_name = config["feature1_name"]
    Gen600Strategy.feature1_direction = config["feature1_direction"]
    Gen600Strategy.feature1_quantile = config["feature1_quantile"]
    Gen600Strategy.feature2_name = config["feature2_name"]
    Gen600Strategy.feature2_direction = config["feature2_direction"]
    Gen600Strategy.feature2_quantile = config["feature2_quantile"]
    Gen600Strategy.tp_mult = tp_mult
    Gen600Strategy.sl_mult = sl_mult
    Gen600Strategy.max_bars = config["max_bars"]
    Gen600Strategy.bar_range = bar_range

    bt = Backtest(
        df,
        Gen600Strategy,
        cash=10_000_000,
        commission=0,
        hedging=True,
        exclusive_orders=False,
    )

    stats = bt.run()

    signal_ts_list = stats._strategy._signal_timestamps
    trades = stats._trades.sort_values("EntryTime").reset_index(drop=True)
    py_trades = []
    for i, (_, trade) in enumerate(trades.iterrows()):
        entry_price = float(trade["EntryPrice"])
        exit_price = float(trade["ExitPrice"])
        pnl_pct = (exit_price - entry_price) / entry_price

        signal_ts = str(signal_ts_list[i]) if i < len(signal_ts_list) else "0"

        if bar_range > 0:
            tp_price = entry_price * (1.0 + tp_mult * bar_range)
            sl_price = entry_price * (1.0 - sl_mult * bar_range)
            if exit_price >= tp_price * 0.999:
                exit_type = "TP"
            elif exit_price <= sl_price * 1.001:
                exit_type = "SL"
            else:
                exit_type = "TIME"
        else:
            exit_type = "TIME"

        py_trades.append({
            "timestamp_ms": signal_ts,
            "entry_price": str(entry_price),
            "exit_type": exit_type,
            "exit_price": str(exit_price),
            "pnl_pct": pnl_pct,
        })

    return py_trades, stats


def compute_kelly(trades, is_sql=False):
    """Compute Kelly fraction from trade list."""
    if not trades:
        return 0.0

    if is_sql:
        wins = sum(1 for t in trades if t["exit_type"] == "TP")
        losses = sum(1 for t in trades if t["exit_type"] == "SL")
        # TIME exits: compute from entry/exit price
        for t in trades:
            if t["exit_type"] == "TIME":
                ep = float(t["entry_price"])
                xp = float(t["exit_price"])
                if xp > ep:
                    wins += 1
                else:
                    losses += 1
    else:
        wins = sum(1 for t in trades if t.get("pnl_pct", 0) > 0)
        losses = sum(1 for t in trades if t.get("pnl_pct", 0) <= 0)

    n = wins + losses
    if n == 0:
        return 0.0
    p = wins / n
    if p >= 1.0:
        return 1.0
    if p <= 0.0:
        return -1.0

    # For symmetric barriers: avg win ≈ avg loss ≈ barrier distance
    # Kelly = p - (1-p) = 2p - 1
    # Use actual PnL for more accurate calculation
    if not is_sql:
        pnls = [t["pnl_pct"] for t in trades]
        avg_win = sum(p for p in pnls if p > 0) / max(wins, 1)
        avg_loss = abs(sum(p for p in pnls if p <= 0) / max(losses, 1))
        if avg_loss > 0:
            return p - (1 - p) / (avg_win / avg_loss)
        return p
    else:
        # For SQL: use entry/exit prices
        pnls = []
        for t in trades:
            ep = float(t["entry_price"])
            xp = float(t["exit_price"])
            pnls.append((xp - ep) / ep)
        avg_win = sum(p for p in pnls if p > 0) / max(wins, 1)
        avg_loss = abs(sum(p for p in pnls if p <= 0) / max(losses, 1))
        if avg_loss > 0:
            return p - (1 - p) / (avg_win / avg_loss)
        return p


def _build_config(args):
    """Build config dict from CLI args."""
    extra = args.extra_columns.split(",") if args.extra_columns else None
    return {
        "pattern": args.pattern,
        "feature1_name": args.feature1,
        "feature1_direction": args.dir1,
        "feature1_quantile": args.q1,
        "feature2_name": args.feature2,
        "feature2_direction": args.dir2,
        "feature2_quantile": args.q2,
        "tp_mult": args.tp_mult,
        "sl_mult": args.sl_mult,
        "max_bars": args.max_bars,
        "extra_columns": extra,
        "end_ts_ms": getattr(args, "end_ts_ms", None),
        "bar_count": getattr(args, "bar_count", None),
    }


def _config_label(config):
    """Human-readable config label for output."""
    q1 = f"p{int(config['feature1_quantile'] * 100)}"
    q2 = f"p{int(config['feature2_quantile'] * 100)}"
    return (
        f"{config['pattern']}__{config['feature1_name']}"
        f"_{config['feature1_direction']}_{q1}"
        f"__{config['feature2_name']}"
        f"_{config['feature2_direction']}_{q2}"
    )


def main():
    parser = argparse.ArgumentParser(description="Gen600 5-gate oracle comparison")
    parser.add_argument("--sql-tsv", required=True, help="SQL trade TSV file path")
    parser.add_argument("--symbol", default="SOLUSDT", help="Trading symbol")
    parser.add_argument("--threshold", type=int, default=1000, help="Threshold in dBps")
    # Strategy config (defaults match original udd oracle)
    parser.add_argument("--pattern", default="udd", help="Pattern id")
    parser.add_argument("--feature1", default="volume_per_trade", help="Feature 1 name")
    parser.add_argument("--dir1", default="lt", help="Feature 1 direction (lt/gt)")
    parser.add_argument("--q1", type=float, default=0.50, help="Feature 1 quantile")
    parser.add_argument("--feature2", default="lookback_price_range", help="Feature 2 name")
    parser.add_argument("--dir2", default="lt", help="Feature 2 direction (lt/gt)")
    parser.add_argument("--q2", type=float, default=0.50, help="Feature 2 quantile")
    parser.add_argument("--tp-mult", type=float, default=0.50, help="TP barrier multiplier")
    parser.add_argument("--sl-mult", type=float, default=0.50, help="SL barrier multiplier")
    parser.add_argument("--max-bars", type=int, default=50, help="Max bars time barrier")
    parser.add_argument("--extra-columns", default="volume_per_trade,lookback_price_range",
                        help="Comma-separated extra columns for data loader")
    # Data alignment (match SQL's aligned bar window)
    parser.add_argument("--end-ts", type=int, default=None, dest="end_ts_ms",
                        help="End timestamp in ms (overrides end date for SQL alignment)")
    parser.add_argument("--bar-count", type=int, default=None,
                        help="Trim to last N bars (matches SQL ORDER BY DESC LIMIT N)")
    args = parser.parse_args()

    config = _build_config(args)

    # Load SQL trades
    sql_rows = load_sql_tsv(args.sql_tsv)
    print(f"\nSQL trades:  {len(sql_rows)}")

    # Determine end timestamp from SQL data (match cutoff)
    end_ts_ms = 1738713600000  # 2025-02-05 00:00:00 UTC (matches SQL WHERE clause)

    # Run backtesting.py
    py_trades, _stats = run_backtesting_py(args.symbol, args.threshold, end_ts_ms, config=config)
    print(f"Python trades: {len(py_trades)}")

    # ================================================================
    # Gate 1: Signal count alignment (hedging=True enables multi-position)
    # With hedging=True + exclusive_orders=False, Python evaluates signals
    # independently like SQL. Counts should match within 5%.
    # ================================================================
    max_n = max(len(sql_rows), len(py_trades))
    if max_n == 0:
        print("FAIL: No signals found")
        sys.exit(1)

    count_diff = abs(len(sql_rows) - len(py_trades)) / max_n
    gate1 = count_diff < 0.05
    verdict = "PASS" if gate1 else "FAIL"
    print(f"\nGate 1 - Signal Count: SQL={len(sql_rows)} PY={len(py_trades)}"
          f" diff={count_diff:.4f} (<5%) -> {verdict}")

    # ================================================================
    # Gate 2: Timestamp match — bidirectional overlap
    # ================================================================
    sql_by_ts = {row["timestamp_ms"]: row for row in sql_rows}
    py_by_ts = {row["timestamp_ms"]: row for row in py_trades}

    sql_ts = set(sql_by_ts.keys())
    py_ts = set(py_by_ts.keys())
    matched_ts = sql_ts & py_ts
    only_sql = sql_ts - py_ts
    only_py = py_ts - sql_ts

    overlap = len(matched_ts) / max_n if max_n > 0 else 0
    gate2 = overlap > 0.95
    verdict = "PASS" if gate2 else "FAIL"
    print(f"Gate 2 - Timestamp Match: {len(matched_ts)}/{max_n}"
          f" ({overlap:.4f}) (>95%) -> {verdict}")

    if only_sql:
        print(f"  SQL-only timestamps: {len(only_sql)} (first 5: {sorted(only_sql)[:5]})")
    if only_py:
        print(f"  Python-only timestamps: {len(only_py)} (first 5: {sorted(only_py)[:5]})")

    # ================================================================
    # Gate 3: Entry price alignment on matched signals
    # _trades sorted by EntryTime to match signal chronological order.
    # Both SQL (leadInFrame(open,1)) and Python (next-bar open) use
    # the same deterministic price — expect near-100% match.
    # ================================================================
    price_matches = 0
    price_mismatches = []

    for ts in sorted(matched_ts):
        sql_ep = float(sql_by_ts[ts]["entry_price"])
        py_ep = float(py_by_ts[ts]["entry_price"])
        if py_ep > 0:
            diff = abs(sql_ep - py_ep) / py_ep
            if diff < 0.0001:  # 0.01%
                price_matches += 1
            else:
                price_mismatches.append((ts, sql_ep, py_ep, diff))

    if len(matched_ts) > 0:
        price_match_rate = price_matches / len(matched_ts)
        gate3 = price_match_rate > 0.95
        verdict = "PASS" if gate3 else "FAIL"
        print(f"Gate 3 - Entry Price: {price_matches}/{len(matched_ts)}"
              f" ({price_match_rate:.4f}) (>95%) -> {verdict}")
    else:
        gate3 = False
        print("Gate 3 - Entry Price: No matched signals to compare -> FAIL")

    if price_mismatches:
        print(f"  Price mismatches ({len(price_mismatches)}):")
        for ts, sql_ep, py_ep, diff in price_mismatches[:5]:
            print(f"    ts={ts}: SQL={sql_ep:.8f} PY={py_ep:.8f} diff={diff:.6f}")

    # ================================================================
    # Gate 4: Exit type alignment on matched signals
    # ================================================================
    exit_matches = 0
    exit_mismatches = []
    for ts in sorted(matched_ts):
        sql_exit = sql_by_ts[ts].get("exit_type", "?")
        py_exit = py_by_ts[ts].get("exit_type", "?")
        if sql_exit == py_exit:
            exit_matches += 1
        else:
            exit_mismatches.append((ts, sql_exit, py_exit))

    if len(matched_ts) > 0:
        exit_match_rate = exit_matches / len(matched_ts)
        gate4 = exit_match_rate > 0.90
        verdict = "PASS" if gate4 else "FAIL"
        print(f"Gate 4 - Exit Type: {exit_matches}/{len(matched_ts)}"
              f" ({exit_match_rate:.4f}) (>90%) -> {verdict}")
    else:
        gate4 = False
        print("Gate 4 - Exit Type: No matched signals to compare -> FAIL")

    if exit_mismatches:
        print("  Exit type mismatches (first 10):")
        for ts, sql_et, py_et in exit_mismatches[:10]:
            print(f"    ts={ts}: SQL={sql_et} PY={py_et}")

    # Count exit type distribution
    sql_exit_dist = {}
    py_exit_dist = {}
    for row in sql_rows:
        et = row.get("exit_type", "?")
        sql_exit_dist[et] = sql_exit_dist.get(et, 0) + 1
    for row in py_trades:
        et = row.get("exit_type", "?")
        py_exit_dist[et] = py_exit_dist.get(et, 0) + 1
    print(f"  SQL exit distribution: {sql_exit_dist}")
    print(f"  Python exit distribution: {py_exit_dist}")

    # ================================================================
    # Gate 5: Kelly fraction alignment
    # ================================================================
    kelly_sql = compute_kelly(sql_rows, is_sql=True)
    kelly_py = compute_kelly(py_trades, is_sql=False)
    kelly_diff = abs(kelly_sql - kelly_py)
    gate5 = kelly_diff < 0.02
    verdict = "PASS" if gate5 else "FAIL"
    print(f"Gate 5 - Kelly Fraction: SQL={kelly_sql:.4f} PY={kelly_py:.4f}"
          f" diff={kelly_diff:.4f} (<0.02) -> {verdict}")

    # Also report win rates
    sql_wr = sum(1 for r in sql_rows if r.get("exit_type") == "TP") / len(sql_rows) if sql_rows else 0
    py_wr = sum(1 for t in py_trades if t.get("pnl_pct", 0) > 0) / len(py_trades) if py_trades else 0
    print(f"  Win Rate: SQL={sql_wr:.4f} PY={py_wr:.4f}")

    # ================================================================
    # Overall verdict
    # ================================================================
    print(f"\n{'='*60}")
    gates = [gate1, gate2, gate3, gate4, gate5]
    gate_names = ["Count", "Timing", "Price", "Exit Type", "Kelly"]
    all_pass = all(gates)

    print(f"OVERALL: {'ALL 5 GATES PASS' if all_pass else 'SOME GATES FAILED'}")
    for i, (g, name) in enumerate(zip(gates, gate_names, strict=True), 1):
        print(f"  Gate {i} ({name:>10s}): {'PASS' if g else 'FAIL'}")

    print(f"\nConfig: {_config_label(config)}")
    print(f"Asset:  {args.symbol}@{args.threshold}")
    tp = config['tp_mult']
    sl = config['sl_mult']
    mb = config['max_bars']
    sym = "symmetric" if tp == sl else "inverted"
    print(f"Barrier: TP={tp}x SL={sl}x max_bars={mb} ({sym})")

    # Write results to TSV for downstream consumption
    out_path = f"/tmp/oracle_result_{args.symbol.lower()}_{args.threshold}.tsv"
    with open(out_path, "w") as f:
        f.write("gate\tname\tresult\tdetail\n")
        details = [
            f"diff={count_diff:.4f}",
            f"overlap={overlap:.4f}",
            f"match_rate={price_match_rate:.4f}" if len(matched_ts) > 0 else "no_matches",
            f"match_rate={exit_match_rate:.4f}" if len(matched_ts) > 0 else "no_matches",
            f"sql={kelly_sql:.4f},py={kelly_py:.4f},diff={kelly_diff:.4f}",
        ]
        for i, (g, name, detail) in enumerate(zip(gates, gate_names, details, strict=True), 1):
            f.write(f"{i}\t{name}\t{'PASS' if g else 'FAIL'}\t{detail}\n")
    print(f"\nResults written to {out_path}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
