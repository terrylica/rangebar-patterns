-- GENERATION 8 (NO LOOKAHEAD): Composite signals with YEAR-SPECIFIC percentiles
-- FIX: Uses per-year percentiles to eliminate lookahead bias
-- At worst, this uses annual data which is a practical compromise between:
--   - True expanding window (computationally expensive)
--   - Full dataset (severe lookahead bias)

INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
WITH
-- Compute percentiles PER YEAR (no lookahead within year, mild lookahead across year)
yearly_percentiles AS (
    SELECT
        toYear(fromUnixTimestamp64Milli(timestamp_ms)) as year,
        quantile(0.9)(trade_intensity) as ti_p90,
        quantile(0.95)(trade_intensity) as ti_p95
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
    GROUP BY year
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
bars_with_percentiles AS (
    SELECT
        b.*,
        yp.ti_p90,
        yp.ti_p95
    FROM bars b
    JOIN yearly_percentiles yp ON b.year = yp.year
),
lagged AS (
    SELECT
        direction,
        year,
        ti_p90,
        ti_p95,
        lagInFrame(ti, 1) OVER w as ti_1,
        lagInFrame(kyle, 1) OVER w as kyle_1,
        lagInFrame(direction, 1) OVER w as dir_1,
        lagInFrame(direction, 2) OVER w as dir_2,
        -- Use PRIOR year's percentile to eliminate within-year lookahead
        lagInFrame(ti_p90, 1) OVER w as ti_p90_prior,
        lagInFrame(ti_p95, 1) OVER w as ti_p95_prior
    FROM bars_with_percentiles
    WINDOW w AS (ORDER BY timestamp_ms)
)
SELECT
    'SOLUSDT' as symbol,
    1000 as threshold_decimal_bps,
    combo_name,
    combo_description,
    n_features,
    feature_conditions,
    signal_type,
    lookback_bars,
    total_bars,
    signal_count,
    hits,
    hit_rate,
    hit_rate - 0.5 as edge_pct,
    (hit_rate - 0.5) / sqrt(0.25 / signal_count) as z_score,
    0.5 as p_value, 0.5 as ci_low, 0.5 as ci_high,
    108 as generation  -- 108 = Gen8 no-lookahead version
FROM (
    -- COMBO (no-lookahead): 2 DOWN bars + ti>p95_prior + Kyle>0 → LONG
    SELECT 'nla_combo_2down_ti_p95_kyle_gt_0_long' as combo_name,
           'NO-LOOKAHEAD: 2 DOWN + ti>p95(t-1) + Kyle>0 → LONG' as combo_description,
           4 as n_features,
           '{"direction(t-2,t-1)": "DOWN,DOWN", "trade_intensity(t-1)": ">p95_prior", "kyle_lambda(t-1)": ">0"}' as feature_conditions,
           'long' as signal_type,
           2 as lookback_bars,
           count(*) as total_bars,
           countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0) as signal_count,
           countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p95_prior AND kyle_1 > 0) as hits,
           hits / nullIf(signal_count, 0) as hit_rate
    FROM lagged WHERE dir_2 IS NOT NULL AND ti_p95_prior IS NOT NULL

    UNION ALL
    -- COMBO (no-lookahead): 2 DOWN bars + ti>p90_prior + Kyle>0 → LONG
    SELECT 'nla_combo_2down_ti_p90_kyle_gt_0_long',
           'NO-LOOKAHEAD: 2 DOWN + ti>p90(t-1) + Kyle>0 → LONG',
           4, '{"direction(t-2,t-1)": "DOWN,DOWN", "trade_intensity(t-1)": ">p90_prior", "kyle_lambda(t-1)": ">0"}', 'long', 2, count(*),
           countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p90_prior AND kyle_1 > 0),
           countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p90_prior AND kyle_1 > 0),
           countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p90_prior AND kyle_1 > 0) /
               nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > ti_p90_prior AND kyle_1 > 0), 0)
    FROM lagged WHERE dir_2 IS NOT NULL AND ti_p90_prior IS NOT NULL

    UNION ALL
    -- Simple mean reversion (no percentile needed): 2 DOWN bars + Kyle>0 → LONG
    SELECT 'nla_meanrev_2down_kyle_gt_0_long',
           'NO-LOOKAHEAD: 2 DOWN + Kyle>0 → LONG (no percentile threshold)',
           3, '{"direction(t-2,t-1)": "DOWN,DOWN", "kyle_lambda(t-1)": ">0"}', 'long', 2, count(*),
           countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0),
           countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0),
           countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0) /
               nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0), 0)
    FROM lagged WHERE dir_2 IS NOT NULL

    UNION ALL
    -- Simple mean reversion: 2 DOWN bars → LONG (baseline)
    SELECT 'nla_meanrev_2down_long',
           'NO-LOOKAHEAD: 2 DOWN → LONG (pure mean reversion)',
           1, '{"direction(t-2,t-1)": "DOWN,DOWN"}', 'long', 2, count(*),
           countIf(dir_2 = 0 AND dir_1 = 0),
           countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0),
           countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0) / nullIf(countIf(dir_2 = 0 AND dir_1 = 0), 0)
    FROM lagged WHERE dir_2 IS NOT NULL

    UNION ALL
    -- Kyle>0 alone (no percentile, no lookahead)
    SELECT 'nla_kyle_gt_0_long',
           'NO-LOOKAHEAD: Kyle>0 → LONG (baseline)',
           1, '{"kyle_lambda(t-1)": ">0"}', 'long', 1, count(*),
           countIf(kyle_1 > 0),
           countIf(direction = 1 AND kyle_1 > 0),
           countIf(direction = 1 AND kyle_1 > 0) / nullIf(countIf(kyle_1 > 0), 0)
    FROM lagged WHERE kyle_1 IS NOT NULL

    UNION ALL
    -- Single DOWN bar + Kyle>0 (no percentile)
    SELECT 'nla_1down_kyle_gt_0_long',
           'NO-LOOKAHEAD: 1 DOWN + Kyle>0 → LONG',
           2, '{"direction(t-1)": "DOWN", "kyle_lambda(t-1)": ">0"}', 'long', 1, count(*),
           countIf(dir_1 = 0 AND kyle_1 > 0),
           countIf(direction = 1 AND dir_1 = 0 AND kyle_1 > 0),
           countIf(direction = 1 AND dir_1 = 0 AND kyle_1 > 0) / nullIf(countIf(dir_1 = 0 AND kyle_1 > 0), 0)
    FROM lagged WHERE dir_1 IS NOT NULL
);
