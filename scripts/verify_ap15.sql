-- AP-15 Verification: Extract champion signal timestamps + entry prices
-- Run on BigBlack: ssh bigblack 'clickhouse-client --query "$(cat scripts/verify_ap15.sql)"'
-- Compare against Python output from scripts/verify_ap15.py
--
-- Uses SOLUSDT @500 (most studied asset/threshold)
-- Champion pattern: 2 consecutive DOWN bars + ti > p95_rolling + kyle > 0

WITH
base_bars AS (
    SELECT
        timestamp_ms,
        open, high, low, close,
        trade_intensity,
        kyle_lambda_proxy,
        CASE WHEN close > open THEN 1 ELSE 0 END AS direction,
        row_number() OVER (ORDER BY timestamp_ms) AS rn
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT'
      AND threshold_decimal_bps = 500
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
        open, close,
        -- AP-15: current row IS the 2nd DOWN bar
        trade_intensity AS ti_0,
        kyle_lambda_proxy AS kyle_0,
        direction AS dir_0,
        lagInFrame(direction, 1) OVER w AS dir_1,
        lagInFrame(ti_p95_rolling, 0) OVER w AS ti_p95_prior,
        leadInFrame(open, 1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS entry_price,
        rn
    FROM running_stats
    WINDOW w AS (ORDER BY timestamp_ms)
),
champion_signals AS (
    SELECT *
    FROM signal_detection
    WHERE dir_1 = 0 AND dir_0 = 0
      AND ti_0 > ti_p95_prior
      AND kyle_0 > 0
      AND rn > 1000
      AND ti_p95_prior IS NOT NULL
      AND ti_p95_prior > 0
      AND entry_price IS NOT NULL
      AND entry_price > 0
)
SELECT
    timestamp_ms,
    open AS signal_open,
    close AS signal_close,
    entry_price,
    ti_0,
    ti_p95_prior,
    kyle_0,
    dir_0,
    dir_1
FROM champion_signals
ORDER BY timestamp_ms
FORMAT TabSeparatedWithNames;
