-- GENERATION 4: TEMPORAL STABILITY ANALYSIS
-- Validate Gen2 top performers across years (2020-2025)
-- A truly robust pattern should work consistently across time

-- ti_p95_kyle_gt_0 per year
INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
WITH percentiles AS (
    SELECT
        quantile(0.95)(trade_intensity) as ti_p95
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
),
bars AS (
    SELECT
        timestamp_ms,
        toYear(fromUnixTimestamp64Milli(timestamp_ms)) as year,
        CASE WHEN close > open THEN 1 ELSE 0 END as direction,
        trade_intensity as ti, kyle_lambda_proxy as kyle
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
lagged AS (
    SELECT
        year,
        direction,
        lagInFrame(ti, 1) OVER w as ti_1,
        lagInFrame(kyle, 1) OVER w as kyle_1
    FROM bars
    WINDOW w AS (ORDER BY timestamp_ms)
)
SELECT
    'SOLUSDT',
    1000,
    concat('ti_p95_kyle_gt_0_Y', toString(year)),
    concat('ti_p95+kyle>0 in ', toString(year)),
    2,
    '{"trade_intensity": ">p95", "kyle_lambda": ">0"}',
    'long',
    1,
    count(*),
    countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0), 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0), 0) - 0.5,
    (countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0), 0) - 0.5) /
        sqrt(0.25 / countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0)),
    0.5, 0.5, 0.5,
    4
FROM lagged
WHERE ti_1 IS NOT NULL
GROUP BY year;

-- ti_p90_kyle_gt_0 per year (more samples)
INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
WITH percentiles AS (
    SELECT
        quantile(0.9)(trade_intensity) as ti_p90
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
),
bars AS (
    SELECT
        timestamp_ms,
        toYear(fromUnixTimestamp64Milli(timestamp_ms)) as year,
        CASE WHEN close > open THEN 1 ELSE 0 END as direction,
        trade_intensity as ti, kyle_lambda_proxy as kyle
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
lagged AS (
    SELECT
        year,
        direction,
        lagInFrame(ti, 1) OVER w as ti_1,
        lagInFrame(kyle, 1) OVER w as kyle_1
    FROM bars
    WINDOW w AS (ORDER BY timestamp_ms)
)
SELECT
    'SOLUSDT',
    1000,
    concat('ti_p90_kyle_gt_0_Y', toString(year)),
    concat('ti_p90+kyle>0 in ', toString(year)),
    2,
    '{"trade_intensity": ">p90", "kyle_lambda": ">0"}',
    'long',
    1,
    count(*),
    countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0), 0),
    countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0), 0) - 0.5,
    (countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0) /
        nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0), 0) - 0.5) /
        sqrt(0.25 / countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0)),
    0.5, 0.5, 0.5,
    4
FROM lagged
WHERE ti_1 IS NOT NULL
GROUP BY year;
