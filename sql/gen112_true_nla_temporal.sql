-- TRUE NO-LOOKAHEAD TEMPORAL STABILITY
-- Check year-by-year performance with proper expanding-window percentiles
-- Generation 112: Temporal stability check

-- ============================================================================
-- Full pattern by year: 2DOWN + ti>p95_expanding + kyle>0
-- ============================================================================

INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
WITH
base_bars AS (
    SELECT
        timestamp_ms,
        toYear(fromUnixTimestamp64Milli(timestamp_ms)) as year,
        CASE WHEN close > open THEN 1 ELSE 0 END as direction,
        trade_intensity,
        kyle_lambda_proxy
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
running_stats AS (
    SELECT
        timestamp_ms,
        year,
        direction,
        trade_intensity,
        kyle_lambda_proxy,
        count(*) OVER (ORDER BY timestamp_ms ROWS UNBOUNDED PRECEDING) as bar_count,
        quantileExactExclusive(0.95)(trade_intensity) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) as ti_p95_expanding
    FROM base_bars
),
lagged AS (
    SELECT
        timestamp_ms,
        year,
        direction,
        lagInFrame(trade_intensity, 1) OVER w as ti_1,
        lagInFrame(kyle_lambda_proxy, 1) OVER w as kyle_1,
        lagInFrame(direction, 1) OVER w as dir_1,
        lagInFrame(direction, 2) OVER w as dir_2,
        ti_p95_expanding as ti_p95_prior,
        bar_count
    FROM running_stats
    WINDOW w AS (ORDER BY timestamp_ms)
)
SELECT
    'SOLUSDT', 1000,
    concat('true_nla_combo_Y', toString(year)),
    concat('TRUE NLA: 2DOWN+ti>p95+kyle>0 in ', toString(year)),
    4,
    '{"direction(t-2,t-1)": "DOWN,DOWN", "trade_intensity(t-1)": ">p95_expanding", "kyle_lambda(t-1)": ">0"}',
    'long', 2,
    count(*),
    countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0),
    countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0),
    countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0) /
        nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0), 0),
    countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0) /
        nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0), 0) - 0.5,
    (countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0) /
        nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0), 0) - 0.5) /
        sqrt(0.25 / nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0), 0)),
    0.5, 0.5, 0.5,
    112
FROM lagged
WHERE dir_2 IS NOT NULL
  AND ti_p95_prior IS NOT NULL
  AND ti_p95_prior > 0
  AND bar_count > 1000
GROUP BY year;

-- ============================================================================
-- Simple pattern by year: 2DOWN + kyle>0 (no percentile - inherently no lookahead)
-- ============================================================================

INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
WITH
bars AS (
    SELECT
        timestamp_ms,
        toYear(fromUnixTimestamp64Milli(timestamp_ms)) as year,
        CASE WHEN close > open THEN 1 ELSE 0 END as direction,
        kyle_lambda_proxy as kyle
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
lagged AS (
    SELECT
        year,
        direction,
        lagInFrame(kyle, 1) OVER w as kyle_1,
        lagInFrame(direction, 1) OVER w as dir_1,
        lagInFrame(direction, 2) OVER w as dir_2
    FROM bars
    WINDOW w AS (ORDER BY timestamp_ms)
)
SELECT
    'SOLUSDT', 1000,
    concat('true_nla_simple_Y', toString(year)),
    concat('TRUE NLA: 2DOWN+kyle>0 in ', toString(year)),
    3,
    '{"direction(t-2,t-1)": "DOWN,DOWN", "kyle_lambda(t-1)": ">0"}',
    'long', 2,
    count(*),
    countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0),
    countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0),
    countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0) /
        nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0), 0),
    countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0) /
        nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0), 0) - 0.5,
    (countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0) /
        nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0), 0) - 0.5) /
        sqrt(0.25 / countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0)),
    0.5, 0.5, 0.5,
    112
FROM lagged
WHERE dir_2 IS NOT NULL
GROUP BY year;
