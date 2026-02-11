"""Atomic trade reconstruction: bar-by-bar inspection of ClickHouse trade configs.

Reconstructs individual trades from high-performing SQL configs to understand
what the pattern captures at the microstructure level. Shows feature diagnostics,
barrier progression, and per-bar P&L tracking.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/13

Run with:
    RBP_INSPECT_CONFIG_ID=price_impact_lt_p10__volume_per_trade_gt_p75 \
    RBP_INSPECT_TRADE_N=1 \
    python -m rangebar_patterns.introspect
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime

from rangebar_patterns.config import MAX_BARS, SL_MULT, SYMBOL, THRESHOLD_DBPS, TP_MULT
from rangebar_patterns.eval.extraction import _CTE_TEMPLATE, FEATURES, GRID

# Reverse lookup: suffix → (quantile_pct, direction)
_SUFFIX_TO_GRID: dict[str, tuple[str, str]] = {
    suffix: (quantile_pct, direction)
    for quantile_pct, direction, suffix in GRID
}

# ---------------------------------------------------------------------------
# Final SELECTs for inspection (appended to _CTE_TEMPLATE via {final_select})
# ---------------------------------------------------------------------------

# Query 1: Numbered list of all trades for this config
_TRADE_LIST_SELECT = """
SELECT
    row_number() OVER (ORDER BY timestamp_ms) AS trade_n,
    timestamp_ms,
    entry_price,
    exit_type,
    exit_price,
    (exit_price - entry_price) / entry_price AS pnl_pct
FROM trade_outcomes
WHERE exit_type != 'INCOMPLETE'
ORDER BY timestamp_ms
""".strip()

# Query 2: Single trade detail — bar-by-bar lifecycle with barrier distances.
# Requires additional CTE to filter to one specific signal by timestamp_ms,
# then expands forward arrays to rows via ARRAY JOIN.
_TRADE_DETAIL_SELECT = """
SELECT
    s.timestamp_ms AS signal_ts,
    s.entry_price AS entry_price,
    s.feature1_lag1 AS feature1_lag1,
    s.feature2_lag1 AS feature2_lag1,
    s.feature1_q AS feature1_threshold,
    s.feature2_q AS feature2_threshold,
    p.tp_price,
    p.sl_price,
    p.tp_mult,
    p.sl_mult,
    p.max_bars,
    t.exit_type,
    t.exit_price,
    b.exit_bar,
    bar_idx,
    p.fwd_opens[bar_idx] AS bar_open,
    p.fwd_highs[bar_idx] AS bar_high,
    p.fwd_lows[bar_idx] AS bar_low,
    p.fwd_closes[bar_idx] AS bar_close,
    p.tp_price - p.fwd_highs[bar_idx] AS tp_distance,
    p.fwd_lows[bar_idx] - p.sl_price AS sl_distance,
    (p.fwd_closes[bar_idx] - s.entry_price) / s.entry_price AS running_pnl
FROM signals s
INNER JOIN param_with_prices p ON p.timestamp_ms = s.timestamp_ms
INNER JOIN trade_outcomes t ON t.timestamp_ms = s.timestamp_ms
INNER JOIN (
    SELECT
        timestamp_ms,
        CASE
            WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_sl_bar <= raw_tp_bar THEN raw_sl_bar
            WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_tp_bar < raw_sl_bar THEN raw_tp_bar
            WHEN raw_sl_bar > 0 AND raw_tp_bar = 0 THEN raw_sl_bar
            WHEN raw_tp_bar > 0 AND raw_sl_bar = 0 THEN raw_tp_bar
            ELSE max_bars
        END AS exit_bar
    FROM barrier_scan
) b ON b.timestamp_ms = s.timestamp_ms
ARRAY JOIN arrayEnumerate(p.fwd_opens) AS bar_idx
WHERE s.timestamp_ms = {signal_ts}
  AND bar_idx <= b.exit_bar
ORDER BY bar_idx
""".strip()


def _parse_half(half: str) -> tuple[str, str, str, str]:
    """Parse one half of a config_id into (feature, quantile_pct, direction, suffix).

    Handles multi-word features like 'volume_per_trade' by trying longest
    feature match first.
    """
    for feature in sorted(FEATURES, key=len, reverse=True):
        prefix = feature + "_"
        if half.startswith(prefix):
            suffix = half[len(prefix):]
            if suffix in _SUFFIX_TO_GRID:
                quantile_pct, direction = _SUFFIX_TO_GRID[suffix]
                return feature, quantile_pct, direction, suffix
    raise ValueError(f"Cannot parse config half: {half!r}")


def parse_config_id(config_id: str) -> dict:
    """Reverse a config_id string into SQL parameter dict.

    Args:
        config_id: Format 'feature1_qualifier1__feature2_qualifier2'
                   e.g. 'price_impact_lt_p10__volume_per_trade_gt_p75'

    Returns:
        Dict with keys: config_id, feature_col_1, feature_col_2,
        quantile_pct_1, quantile_pct_2, direction_1, direction_2
    """
    parts = config_id.split("__")
    if len(parts) != 2:
        raise ValueError(f"config_id must contain exactly one '__': {config_id!r}")

    f1, q1, d1, _s1 = _parse_half(parts[0])
    f2, q2, d2, _s2 = _parse_half(parts[1])

    return {
        "config_id": config_id,
        "feature_col_1": f1,
        "feature_col_2": f2,
        "quantile_pct_1": q1,
        "quantile_pct_2": q2,
        "direction_1": d1,
        "direction_2": d2,
    }


def build_inspect_sql(config: dict, mode: str, signal_ts: int | None = None) -> str:
    """Build SQL for trade inspection.

    Args:
        config: Dict from parse_config_id().
        mode: 'trade_list' or 'trade_detail'.
        signal_ts: Required for 'trade_detail' — timestamp_ms of the signal.
    """
    if mode == "trade_list":
        final_select = _TRADE_LIST_SELECT
    elif mode == "trade_detail":
        if signal_ts is None:
            raise ValueError("signal_ts required for trade_detail mode")
        final_select = _TRADE_DETAIL_SELECT.format(signal_ts=signal_ts)
    else:
        raise ValueError(f"Unknown mode: {mode!r}")

    return _CTE_TEMPLATE.format(
        symbol=SYMBOL,
        threshold=THRESHOLD_DBPS,
        tp_mult=TP_MULT,
        sl_mult=SL_MULT,
        max_bars=MAX_BARS,
        max_bars_plus1=MAX_BARS + 1,
        final_select=final_select,
        **config,
    )


# ---------------------------------------------------------------------------
# ClickHouse query execution
# ---------------------------------------------------------------------------


def fetch_trade_list(client, config: dict) -> list[dict]:
    """Fetch numbered trade list for a config."""
    sql = build_inspect_sql(config, "trade_list")
    result = client.query(sql)
    cols = result.column_names
    return [dict(zip(cols, row, strict=True)) for row in result.result_rows]


def fetch_trade_detail(client, config: dict, trade_meta: dict) -> dict:
    """Fetch bar-by-bar detail for a single trade.

    Returns dict with trade metadata + list of bar dicts.
    """
    sql = build_inspect_sql(config, "trade_detail", signal_ts=trade_meta["timestamp_ms"])
    result = client.query(sql)
    cols = result.column_names
    rows = [dict(zip(cols, row, strict=True)) for row in result.result_rows]

    if not rows:
        return {"config": config, "trade_meta": trade_meta, "bars": [], "error": "No rows returned"}

    first = rows[0]
    return {
        "config": config,
        "trade_meta": trade_meta,
        "signal_ts": int(first["signal_ts"]),
        "entry_price": float(first["entry_price"]),
        "exit_price": float(first["exit_price"]),
        "exit_type": first["exit_type"],
        "tp_price": float(first["tp_price"]),
        "sl_price": float(first["sl_price"]),
        "tp_mult": float(first["tp_mult"]),
        "sl_mult": float(first["sl_mult"]),
        "max_bars": int(first["max_bars"]),
        "feature1_name": config["feature_col_1"],
        "feature1_value": float(first["feature1_lag1"]),
        "feature1_threshold": float(first["feature1_threshold"]),
        "feature2_name": config["feature_col_2"],
        "feature2_value": float(first["feature2_lag1"]),
        "feature2_threshold": float(first["feature2_threshold"]),
        "bars": [
            {
                "bar_idx": int(r["bar_idx"]),
                "open": float(r["bar_open"]),
                "high": float(r["bar_high"]),
                "low": float(r["bar_low"]),
                "close": float(r["bar_close"]),
                "tp_distance": float(r["tp_distance"]),
                "sl_distance": float(r["sl_distance"]),
                "running_pnl": float(r["running_pnl"]),
            }
            for r in rows
        ],
    }


# ---------------------------------------------------------------------------
# Renderers (plain text, no external dependencies)
# ---------------------------------------------------------------------------


def render_summary(detail: dict, total_trades: int) -> str:
    """Trade summary header."""
    ts = datetime.fromtimestamp(detail["signal_ts"] / 1000, tz=UTC)
    pnl = (detail["exit_price"] - detail["entry_price"]) / detail["entry_price"] * 100
    n_bars = len(detail["bars"])
    trade_n = detail["trade_meta"]["trade_n"]

    lines = [
        f"{'═' * 50}",
        f"  Trade #{trade_n} / {total_trades}",
        f"{'═' * 50}",
        f"  Config:  {detail['config']['config_id']}",
        f"  Symbol:  {SYMBOL} @{THRESHOLD_DBPS}dbps",
        f"  Signal:  {ts.strftime('%Y-%m-%d %H:%M:%S')} UTC",
        f"  Entry:   {detail['entry_price']:.6f} -> Exit: {detail['exit_price']:.6f} ({detail['exit_type']})",
        f"  P&L:     {pnl:+.4f}%",
        f"  Bars:    {n_bars} / {detail['max_bars']} max",
    ]
    return "\n".join(lines)


def render_feature_diagnostic(detail: dict) -> str:
    """Feature diagnostic table showing quantile pass/fail."""
    config = detail["config"]
    d1_symbol = "<" if config["direction_1"] == "<" else ">"
    d2_symbol = "<" if config["direction_2"] == "<" else ">"
    pass1 = (
        detail["feature1_value"] < detail["feature1_threshold"]
        if d1_symbol == "<"
        else detail["feature1_value"] > detail["feature1_threshold"]
    )
    pass2 = (
        detail["feature2_value"] < detail["feature2_threshold"]
        if d2_symbol == "<"
        else detail["feature2_value"] > detail["feature2_threshold"]
    )

    def _fmt_row(name, val, thresh, qpct, direction, passed):
        q_label = "p" + qpct.replace("0.", "")
        return (
            f"  {name:<25s} {val:>12.6f}  {thresh:>12.6f}"
            f"  {q_label:>8s}  {direction:>6s}  {'YES' if passed else 'NO':>4s}"
        )

    hdr = (
        f"  {'Feature':<25s} {'Value':>12s}  {'Threshold':>12s}"
        f"  {'Quantile':>8s}  {'Filter':>6s}  {'Pass':>4s}"
    )
    sep = f"  {'-' * 25} {'-' * 12}  {'-' * 12}  {'-' * 8}  {'-' * 6}  {'-' * 4}"

    lines = [
        "",
        "Feature Diagnostic:",
        hdr,
        sep,
        _fmt_row(
            detail["feature1_name"], detail["feature1_value"],
            detail["feature1_threshold"], config["quantile_pct_1"], d1_symbol, pass1,
        ),
        _fmt_row(
            detail["feature2_name"], detail["feature2_value"],
            detail["feature2_threshold"], config["quantile_pct_2"], d2_symbol, pass2,
        ),
    ]
    return "\n".join(lines)


def render_barrier_progression(detail: dict) -> str:
    """Bar-by-bar barrier progression table."""
    hdr = (
        f"  {'Bar':>4s}  {'Open':>12s}  {'High':>12s}  {'Low':>12s}"
        f"  {'Close':>12s}  {'->TP':>10s}  {'->SL':>10s}  {'P&L':>8s}"
    )
    sep = (
        f"  {'-' * 4}  {'-' * 12}  {'-' * 12}  {'-' * 12}"
        f"  {'-' * 12}  {'-' * 10}  {'-' * 10}  {'-' * 8}"
    )
    lines = ["", "Barrier Progression:", hdr, sep]

    exit_type = detail["exit_type"]
    exit_bar = len(detail["bars"])

    for bar in detail["bars"]:
        idx = bar["bar_idx"]
        is_exit_bar = idx == exit_bar

        if is_exit_bar and exit_type == "TP":
            tp_str = "HIT TP"
            sl_str = ""
        elif is_exit_bar and exit_type == "SL":
            tp_str = ""
            sl_str = "HIT SL"
        else:
            tp_str = f"{bar['tp_distance']:+.6f}"
            sl_str = f"{bar['sl_distance']:+.6f}"

        pnl_str = f"{bar['running_pnl'] * 100:+.4f}%"

        lines.append(
            f"  {idx:>4d}  {bar['open']:>12.6f}  {bar['high']:>12.6f}  "
            f"{bar['low']:>12.6f}  {bar['close']:>12.6f}  "
            f"{tp_str:>10s}  {sl_str:>10s}  {pnl_str:>8s}"
        )

    return "\n".join(lines)


def export_json(detail: dict) -> str:
    """JSON export for ML pipeline consumption."""
    return json.dumps(detail, default=str)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    """Inspect a single trade bar-by-bar."""
    config_id = os.environ.get("RBP_INSPECT_CONFIG_ID")
    trade_n = int(os.environ.get("RBP_INSPECT_TRADE_N", "1"))
    json_mode = "--json" in sys.argv

    if not config_id:
        print("Usage: RBP_INSPECT_CONFIG_ID=<config_id> python -m rangebar_patterns.introspect")
        print("  env: RBP_INSPECT_TRADE_N=1 (default)")
        print("  flag: --json for ML pipeline output")
        sys.exit(1)

    config = parse_config_id(config_id)

    import clickhouse_connect

    from backtest.backtesting_py.ssh_tunnel import SSHTunnel

    ssh_host = os.environ.get("RANGEBAR_CH_HOST", "localhost")
    with SSHTunnel(ssh_host) as local_port:
        client = clickhouse_connect.get_client(host="localhost", port=local_port)

        trades = fetch_trade_list(client, config)
        if not trades:
            print(f"No trades found for config: {config_id}")
            sys.exit(1)

        if trade_n < 1 or trade_n > len(trades):
            print(f"trade_n={trade_n} out of range [1, {len(trades)}]")
            sys.exit(1)

        trade_meta = trades[trade_n - 1]
        detail = fetch_trade_detail(client, config, trade_meta)

    if json_mode:
        print(export_json(detail))
    else:
        print(render_summary(detail, total_trades=len(trades)))
        print(render_feature_diagnostic(detail))
        print(render_barrier_progression(detail))


if __name__ == "__main__":
    main()
