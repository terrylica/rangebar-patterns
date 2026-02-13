"""AP-15 Verification: Extract Python champion signals for comparison with SQL.

Usage:
    python scripts/verify_ap15.py > /tmp/python_ap15_signals.tsv

Then compare with SQL output:
    ssh bigblack 'clickhouse-client --query "$(cat scripts/verify_ap15.sql)"' > /tmp/sql_ap15_signals.tsv
    python scripts/verify_ap15_compare.py
"""

import sys

import numpy as np

# Add project root to path
sys.path.insert(0, ".")

from backtest.backtesting_py.data_loader import load_range_bars


def rolling_p95(ti_values, window=1000):
    """Rolling p95 matching SQL: ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING."""
    result = np.full(len(ti_values), np.nan)
    for i in range(1, len(ti_values)):
        start = max(0, i - window)
        result[i] = np.percentile(ti_values[start:i], 95)
    return result


def main():
    # Load same data as SQL: SOLUSDT @500
    df = load_range_bars(symbol="SOLUSDT", threshold=500)
    print(f"# Loaded {len(df)} bars", file=sys.stderr)

    # Compute direction: same as SQL CASE WHEN close > open THEN 1 ELSE 0 END
    direction = (df["Close"] > df["Open"]).astype(int).values

    # Compute rolling p95 of trade_intensity
    ti = df["trade_intensity"].values
    ti_p95 = rolling_p95(ti, window=1000)

    kyle = df["kyle_lambda_proxy"].values
    # df.index is DatetimeIndex[ms] from pd.to_datetime(timestamp_ms, unit="ms")
    # astype(int64) gives ms directly (no division needed)
    timestamps = df.index.astype(np.int64).values
    opens = df["Open"].values
    closes = df["Close"].values

    # Header
    print("timestamp_ms\tsignal_open\tsignal_close\tentry_price\tti_0\tti_p95_prior\tkyle_0\tdir_0\tdir_1")

    # Detect champion signals: 2 consecutive DOWN + ti > p95 + kyle > 0
    count = 0
    for i in range(1001, len(df)):  # rn > 1000 equivalent (1-indexed rn=1001 = 0-indexed 1000)
        dir_0 = direction[i]
        dir_1 = direction[i - 1]

        if dir_1 != 0 or dir_0 != 0:
            continue

        ti_0 = ti[i]
        ti_p95_prior = ti_p95[i]

        if np.isnan(ti_p95_prior) or ti_p95_prior <= 0:
            continue
        if ti_0 <= ti_p95_prior:
            continue

        kyle_0 = kyle[i]
        if kyle_0 <= 0 or np.isnan(kyle_0):
            continue

        # Entry price = next bar's open
        if i + 1 >= len(df):
            continue
        entry_price = opens[i + 1]
        if entry_price <= 0 or np.isnan(entry_price):
            continue

        print(
            f"{timestamps[i]}\t{opens[i]}\t{closes[i]}\t{entry_price}\t"
            f"{ti_0}\t{ti_p95_prior}\t{kyle_0}\t{dir_0}\t{dir_1}"
        )
        count += 1

    print(f"# Total signals: {count}", file=sys.stderr)


if __name__ == "__main__":
    main()
