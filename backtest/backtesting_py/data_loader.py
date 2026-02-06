"""Load range bars from BigBlack ClickHouse into backtesting.py-compatible DataFrame.

ADR: docs/adr/2026-02-06-repository-creation.md

Returns DataFrame with DatetimeIndex + capitalized OHLCV + microstructure features.
"""

from __future__ import annotations


def load_range_bars(
    symbol: str = "SOLUSDT",
    threshold: int = 250,
    start: str = "2020-01-01",
    end: str = "2026-01-01",
    host: str = "bigblack",
):
    """Load range bars with microstructure features from ClickHouse.

    Returns DataFrame with DatetimeIndex + OHLCV + trade_intensity + kyle_lambda_proxy.
    Compatible with backtesting.py (requires capitalized OHLCV columns).
    """
    import clickhouse_connect
    import pandas as pd
    import polars as pl

    start_ts = int(pd.Timestamp(start).timestamp() * 1000)
    end_ts = int(pd.Timestamp(end).timestamp() * 1000)

    client = clickhouse_connect.get_client(host=host)
    result = client.query_arrow(f"""
        SELECT timestamp_ms, open, high, low, close, volume,
               trade_intensity, kyle_lambda_proxy
        FROM rangebar_cache.range_bars
        WHERE symbol = '{symbol}'
          AND threshold_decimal_bps = {threshold}
          AND timestamp_ms >= {start_ts}
          AND timestamp_ms < {end_ts}
        ORDER BY timestamp_ms
    """)

    df = pl.from_arrow(result).to_pandas()
    df.index = pd.to_datetime(df["timestamp_ms"], unit="ms")
    df.index.name = None

    # backtesting.py requires capitalized OHLCV columns
    df = df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    })
    return df
