"""Load range bars from ClickHouse into backtesting.py-compatible DataFrame.

ADR: docs/adr/2026-02-06-repository-creation.md

Prefers local ClickHouse (synced via `mise run ch:sync`), falls back to remote SSH tunnel.
Returns DataFrame with DatetimeIndex + capitalized OHLCV + microstructure features.
"""

from __future__ import annotations


def load_range_bars(
    symbol: str = "SOLUSDT",
    threshold: int = 250,
    start: str = "2020-01-01",
    end: str = "2026-01-01",
    ssh_alias: str | None = None,
):
    """Load range bars with microstructure features from ClickHouse.

    Tries local ClickHouse first (localhost:8123). If local has no data for the
    requested symbol/threshold, falls back to SSH tunnel (set RANGEBAR_CH_HOST).

    Returns DataFrame with DatetimeIndex + OHLCV + trade_intensity + kyle_lambda_proxy.
    Compatible with backtesting.py (requires capitalized OHLCV columns).
    """
    import clickhouse_connect
    import pandas as pd
    import polars as pl

    from backtest.backtesting_py.ssh_tunnel import SSHTunnel, _is_port_open

    start_ts = int(pd.Timestamp(start).timestamp() * 1000)
    end_ts = int(pd.Timestamp(end).timestamp() * 1000)

    query = f"""
        SELECT timestamp_ms, open, high, low, close, volume,
               trade_intensity, kyle_lambda_proxy, duration_us
        FROM rangebar_cache.range_bars
        WHERE symbol = '{symbol}'
          AND threshold_decimal_bps = {threshold}
          AND timestamp_ms >= {start_ts}
          AND timestamp_ms < {end_ts}
        ORDER BY timestamp_ms
    """

    # Try local ClickHouse first
    if _is_port_open("localhost", 8123, timeout=1.0):
        client = clickhouse_connect.get_client(host="localhost", port=8123)
        result = client.query_arrow(query)
        if result.num_rows > 0:
            print(f"  [local] {result.num_rows} rows from localhost:8123")
            return _to_backtest_df(result, pl, pd)

    # Fall back to SSH tunnel
    import os
    if ssh_alias is None:
        ssh_alias = os.environ.get("RANGEBAR_CH_HOST", "localhost")
    print(f"  [tunnel] No local data, connecting via SSH tunnel to {ssh_alias}...")
    tunnel = SSHTunnel(ssh_alias)
    with tunnel as local_port:
        client = clickhouse_connect.get_client(host="localhost", port=local_port)
        result = client.query_arrow(query)
        print(f"  [tunnel] {result.num_rows} rows via {ssh_alias}")

    return _to_backtest_df(result, pl, pd)


def _to_backtest_df(arrow_table, pl, pd):
    """Convert Arrow table to backtesting.py-compatible DataFrame."""
    df = pl.from_arrow(arrow_table).to_pandas()
    df.index = pd.to_datetime(df["timestamp_ms"], unit="ms")
    df.index.name = None
    df = df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    })
    return df
