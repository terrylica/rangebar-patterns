"""Agent 2: Extract per-trade return arrays from ClickHouse.

Returns full ordered sequence of individual trade returns per config,
needed by Omega Ratio (layer5), CSCV/PBO (layer6), and E-values (layer7).

Copied from layer1_sql_moments.py (same CTE chain, different final SELECT).
Reuses SSH tunnel from backtest/backtesting_py/ssh_tunnel.py.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""

from __future__ import annotations

import itertools
import json
import sys
import time
from pathlib import Path

# Add repo root to sys.path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

RESULTS_DIR = Path(__file__).resolve().parent / "results"
OUTPUT_FILE = RESULTS_DIR / "trade_returns.jsonl"

# Same config space as gen500 (scripts/gen500/generate.sh)
FEATURES = [
    "ofi", "aggression_ratio", "turnover_imbalance", "price_impact",
    "vwap_close_deviation", "volume_per_trade", "aggregation_density", "duration_us",
]

GRID = [
    ("0.50", ">", "gt_p50"),
    ("0.50", "<", "lt_p50"),
    ("0.75", ">", "gt_p75"),
    ("0.25", "<", "lt_p25"),
    ("0.90", ">", "gt_p90"),
    ("0.10", "<", "lt_p10"),
]

SYMBOL = "SOLUSDT"
THRESHOLD_DBPS = 500

# SQL template: gen500 CTE chain with groupArray in final SELECT
# Returns per-trade return arrays ordered by timestamp
SQL_TEMPLATE = """
WITH
base_bars AS (
    SELECT
        timestamp_ms,
        open, high, low, close,
        trade_intensity,
        kyle_lambda_proxy,
        {feature_col_1},
        {feature_col_2},
        CASE WHEN close > open THEN 1 ELSE 0 END AS direction,
        row_number() OVER (ORDER BY timestamp_ms) AS rn
    FROM rangebar_cache.range_bars
    WHERE symbol = '{symbol}' AND threshold_decimal_bps = {threshold}
    ORDER BY timestamp_ms
),
running_stats AS (
    SELECT
        *,
        quantileExactExclusive(0.95)(trade_intensity) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
        ) AS ti_p95_rolling
    FROM base_bars
),
signal_detection AS (
    SELECT
        timestamp_ms,
        open, high, low, close,
        direction,
        rn,
        lagInFrame(trade_intensity, 1) OVER w AS ti_1,
        lagInFrame(kyle_lambda_proxy, 1) OVER w AS kyle_1,
        lagInFrame(direction, 1) OVER w AS dir_1,
        lagInFrame(direction, 2) OVER w AS dir_2,
        lagInFrame(ti_p95_rolling, 0) OVER w AS ti_p95_prior,
        lagInFrame({feature_col_1}, 1) OVER w AS feature1_lag1,
        lagInFrame({feature_col_2}, 1) OVER w AS feature2_lag1,
        leadInFrame(open, 1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS entry_price
    FROM running_stats
    WINDOW w AS (ORDER BY timestamp_ms)
),
champion_signals AS (
    SELECT *
    FROM signal_detection
    WHERE dir_2 = 0 AND dir_1 = 0
      AND ti_1 > ti_p95_prior
      AND kyle_1 > 0
      AND rn > 1000
      AND ti_p95_prior IS NOT NULL
      AND ti_p95_prior > 0
      AND entry_price IS NOT NULL
      AND entry_price > 0
      AND feature1_lag1 IS NOT NULL
      AND feature2_lag1 IS NOT NULL
),
feature1_with_quantile AS (
    SELECT
        *,
        quantileExactExclusive({quantile_pct_1})(feature1_lag1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
        ) AS feature1_q
    FROM champion_signals
),
feature2_with_quantile AS (
    SELECT
        *,
        quantileExactExclusive({quantile_pct_2})(feature2_lag1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
        ) AS feature2_q
    FROM feature1_with_quantile
),
signals AS (
    SELECT *
    FROM feature2_with_quantile
    WHERE feature1_q IS NOT NULL
      AND feature2_q IS NOT NULL
      AND feature1_lag1 {direction_1} feature1_q
      AND feature2_lag1 {direction_2} feature2_q
),
forward_arrays AS (
    SELECT
        s.timestamp_ms,
        s.entry_price,
        s.rn AS signal_rn,
        groupArray(b.high) AS fwd_highs,
        groupArray(b.low) AS fwd_lows,
        groupArray(b.open) AS fwd_opens,
        groupArray(b.close) AS fwd_closes
    FROM signals s
    INNER JOIN base_bars b
        ON b.rn BETWEEN s.rn + 1 AND s.rn + 51
    GROUP BY s.timestamp_ms, s.entry_price, s.rn
),
param_with_prices AS (
    SELECT
        *,
        0.5 AS tp_mult,
        0.25 AS sl_mult,
        toUInt32(50) AS max_bars,
        entry_price * (1.0 + 0.5 * ({threshold} / 10000.0)) AS tp_price,
        entry_price * (1.0 - 0.25 * ({threshold} / 10000.0)) AS sl_price
    FROM forward_arrays
),
barrier_scan AS (
    SELECT
        timestamp_ms,
        entry_price,
        tp_mult,
        sl_mult,
        max_bars,
        tp_price,
        sl_price,
        fwd_opens,
        fwd_closes,
        length(fwd_highs) AS available_bars,
        arrayFirstIndex(x -> x >= tp_price, arraySlice(fwd_highs, 1, max_bars)) AS raw_tp_bar,
        arrayFirstIndex(x -> x <= sl_price, arraySlice(fwd_lows, 1, max_bars)) AS raw_sl_bar,
        length(arraySlice(fwd_highs, 1, max_bars)) AS window_bars
    FROM param_with_prices
),
trade_outcomes AS (
    SELECT
        timestamp_ms,
        entry_price,
        CASE
            WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_sl_bar <= raw_tp_bar THEN 'SL'
            WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_tp_bar < raw_sl_bar THEN 'TP'
            WHEN raw_sl_bar > 0 AND raw_tp_bar = 0 THEN 'SL'
            WHEN raw_tp_bar > 0 AND raw_sl_bar = 0 THEN 'TP'
            WHEN window_bars >= max_bars THEN 'TIME'
            ELSE 'INCOMPLETE'
        END AS exit_type,
        CASE
            WHEN raw_sl_bar > 0 AND (raw_tp_bar = 0 OR raw_sl_bar <= raw_tp_bar)
                THEN least(fwd_opens[raw_sl_bar], sl_price)
            WHEN raw_tp_bar > 0 AND (raw_sl_bar = 0 OR raw_tp_bar < raw_sl_bar)
                THEN tp_price
            WHEN window_bars >= max_bars
                THEN fwd_closes[max_bars]
            ELSE 0
        END AS exit_price
    FROM barrier_scan
)
SELECT
    '{config_id}' AS config_id,
    toUInt32(count(*)) AS n_trades,
    groupArray((exit_price - entry_price) / entry_price) AS returns,
    groupArray(timestamp_ms) AS timestamps_ms
FROM trade_outcomes
WHERE exit_type != 'INCOMPLETE'
"""


def generate_configs():
    """Generate all 1,008 2-feature configs (same as scripts/gen500/generate.sh)."""
    configs = []
    for i, j in itertools.combinations(range(len(FEATURES)), 2):
        f1, f2 = FEATURES[i], FEATURES[j]
        for q1, d1, s1 in GRID:
            for q2, d2, s2 in GRID:
                config_id = f"{f1}_{s1}__{f2}_{s2}"
                configs.append({
                    "config_id": config_id,
                    "feature_col_1": f1,
                    "feature_col_2": f2,
                    "quantile_pct_1": q1,
                    "quantile_pct_2": q2,
                    "direction_1": d1,
                    "direction_2": d2,
                })
    return configs


def run_query(client, config: dict) -> dict | None:
    """Execute trade-return SQL for one config, return result dict with arrays."""
    sql = SQL_TEMPLATE.format(
        symbol=SYMBOL,
        threshold=THRESHOLD_DBPS,
        **config,
    )
    try:
        result = client.query(sql)
        if not result.result_rows:
            return None
        row = result.result_rows[0]
        cols = result.column_names
        data = dict(zip(cols, row, strict=True))
        # Convert arrays to Python lists of floats/ints
        if "returns" in data and data["returns"] is not None:
            data["returns"] = [float(x) for x in data["returns"]]
        if "timestamps_ms" in data and data["timestamps_ms"] is not None:
            data["timestamps_ms"] = [int(x) for x in data["timestamps_ms"]]
        return data
    except (OSError, RuntimeError, ValueError) as e:
        print(f"  ERROR {config['config_id']}: {e}", file=sys.stderr)
        return None


def main():
    import clickhouse_connect

    from backtest.backtesting_py.ssh_tunnel import SSHTunnel

    configs = generate_configs()
    print(f"Generated {len(configs)} configs for {SYMBOL}@{THRESHOLD_DBPS}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    with SSHTunnel("bigblack") as local_port:
        client = clickhouse_connect.get_client(host="localhost", port=local_port)
        print(f"Connected via SSH tunnel on port {local_port}")

        with open(OUTPUT_FILE, "w") as f:
            for idx, config in enumerate(configs):
                result = run_query(client, config)
                if result is None:
                    result = {
                        "config_id": config["config_id"],
                        "n_trades": 0,
                        "returns": [],
                        "timestamps_ms": [],
                        "error": True,
                    }
                else:
                    result["error"] = False
                    # Ensure n_trades is int
                    result["n_trades"] = int(result["n_trades"])
                f.write(json.dumps(result) + "\n")

                if (idx + 1) % 50 == 0:
                    elapsed = time.time() - t0
                    rate = (idx + 1) / elapsed
                    eta = (len(configs) - idx - 1) / rate
                    print(f"  [{idx + 1}/{len(configs)}] {rate:.1f} q/s, ETA {eta:.0f}s")

    elapsed = time.time() - t0
    print(f"\nDone: {len(configs)} configs in {elapsed:.1f}s ({len(configs)/elapsed:.1f} q/s)")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
