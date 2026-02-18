-- Gen600 Oracle: Per-trade output for udd__volume_per_trade_lt_p50__lookback_price_range_lt_p50
-- Symmetric barrier only (TP=0.50x, SL=0.50x, max_bars=50)
-- Symbol/threshold substituted by caller via sed
WITH
base_bars AS (
    SELECT
        timestamp_ms,
        open, high, low, close,
        trade_intensity,
        kyle_lambda_proxy,
        volume_per_trade,
        lookback_price_range,
        arraySlice(groupArray(high) OVER (
            ORDER BY timestamp_ms ROWS BETWEEN CURRENT ROW AND 101 FOLLOWING
        ), 2, 101) AS fwd_highs,
        arraySlice(groupArray(low) OVER (
            ORDER BY timestamp_ms ROWS BETWEEN CURRENT ROW AND 101 FOLLOWING
        ), 2, 101) AS fwd_lows,
        arraySlice(groupArray(open) OVER (
            ORDER BY timestamp_ms ROWS BETWEEN CURRENT ROW AND 101 FOLLOWING
        ), 2, 101) AS fwd_opens,
        arraySlice(groupArray(close) OVER (
            ORDER BY timestamp_ms ROWS BETWEEN CURRENT ROW AND 101 FOLLOWING
        ), 2, 101) AS fwd_closes,
        CASE WHEN close > open THEN 1 ELSE 0 END AS direction,
        row_number() OVER (ORDER BY timestamp_ms) AS rn
    FROM rangebar_cache.range_bars
    WHERE symbol = '__SYMBOL__'
      AND threshold_decimal_bps = __THRESHOLD__
      AND timestamp_ms <= 1738713600000
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
        trade_intensity AS ti_0,
        kyle_lambda_proxy AS kyle_0,
        direction AS dir_0,
        lagInFrame(direction, 1) OVER w AS dir_1,
        lagInFrame(direction, 2) OVER w AS dir_2,
        lagInFrame(ti_p95_rolling, 0) OVER w AS ti_p95_prior,
        volume_per_trade AS feature1_val,
        lookback_price_range AS feature2_val,
        leadInFrame(open, 1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS entry_price,
        fwd_highs, fwd_lows, fwd_opens, fwd_closes
    FROM running_stats
    WINDOW w AS (ORDER BY timestamp_ms)
),
champion_signals AS (
    SELECT *
    FROM signal_detection
    WHERE dir_2 = 1 AND dir_1 = 0 AND dir_0 = 0
      AND ti_0 > ti_p95_prior
      AND kyle_0 > 0
      AND rn > 1000
      AND ti_p95_prior IS NOT NULL
      AND ti_p95_prior > 0
      AND entry_price IS NOT NULL
      AND entry_price > 0
      AND feature1_val IS NOT NULL
      AND feature2_val IS NOT NULL
),
feature1_with_quantile AS (
    SELECT
        *,
        quantileExactExclusive(0.50)(feature1_val) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
        ) AS feature1_q
    FROM champion_signals
),
feature2_with_quantile AS (
    SELECT
        *,
        quantileExactExclusive(0.50)(feature2_val) OVER (
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
      AND feature1_val < feature1_q
      AND feature2_val < feature2_q
),
barrier_params AS (
    SELECT
        s.timestamp_ms,
        s.entry_price,
        s.entry_price * (1.0 + 5.0 * (__THRESHOLD__ / 100000.0)) AS tp_price,
        s.entry_price * (1.0 - 5.0 * (__THRESHOLD__ / 100000.0)) AS sl_price,
        toUInt32(50) AS max_bars,
        s.fwd_highs, s.fwd_lows, s.fwd_opens, s.fwd_closes
    FROM signals s
),
barrier_scan AS (
    SELECT
        timestamp_ms,
        entry_price,
        max_bars,
        tp_price,
        sl_price,
        fwd_opens,
        fwd_closes,
        length(fwd_highs) AS available_bars,
        arrayFirstIndex(x -> x >= tp_price, arraySlice(fwd_highs, 1, max_bars)) AS raw_tp_bar,
        arrayFirstIndex(x -> x <= sl_price, arraySlice(fwd_lows, 1, max_bars)) AS raw_sl_bar,
        length(arraySlice(fwd_highs, 1, max_bars)) AS window_bars
    FROM barrier_params
),
trade_outcomes AS (
    SELECT
        timestamp_ms,
        entry_price,
        tp_price,
        sl_price,
        CASE
            WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_sl_bar <= raw_tp_bar THEN 'SL'
            WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_tp_bar < raw_sl_bar THEN 'TP'
            WHEN raw_sl_bar > 0 AND raw_tp_bar = 0 THEN 'SL'
            WHEN raw_tp_bar > 0 AND raw_sl_bar = 0 THEN 'TP'
            WHEN window_bars >= max_bars THEN 'TIME'
            ELSE 'INCOMPLETE'
        END AS exit_type,
        CASE
            WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_sl_bar <= raw_tp_bar THEN raw_sl_bar
            WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_tp_bar < raw_sl_bar THEN raw_tp_bar
            WHEN raw_sl_bar > 0 AND raw_tp_bar = 0 THEN raw_sl_bar
            WHEN raw_tp_bar > 0 AND raw_sl_bar = 0 THEN raw_tp_bar
            WHEN window_bars >= max_bars THEN max_bars
            ELSE 0
        END AS exit_bar,
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
    timestamp_ms,
    entry_price,
    exit_type,
    exit_price,
    exit_bar
FROM trade_outcomes
WHERE exit_type != 'INCOMPLETE'
ORDER BY timestamp_ms
FORMAT TabSeparatedWithNames;
