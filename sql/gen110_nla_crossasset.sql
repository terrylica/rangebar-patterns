-- NO-LOOKAHEAD CROSS-ASSET VALIDATION
-- Test the champion pattern on BTC and BNB using prior-year percentiles
-- Also test the simpler pattern (2 DOWN + kyle>0) which has no percentile

-- BTCUSDT with prior-year percentiles
INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
WITH
yearly_percentiles AS (
    SELECT
        toYear(fromUnixTimestamp64Milli(timestamp_ms)) as year,
        quantile(0.95)(trade_intensity) as ti_p95
    FROM rangebar_cache.range_bars
    WHERE symbol = 'BTCUSDT' AND threshold_decimal_bps = 1000
    GROUP BY year
),
bars AS (
    SELECT timestamp_ms, toYear(fromUnixTimestamp64Milli(timestamp_ms)) as year,
           CASE WHEN close > open THEN 1 ELSE 0 END as direction,
           trade_intensity as ti, kyle_lambda_proxy as kyle
    FROM rangebar_cache.range_bars
    WHERE symbol = 'BTCUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
bars_with_percentiles AS (
    SELECT b.*, yp.ti_p95
    FROM bars b JOIN yearly_percentiles yp ON b.year = yp.year
),
lagged AS (
    SELECT direction, lagInFrame(ti, 1) OVER w as ti_1, lagInFrame(kyle, 1) OVER w as kyle_1,
           lagInFrame(direction, 1) OVER w as dir_1, lagInFrame(direction, 2) OVER w as dir_2,
           lagInFrame(ti_p95, 1) OVER w as ti_p95_prior
    FROM bars_with_percentiles WINDOW w AS (ORDER BY timestamp_ms)
)
SELECT 'BTCUSDT', 1000, 'nla_combo_2down_ti_p95_kyle_gt_0_long',
       'BTC: NO-LOOKAHEAD 2DOWN+ti>p95+kyle>0 → LONG', 4,
       '{"direction(t-2,t-1)": "DOWN,DOWN", "trade_intensity(t-1)": ">p95_prior", "kyle_lambda(t-1)": ">0"}',
       'long', 2, count(*),
       countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0),
       countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0),
       countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0) /
           nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0), 0),
       countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0) /
           nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0), 0) - 0.5,
       (countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0) /
           nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0), 0) - 0.5) /
           sqrt(0.25 / countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0)),
       0.5, 0.5, 0.5, 110
FROM lagged WHERE dir_2 IS NOT NULL AND ti_p95_prior IS NOT NULL;

-- BTCUSDT simple pattern (no percentile)
INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
WITH
bars AS (
    SELECT timestamp_ms, CASE WHEN close > open THEN 1 ELSE 0 END as direction,
           kyle_lambda_proxy as kyle
    FROM rangebar_cache.range_bars
    WHERE symbol = 'BTCUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
lagged AS (
    SELECT direction, lagInFrame(kyle, 1) OVER w as kyle_1,
           lagInFrame(direction, 1) OVER w as dir_1, lagInFrame(direction, 2) OVER w as dir_2
    FROM bars WINDOW w AS (ORDER BY timestamp_ms)
)
SELECT 'BTCUSDT', 1000, 'nla_2down_kyle_gt_0_long',
       'BTC: NO-LOOKAHEAD 2DOWN+kyle>0 → LONG', 3,
       '{"direction(t-2,t-1)": "DOWN,DOWN", "kyle_lambda(t-1)": ">0"}', 'long', 2, count(*),
       countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0),
       countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0),
       countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0) /
           nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0), 0),
       countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0) /
           nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0), 0) - 0.5,
       (countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0) /
           nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0), 0) - 0.5) /
           sqrt(0.25 / countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0)),
       0.5, 0.5, 0.5, 110
FROM lagged WHERE dir_2 IS NOT NULL;

-- BNBUSDT with prior-year percentiles
INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
WITH
yearly_percentiles AS (
    SELECT
        toYear(fromUnixTimestamp64Milli(timestamp_ms)) as year,
        quantile(0.95)(trade_intensity) as ti_p95
    FROM rangebar_cache.range_bars
    WHERE symbol = 'BNBUSDT' AND threshold_decimal_bps = 1000
    GROUP BY year
),
bars AS (
    SELECT timestamp_ms, toYear(fromUnixTimestamp64Milli(timestamp_ms)) as year,
           CASE WHEN close > open THEN 1 ELSE 0 END as direction,
           trade_intensity as ti, kyle_lambda_proxy as kyle
    FROM rangebar_cache.range_bars
    WHERE symbol = 'BNBUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
bars_with_percentiles AS (
    SELECT b.*, yp.ti_p95
    FROM bars b JOIN yearly_percentiles yp ON b.year = yp.year
),
lagged AS (
    SELECT direction, lagInFrame(ti, 1) OVER w as ti_1, lagInFrame(kyle, 1) OVER w as kyle_1,
           lagInFrame(direction, 1) OVER w as dir_1, lagInFrame(direction, 2) OVER w as dir_2,
           lagInFrame(ti_p95, 1) OVER w as ti_p95_prior
    FROM bars_with_percentiles WINDOW w AS (ORDER BY timestamp_ms)
)
SELECT 'BNBUSDT', 1000, 'nla_combo_2down_ti_p95_kyle_gt_0_long',
       'BNB: NO-LOOKAHEAD 2DOWN+ti>p95+kyle>0 → LONG', 4,
       '{"direction(t-2,t-1)": "DOWN,DOWN", "trade_intensity(t-1)": ">p95_prior", "kyle_lambda(t-1)": ">0"}',
       'long', 2, count(*),
       countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0),
       countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0),
       countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0) /
           nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0), 0),
       countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0) /
           nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0), 0) - 0.5,
       (countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0) /
           nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0), 0) - 0.5) /
           sqrt(0.25 / countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0)),
       0.5, 0.5, 0.5, 110
FROM lagged WHERE dir_2 IS NOT NULL AND ti_p95_prior IS NOT NULL;

-- BNBUSDT simple pattern (no percentile)
INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
WITH
bars AS (
    SELECT timestamp_ms, CASE WHEN close > open THEN 1 ELSE 0 END as direction,
           kyle_lambda_proxy as kyle
    FROM rangebar_cache.range_bars
    WHERE symbol = 'BNBUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
lagged AS (
    SELECT direction, lagInFrame(kyle, 1) OVER w as kyle_1,
           lagInFrame(direction, 1) OVER w as dir_1, lagInFrame(direction, 2) OVER w as dir_2
    FROM bars WINDOW w AS (ORDER BY timestamp_ms)
)
SELECT 'BNBUSDT', 1000, 'nla_2down_kyle_gt_0_long',
       'BNB: NO-LOOKAHEAD 2DOWN+kyle>0 → LONG', 3,
       '{"direction(t-2,t-1)": "DOWN,DOWN", "kyle_lambda(t-1)": ">0"}', 'long', 2, count(*),
       countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0),
       countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0),
       countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0) /
           nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0), 0),
       countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0) /
           nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0), 0) - 0.5,
       (countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0) /
           nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0), 0) - 0.5) /
           sqrt(0.25 / countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0)),
       0.5, 0.5, 0.5, 110
FROM lagged WHERE dir_2 IS NOT NULL;

-- SOL control (should match gen108)
INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
WITH
bars AS (
    SELECT timestamp_ms, CASE WHEN close > open THEN 1 ELSE 0 END as direction,
           kyle_lambda_proxy as kyle
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
lagged AS (
    SELECT direction, lagInFrame(kyle, 1) OVER w as kyle_1,
           lagInFrame(direction, 1) OVER w as dir_1, lagInFrame(direction, 2) OVER w as dir_2
    FROM bars WINDOW w AS (ORDER BY timestamp_ms)
)
SELECT 'SOLUSDT', 1000, 'nla_2down_kyle_gt_0_long',
       'SOL: NO-LOOKAHEAD 2DOWN+kyle>0 → LONG (control)', 3,
       '{"direction(t-2,t-1)": "DOWN,DOWN", "kyle_lambda(t-1)": ">0"}', 'long', 2, count(*),
       countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0),
       countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0),
       countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0) /
           nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0), 0),
       countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0) /
           nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0), 0) - 0.5,
       (countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0) /
           nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0), 0) - 0.5) /
           sqrt(0.25 / countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0)),
       0.5, 0.5, 0.5, 110
FROM lagged WHERE dir_2 IS NOT NULL;
