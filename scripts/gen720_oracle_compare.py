"""Gen720 Oracle: 5-gate trade-by-trade comparison of SQL vs backtesting.py.

Adapted from gen600_oracle_compare.py for two-segment SL time-decay barriers.
Tests a SINGLE barrier config from the Gen720 434-barrier grid.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/28

Usage:
    # Single-SL baseline (sl_tight == sl_wide, no tightening):
    uv run --python 3.13 python scripts/gen720_oracle_compare.py \
        --sql-tsv results/eval/gen720/raw/2down_SOLUSDT_500.tsv \
        --symbol SOLUSDT --threshold 500 \
        --barrier-id p0_slt050_mb50

    # Tight SL config (most likely to expose gap-down fill mismatch):
    uv run --python 3.13 python scripts/gen720_oracle_compare.py \
        --sql-tsv results/eval/gen720/raw/2down_SOLUSDT_500.tsv \
        --symbol SOLUSDT --threshold 500 \
        --barrier-id p5_slt010_mb100

    # Any barrier config (fully parameterized override):
    uv run --python 3.13 python scripts/gen720_oracle_compare.py \
        --sql-tsv results/eval/gen720/raw/exh_l_SOLUSDT_500.tsv \
        --symbol SOLUSDT --threshold 500 \
        --pattern exh_l \
        --phase1-bars 5 --sl-tight-mult 0.10 \
        --tp-mult 0.25 --sl-mult 0.50 --max-bars 100

Gates:
    1. Signal count: |N_SQL - N_PY| / max(N_SQL, N_PY) < 5%
    2. Timestamp match: >95% of signals have identical timestamp_ms
    3. Entry price match: >95% of matched signals have <0.01% price difference
    4. Exit type match: >90% of matched signals have same exit type (TP/SL/TIME)
    5. PF (profit factor): |PF_SQL - PF_PY| < 0.08 (wider than Gen600's 0.02 Kelly
       to accommodate gap-down SL fill price mismatch in backtesting.py)

Note on Gate 5: Gen720 uses PF instead of Kelly because tight-SL configs amplify
the gap-down fill price difference (SQL: least(open, sl_price), backtesting.py:
max(open, stop_price) for long). PF is a more direct comparison metric for
barrier-based strategies where win/loss sizes are barrier-determined.
"""

import argparse
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def parse_barrier_id(barrier_id):
    """Parse barrier_id string into component parameters.

    Format: p{phase1_bars}_slt{sl_tight_mult*100:03d}_mb{max_bars}
    Examples:
        p5_slt010_mb100 -> phase1_bars=5, sl_tight_mult=0.10, max_bars=100
        p0_slt050_mb50  -> phase1_bars=0, sl_tight_mult=0.50, max_bars=50
        p3_slt000_mb20  -> phase1_bars=3, sl_tight_mult=0.00, max_bars=20
    """
    parts = barrier_id.split("_")
    if len(parts) != 3:
        raise ValueError(f"Invalid barrier_id format: {barrier_id}")

    phase1_bars = int(parts[0][1:])  # "p5" -> 5
    sl_tight_mult = int(parts[1][3:]) / 100.0  # "slt010" -> 0.10
    max_bars = int(parts[2][2:])  # "mb100" -> 100

    return {
        "phase1_bars": phase1_bars,
        "sl_tight_mult": sl_tight_mult,
        "max_bars": max_bars,
    }


def load_sql_tsv(path, barrier_id):
    """Load SQL TSV output, filter to a single barrier_id.

    Gen720 TSV contains ALL 434 barrier combos per signal. We filter to
    the specific barrier_id being oracle-tested.
    """
    rows = []
    with open(path) as f:
        header_line = None
        for line in f:
            stripped = line.strip()
            # Gen720 header: formation\tbarrier_id\tsignal_ts_ms\t...
            if stripped.startswith("formation\t") or stripped.startswith("signal_ts_ms"):
                header_line = stripped
                break
        if header_line is None:
            return rows
        header = header_line.split("\t")
        bid_idx = header.index("barrier_id") if "barrier_id" in header else None
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split("\t")
            if len(fields) != len(header):
                continue
            # Filter to target barrier_id
            if bid_idx is not None and fields[bid_idx] != barrier_id:
                continue
            rows.append(dict(zip(header, fields, strict=True)))
    return rows


def run_backtesting_py(symbol, threshold, *, config):
    """Run Gen720Strategy via backtesting.py and extract per-trade data.

    Args:
        config: dict with keys: pattern, tp_mult, sl_mult, sl_tight_mult,
            phase1_bars, max_bars

    Returns list of dicts with: timestamp_ms, entry_price, exit_type, exit_price, pnl_pct
    """
    from backtesting import Backtest

    from backtest.backtesting_py.data_loader import load_range_bars
    from backtest.backtesting_py.gen720_strategy import Gen720Strategy

    threshold_pct = threshold / 10000.0
    tp_mult = config["tp_mult"]
    sl_mult = config["sl_mult"]
    sl_tight_mult = config["sl_tight_mult"]
    phase1_bars = config["phase1_bars"]

    # Determine extra columns needed for the pattern
    extra_columns = None
    if config["pattern"] in ("exh_l", "exh_l_ng", "exh_s"):
        extra_columns = ["intra_max_drawdown"]
    elif config["pattern"] == "vwap_l":
        extra_columns = ["lookback_vwap_position"]
    elif config["pattern"] == "hvd":
        extra_columns = ["volume"]

    print(f"Loading {symbol}@{threshold} range bars...")
    df = load_range_bars(
        symbol=symbol,
        threshold=threshold,
        start="2017-01-01",
        end="2026-03-01",
        extra_columns=extra_columns,
    )
    print(f"  Loaded {len(df)} bars ({df.index[0]} to {df.index[-1]})")

    Gen720Strategy.pattern = config["pattern"]
    Gen720Strategy.tp_mult = tp_mult
    Gen720Strategy.sl_mult = sl_mult
    Gen720Strategy.sl_tight_mult = sl_tight_mult
    Gen720Strategy.phase1_bars = phase1_bars
    Gen720Strategy.max_bars = config["max_bars"]
    Gen720Strategy.threshold_pct = threshold_pct

    bt = Backtest(
        df,
        Gen720Strategy,
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

        # Detect exit type from price proximity
        if threshold_pct > 0:
            tp_price = entry_price * (1.0 + tp_mult * threshold_pct)
            # SL could be wide or tight depending on when trade exited
            sl_wide = entry_price * (1.0 - sl_mult * threshold_pct)
            sl_tight = entry_price * (1.0 - sl_tight_mult * threshold_pct)

            if exit_price >= tp_price * 0.999:
                exit_type = "TP"
            elif exit_price <= sl_wide * 1.001 or exit_price <= sl_tight * 1.001:
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


def compute_pf(trades, is_sql=False):
    """Compute profit factor from trade list."""
    if not trades:
        return 0.0

    gross_profit = 0.0
    gross_loss = 0.0

    for t in trades:
        if is_sql:
            ep = float(t["entry_price"])
            xp = float(t["exit_price"])
            pnl = (xp - ep) / ep
        else:
            pnl = t.get("pnl_pct", 0)

        if pnl > 0:
            gross_profit += pnl
        else:
            gross_loss += abs(pnl)

    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def main():
    parser = argparse.ArgumentParser(description="Gen720 5-gate oracle comparison")
    parser.add_argument("--sql-tsv", required=True, help="Gen720 SQL TSV file path")
    parser.add_argument("--symbol", default="SOLUSDT", help="Trading symbol")
    parser.add_argument("--threshold", type=int, default=500, help="Threshold in dBps")
    parser.add_argument("--pattern", default="2down", help="Pattern id")
    # Barrier config — either via --barrier-id or individual params
    parser.add_argument("--barrier-id", help="Barrier ID (e.g., p5_slt010_mb100)")
    parser.add_argument("--phase1-bars", type=int, default=None,
                        help="Phase 1 bar count (overrides barrier-id)")
    parser.add_argument("--sl-tight-mult", type=float, default=None,
                        help="Tight SL multiplier (overrides barrier-id)")
    parser.add_argument("--tp-mult", type=float, default=0.25, help="TP multiplier")
    parser.add_argument("--sl-mult", type=float, default=0.50, help="Wide SL multiplier")
    parser.add_argument("--max-bars", type=int, default=None,
                        help="Max bars time barrier (overrides barrier-id)")
    # Gate threshold
    parser.add_argument("--pf-gate", type=float, default=0.08,
                        help="Gate 5 PF difference threshold (default 0.08)")
    args = parser.parse_args()

    # Resolve barrier params from --barrier-id or individual args
    if args.barrier_id:
        bp = parse_barrier_id(args.barrier_id)
        phase1_bars = args.phase1_bars if args.phase1_bars is not None else bp["phase1_bars"]
        sl_tight_mult = args.sl_tight_mult if args.sl_tight_mult is not None else bp["sl_tight_mult"]
        max_bars = args.max_bars if args.max_bars is not None else bp["max_bars"]
        barrier_id = args.barrier_id
    else:
        phase1_bars = args.phase1_bars if args.phase1_bars is not None else 5
        sl_tight_mult = args.sl_tight_mult if args.sl_tight_mult is not None else 0.10
        max_bars = args.max_bars if args.max_bars is not None else 100
        barrier_id = f"p{phase1_bars}_slt{int(sl_tight_mult * 100):03d}_mb{max_bars}"

    config = {
        "pattern": args.pattern,
        "tp_mult": args.tp_mult,
        "sl_mult": args.sl_mult,
        "sl_tight_mult": sl_tight_mult,
        "phase1_bars": phase1_bars,
        "max_bars": max_bars,
    }

    print(f"Gen720 Oracle: {args.pattern} {args.symbol}@{args.threshold}")
    print(f"Barrier: {barrier_id} (TP={args.tp_mult}x SL={args.sl_mult}x "
          f"SL_tight={sl_tight_mult}x phase1={phase1_bars} max_bars={max_bars})")
    print()

    # Load SQL trades for this specific barrier
    sql_rows = load_sql_tsv(args.sql_tsv, barrier_id)
    print(f"SQL trades:  {len(sql_rows)} (barrier_id={barrier_id})")

    if not sql_rows:
        print(f"FAIL: No SQL trades found for barrier_id={barrier_id}")
        print("  Check TSV has this barrier_id. Available barrier_ids (first 5):")
        # Show what's actually in the file
        with open(args.sql_tsv) as f:
            header = None
            seen_bids = set()
            for line in f:
                s = line.strip()
                if header is None and ("barrier_id" in s or "signal_ts_ms" in s):
                    header = s.split("\t")
                    bid_idx = header.index("barrier_id") if "barrier_id" in header else None
                    continue
                if header and bid_idx is not None:
                    fields = s.split("\t")
                    if len(fields) > bid_idx:
                        seen_bids.add(fields[bid_idx])
                    if len(seen_bids) >= 5:
                        break
            print(f"  {sorted(seen_bids)[:5]}")
        sys.exit(1)

    # Run backtesting.py
    py_trades, _stats = run_backtesting_py(args.symbol, args.threshold, config=config)
    print(f"Python trades: {len(py_trades)}")

    # ================================================================
    # Gate 1: Signal count alignment
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
    sql_by_ts = {row["signal_ts_ms"]: row for row in sql_rows}
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

    price_match_rate = 0.0
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

    exit_match_rate = 0.0
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

    # Exit type distribution
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
    # Gate 5: Profit factor alignment
    # Wider threshold (0.08) than Gen600 Kelly (0.02) because:
    # - Gap-down SL fill price mismatch (SQL: least(open,sl), PY: max(open,sl))
    # - Two-segment SL creates more SL events with tight sl_tight_mult
    # - backtesting.py gives BETTER SL fills than SQL (optimistic)
    # ================================================================
    pf_sql = compute_pf(sql_rows, is_sql=True)
    pf_py = compute_pf(py_trades, is_sql=False)

    if pf_sql == float("inf") or pf_py == float("inf"):
        pf_diff = 0.0 if pf_sql == pf_py else 999.0
    else:
        pf_diff = abs(pf_sql - pf_py)

    pf_threshold = args.pf_gate
    gate5 = pf_diff < pf_threshold
    verdict = "PASS" if gate5 else "FAIL"
    print(f"Gate 5 - Profit Factor: SQL={pf_sql:.4f} PY={pf_py:.4f}"
          f" diff={pf_diff:.4f} (<{pf_threshold}) -> {verdict}")

    # Win rates
    sql_wins = sum(1 for r in sql_rows if float(r.get("return_pct", 0)) > 0)
    py_wins = sum(1 for t in py_trades if t.get("pnl_pct", 0) > 0)
    sql_wr = sql_wins / len(sql_rows) if sql_rows else 0
    py_wr = py_wins / len(py_trades) if py_trades else 0
    print(f"  Win Rate: SQL={sql_wr:.4f} PY={py_wr:.4f}")

    # ================================================================
    # Overall verdict
    # ================================================================
    print(f"\n{'='*60}")
    gates = [gate1, gate2, gate3, gate4, gate5]
    gate_names = ["Count", "Timing", "Price", "Exit Type", "PF"]
    all_pass = all(gates)

    print(f"OVERALL: {'ALL 5 GATES PASS' if all_pass else 'SOME GATES FAILED'}")
    for i, (g, name) in enumerate(zip(gates, gate_names, strict=True), 1):
        print(f"  Gate {i} ({name:>10s}): {'PASS' if g else 'FAIL'}")

    print(f"\nConfig: {args.pattern} barrier={barrier_id}")
    print(f"Asset:  {args.symbol}@{args.threshold}")
    print(f"Barrier: TP={args.tp_mult}x SL_wide={args.sl_mult}x "
          f"SL_tight={sl_tight_mult}x phase1={phase1_bars} max_bars={max_bars}")

    # Write results to TSV for downstream consumption
    out_path = (f"/tmp/gen720_oracle_{args.pattern}_{barrier_id}"
                f"_{args.symbol.lower()}_{args.threshold}.tsv")
    with open(out_path, "w") as f:
        f.write("gate\tname\tresult\tdetail\n")
        details = [
            f"diff={count_diff:.4f}",
            f"overlap={overlap:.4f}",
            f"match_rate={price_match_rate:.4f}" if len(matched_ts) > 0 else "no_matches",
            f"match_rate={exit_match_rate:.4f}" if len(matched_ts) > 0 else "no_matches",
            f"sql={pf_sql:.4f},py={pf_py:.4f},diff={pf_diff:.4f}",
        ]
        for i, (g, name, detail) in enumerate(zip(gates, gate_names, details, strict=True), 1):
            f.write(f"{i}\t{name}\t{'PASS' if g else 'FAIL'}\t{detail}\n")
    print(f"\nResults written to {out_path}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
