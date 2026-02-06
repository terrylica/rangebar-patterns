-- GENERATION 5: CROSS-ASSET VALIDATION
-- Test the champion pattern (ti_p95 + kyle>0) on BTC, ETH, BNB
-- If it works across assets, it's a structural market microstructure phenomenon

-- BTCUSDT
INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
WITH percentiles AS (
    SELECT quantile(0.95)(trade_intensity) as ti_p95
    FROM rangebar_cache.range_bars
    WHERE symbol = 'BTCUSDT' AND threshold_decimal_bps = 1000
),
bars AS (
    SELECT timestamp_ms, CASE WHEN close > open THEN 1 ELSE 0 END as direction,
           trade_intensity as ti, kyle_lambda_proxy as kyle
    FROM rangebar_cache.range_bars
    WHERE symbol = 'BTCUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
lagged AS (
    SELECT direction, lagInFrame(ti, 1) OVER w as ti_1, lagInFrame(kyle, 1) OVER w as kyle_1
    FROM bars WINDOW w AS (ORDER BY timestamp_ms)
)
SELECT
    'BTCUSDT', 1000, 'ti_p95_kyle_gt_0', 'BTC: Intensity>p95 AND Kyle>0 -> UP', 2,
    '{"trade_intensity": ">p95", "kyle_lambda": ">0"}', 'long', 1, count(*),
    countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0), 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0), 0) - 0.5,
    (countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0), 0) - 0.5) /
        sqrt(0.25 / countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0)),
    0.5, 0.5, 0.5, 5
FROM lagged WHERE ti_1 IS NOT NULL;

-- ETHUSDT
INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
WITH percentiles AS (
    SELECT quantile(0.95)(trade_intensity) as ti_p95
    FROM rangebar_cache.range_bars
    WHERE symbol = 'ETHUSDT' AND threshold_decimal_bps = 1000
),
bars AS (
    SELECT timestamp_ms, CASE WHEN close > open THEN 1 ELSE 0 END as direction,
           trade_intensity as ti, kyle_lambda_proxy as kyle
    FROM rangebar_cache.range_bars
    WHERE symbol = 'ETHUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
lagged AS (
    SELECT direction, lagInFrame(ti, 1) OVER w as ti_1, lagInFrame(kyle, 1) OVER w as kyle_1
    FROM bars WINDOW w AS (ORDER BY timestamp_ms)
)
SELECT
    'ETHUSDT', 1000, 'ti_p95_kyle_gt_0', 'ETH: Intensity>p95 AND Kyle>0 -> UP', 2,
    '{"trade_intensity": ">p95", "kyle_lambda": ">0"}', 'long', 1, count(*),
    countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0), 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0), 0) - 0.5,
    (countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0), 0) - 0.5) /
        sqrt(0.25 / countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0)),
    0.5, 0.5, 0.5, 5
FROM lagged WHERE ti_1 IS NOT NULL;

-- BNBUSDT
INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
WITH percentiles AS (
    SELECT quantile(0.95)(trade_intensity) as ti_p95
    FROM rangebar_cache.range_bars
    WHERE symbol = 'BNBUSDT' AND threshold_decimal_bps = 1000
),
bars AS (
    SELECT timestamp_ms, CASE WHEN close > open THEN 1 ELSE 0 END as direction,
           trade_intensity as ti, kyle_lambda_proxy as kyle
    FROM rangebar_cache.range_bars
    WHERE symbol = 'BNBUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
lagged AS (
    SELECT direction, lagInFrame(ti, 1) OVER w as ti_1, lagInFrame(kyle, 1) OVER w as kyle_1
    FROM bars WINDOW w AS (ORDER BY timestamp_ms)
)
SELECT
    'BNBUSDT', 1000, 'ti_p95_kyle_gt_0', 'BNB: Intensity>p95 AND Kyle>0 -> UP', 2,
    '{"trade_intensity": ">p95", "kyle_lambda": ">0"}', 'long', 1, count(*),
    countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0), 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0), 0) - 0.5,
    (countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0), 0) - 0.5) /
        sqrt(0.25 / countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0)),
    0.5, 0.5, 0.5, 5
FROM lagged WHERE ti_1 IS NOT NULL;

-- Also test p90 threshold for more samples
-- BTCUSDT p90
INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
WITH percentiles AS (
    SELECT quantile(0.9)(trade_intensity) as ti_p90
    FROM rangebar_cache.range_bars
    WHERE symbol = 'BTCUSDT' AND threshold_decimal_bps = 1000
),
bars AS (
    SELECT timestamp_ms, CASE WHEN close > open THEN 1 ELSE 0 END as direction,
           trade_intensity as ti, kyle_lambda_proxy as kyle
    FROM rangebar_cache.range_bars
    WHERE symbol = 'BTCUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
lagged AS (
    SELECT direction, lagInFrame(ti, 1) OVER w as ti_1, lagInFrame(kyle, 1) OVER w as kyle_1
    FROM bars WINDOW w AS (ORDER BY timestamp_ms)
)
SELECT
    'BTCUSDT', 1000, 'ti_p90_kyle_gt_0', 'BTC: Intensity>p90 AND Kyle>0 -> UP', 2,
    '{"trade_intensity": ">p90", "kyle_lambda": ">0"}', 'long', 1, count(*),
    countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0), 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0), 0) - 0.5,
    (countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0), 0) - 0.5) /
        sqrt(0.25 / countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0)),
    0.5, 0.5, 0.5, 5
FROM lagged WHERE ti_1 IS NOT NULL;

-- ETHUSDT p90
INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
WITH percentiles AS (
    SELECT quantile(0.9)(trade_intensity) as ti_p90
    FROM rangebar_cache.range_bars
    WHERE symbol = 'ETHUSDT' AND threshold_decimal_bps = 1000
),
bars AS (
    SELECT timestamp_ms, CASE WHEN close > open THEN 1 ELSE 0 END as direction,
           trade_intensity as ti, kyle_lambda_proxy as kyle
    FROM rangebar_cache.range_bars
    WHERE symbol = 'ETHUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
lagged AS (
    SELECT direction, lagInFrame(ti, 1) OVER w as ti_1, lagInFrame(kyle, 1) OVER w as kyle_1
    FROM bars WINDOW w AS (ORDER BY timestamp_ms)
)
SELECT
    'ETHUSDT', 1000, 'ti_p90_kyle_gt_0', 'ETH: Intensity>p90 AND Kyle>0 -> UP', 2,
    '{"trade_intensity": ">p90", "kyle_lambda": ">0"}', 'long', 1, count(*),
    countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0), 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0), 0) - 0.5,
    (countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0), 0) - 0.5) /
        sqrt(0.25 / countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0)),
    0.5, 0.5, 0.5, 5
FROM lagged WHERE ti_1 IS NOT NULL;

-- BNBUSDT p90
INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
WITH percentiles AS (
    SELECT quantile(0.9)(trade_intensity) as ti_p90
    FROM rangebar_cache.range_bars
    WHERE symbol = 'BNBUSDT' AND threshold_decimal_bps = 1000
),
bars AS (
    SELECT timestamp_ms, CASE WHEN close > open THEN 1 ELSE 0 END as direction,
           trade_intensity as ti, kyle_lambda_proxy as kyle
    FROM rangebar_cache.range_bars
    WHERE symbol = 'BNBUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
lagged AS (
    SELECT direction, lagInFrame(ti, 1) OVER w as ti_1, lagInFrame(kyle, 1) OVER w as kyle_1
    FROM bars WINDOW w AS (ORDER BY timestamp_ms)
)
SELECT
    'BNBUSDT', 1000, 'ti_p90_kyle_gt_0', 'BNB: Intensity>p90 AND Kyle>0 -> UP', 2,
    '{"trade_intensity": ">p90", "kyle_lambda": ">0"}', 'long', 1, count(*),
    countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0), 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0), 0) - 0.5,
    (countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0), 0) - 0.5) /
        sqrt(0.25 / countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0)),
    0.5, 0.5, 0.5, 5
FROM lagged WHERE ti_1 IS NOT NULL;

-- SOLUSDT (control - should match gen2)
INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
WITH percentiles AS (
    SELECT quantile(0.95)(trade_intensity) as ti_p95
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
),
bars AS (
    SELECT timestamp_ms, CASE WHEN close > open THEN 1 ELSE 0 END as direction,
           trade_intensity as ti, kyle_lambda_proxy as kyle
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
lagged AS (
    SELECT direction, lagInFrame(ti, 1) OVER w as ti_1, lagInFrame(kyle, 1) OVER w as kyle_1
    FROM bars WINDOW w AS (ORDER BY timestamp_ms)
)
SELECT
    'SOLUSDT', 1000, 'ti_p95_kyle_gt_0', 'SOL: Intensity>p95 AND Kyle>0 -> UP (control)', 2,
    '{"trade_intensity": ">p95", "kyle_lambda": ">0"}', 'long', 1, count(*),
    countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0), 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0), 0) - 0.5,
    (countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0), 0) - 0.5) /
        sqrt(0.25 / countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0)),
    0.5, 0.5, 0.5, 5
FROM lagged WHERE ti_1 IS NOT NULL;
