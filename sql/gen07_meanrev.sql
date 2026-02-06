-- GENERATION 7: MEAN REVERSION PATTERNS (Based on Gen6 discovery)
-- Gen6 showed: Direction momentum → MEAN REVERSION (2 UP bars → DOWN)
-- This generation explores: optimal streak lengths, intensity filters for reversal

INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
WITH percentiles AS (
    SELECT
        quantile(0.9)(trade_intensity) as ti_p90,
        quantile(0.95)(trade_intensity) as ti_p95
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
),
bars AS (
    SELECT
        timestamp_ms,
        CASE WHEN close > open THEN 1 ELSE 0 END as direction,
        trade_intensity as ti, kyle_lambda_proxy as kyle
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
lagged AS (
    SELECT
        direction,
        lagInFrame(ti, 1) OVER w as ti_1,
        lagInFrame(kyle, 1) OVER w as kyle_1,
        lagInFrame(direction, 1) OVER w as dir_1,
        lagInFrame(direction, 2) OVER w as dir_2,
        lagInFrame(direction, 3) OVER w as dir_3,
        lagInFrame(direction, 4) OVER w as dir_4
    FROM bars
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
    7 as generation
FROM (
    -- MEAN REVERSION: 2 UP bars → SHORT (bet on DOWN) - INVERTED from Gen6 "long" signal
    SELECT 'meanrev_2up_short' as combo_name,
           '2 consecutive UP bars → SHORT (mean reversion)' as combo_description,
           1 as n_features,
           '{"direction(t-2,t-1)": "UP,UP"}' as feature_conditions,
           'short' as signal_type,
           2 as lookback_bars,
           count(*) as total_bars,
           countIf(dir_2 = 1 AND dir_1 = 1) as signal_count,
           countIf(direction = 0 AND dir_2 = 1 AND dir_1 = 1) as hits,
           hits / nullIf(signal_count, 0) as hit_rate
    FROM lagged WHERE dir_2 IS NOT NULL

    UNION ALL
    -- MEAN REVERSION: 2 DOWN bars → LONG (bet on UP)
    SELECT 'meanrev_2down_long',
           '2 consecutive DOWN bars → LONG (mean reversion)',
           1, '{"direction(t-2,t-1)": "DOWN,DOWN"}', 'long', 2, count(*),
           countIf(dir_2 = 0 AND dir_1 = 0),
           countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0),
           countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0) / nullIf(countIf(dir_2 = 0 AND dir_1 = 0), 0)
    FROM lagged WHERE dir_2 IS NOT NULL

    UNION ALL
    -- MEAN REVERSION: 3 UP bars → SHORT (stronger signal)
    SELECT 'meanrev_3up_short',
           '3 consecutive UP bars → SHORT (mean reversion)',
           1, '{"direction(t-3,t-2,t-1)": "UP,UP,UP"}', 'short', 3, count(*),
           countIf(dir_3 = 1 AND dir_2 = 1 AND dir_1 = 1),
           countIf(direction = 0 AND dir_3 = 1 AND dir_2 = 1 AND dir_1 = 1),
           countIf(direction = 0 AND dir_3 = 1 AND dir_2 = 1 AND dir_1 = 1) /
               nullIf(countIf(dir_3 = 1 AND dir_2 = 1 AND dir_1 = 1), 0)
    FROM lagged WHERE dir_3 IS NOT NULL

    UNION ALL
    -- MEAN REVERSION: 3 DOWN bars → LONG
    SELECT 'meanrev_3down_long',
           '3 consecutive DOWN bars → LONG (mean reversion)',
           1, '{"direction(t-3,t-2,t-1)": "DOWN,DOWN,DOWN"}', 'long', 3, count(*),
           countIf(dir_3 = 0 AND dir_2 = 0 AND dir_1 = 0),
           countIf(direction = 1 AND dir_3 = 0 AND dir_2 = 0 AND dir_1 = 0),
           countIf(direction = 1 AND dir_3 = 0 AND dir_2 = 0 AND dir_1 = 0) /
               nullIf(countIf(dir_3 = 0 AND dir_2 = 0 AND dir_1 = 0), 0)
    FROM lagged WHERE dir_3 IS NOT NULL

    UNION ALL
    -- MEAN REVERSION: 4 UP bars → SHORT (very strong signal)
    SELECT 'meanrev_4up_short',
           '4 consecutive UP bars → SHORT (mean reversion)',
           1, '{"direction(t-4,t-3,t-2,t-1)": "UP,UP,UP,UP"}', 'short', 4, count(*),
           countIf(dir_4 = 1 AND dir_3 = 1 AND dir_2 = 1 AND dir_1 = 1),
           countIf(direction = 0 AND dir_4 = 1 AND dir_3 = 1 AND dir_2 = 1 AND dir_1 = 1),
           countIf(direction = 0 AND dir_4 = 1 AND dir_3 = 1 AND dir_2 = 1 AND dir_1 = 1) /
               nullIf(countIf(dir_4 = 1 AND dir_3 = 1 AND dir_2 = 1 AND dir_1 = 1), 0)
    FROM lagged WHERE dir_4 IS NOT NULL

    UNION ALL
    -- MEAN REVERSION: 4 DOWN bars → LONG
    SELECT 'meanrev_4down_long',
           '4 consecutive DOWN bars → LONG (mean reversion)',
           1, '{"direction(t-4,t-3,t-2,t-1)": "DOWN,DOWN,DOWN,DOWN"}', 'long', 4, count(*),
           countIf(dir_4 = 0 AND dir_3 = 0 AND dir_2 = 0 AND dir_1 = 0),
           countIf(direction = 1 AND dir_4 = 0 AND dir_3 = 0 AND dir_2 = 0 AND dir_1 = 0),
           countIf(direction = 1 AND dir_4 = 0 AND dir_3 = 0 AND dir_2 = 0 AND dir_1 = 0) /
               nullIf(countIf(dir_4 = 0 AND dir_3 = 0 AND dir_2 = 0 AND dir_1 = 0), 0)
    FROM lagged WHERE dir_4 IS NOT NULL

    UNION ALL
    -- MEAN REVERSION with HIGH INTENSITY filter: 2 UP + high intensity → SHORT
    SELECT 'meanrev_2up_ti_p90_short',
           '2 UP bars + high intensity → SHORT (stronger reversal)',
           2, '{"direction(t-2,t-1)": "UP,UP", "trade_intensity(t-1)": ">p90"}', 'short', 2, count(*),
           countIf(dir_2 = 1 AND dir_1 = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles)),
           countIf(direction = 0 AND dir_2 = 1 AND dir_1 = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles)),
           countIf(direction = 0 AND dir_2 = 1 AND dir_1 = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles)) /
               nullIf(countIf(dir_2 = 1 AND dir_1 = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles)), 0)
    FROM lagged WHERE dir_2 IS NOT NULL

    UNION ALL
    -- MEAN REVERSION with HIGH INTENSITY filter: 2 DOWN + high intensity → LONG
    SELECT 'meanrev_2down_ti_p90_long',
           '2 DOWN bars + high intensity → LONG (stronger reversal)',
           2, '{"direction(t-2,t-1)": "DOWN,DOWN", "trade_intensity(t-1)": ">p90"}', 'long', 2, count(*),
           countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > (SELECT ti_p90 FROM percentiles)),
           countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > (SELECT ti_p90 FROM percentiles)),
           countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > (SELECT ti_p90 FROM percentiles)) /
               nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > (SELECT ti_p90 FROM percentiles)), 0)
    FROM lagged WHERE dir_2 IS NOT NULL

    UNION ALL
    -- MEAN REVERSION with KYLE filter: 2 UP + Kyle<0 → SHORT (Kyle disagrees with momentum)
    SELECT 'meanrev_2up_kyle_lt_0_short',
           '2 UP bars + Kyle<0 → SHORT (exhaustion signal)',
           2, '{"direction(t-2,t-1)": "UP,UP", "kyle_lambda(t-1)": "<0"}', 'short', 2, count(*),
           countIf(dir_2 = 1 AND dir_1 = 1 AND kyle_1 < 0),
           countIf(direction = 0 AND dir_2 = 1 AND dir_1 = 1 AND kyle_1 < 0),
           countIf(direction = 0 AND dir_2 = 1 AND dir_1 = 1 AND kyle_1 < 0) /
               nullIf(countIf(dir_2 = 1 AND dir_1 = 1 AND kyle_1 < 0), 0)
    FROM lagged WHERE dir_2 IS NOT NULL

    UNION ALL
    -- MEAN REVERSION with KYLE filter: 2 DOWN + Kyle>0 → LONG (Kyle disagrees with momentum)
    SELECT 'meanrev_2down_kyle_gt_0_long',
           '2 DOWN bars + Kyle>0 → LONG (exhaustion signal)',
           2, '{"direction(t-2,t-1)": "DOWN,DOWN", "kyle_lambda(t-1)": ">0"}', 'long', 2, count(*),
           countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0),
           countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0),
           countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0) /
               nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND kyle_1 > 0), 0)
    FROM lagged WHERE dir_2 IS NOT NULL

    UNION ALL
    -- Single alternating: Last bar UP → SHORT (simple mean reversion)
    SELECT 'single_up_short',
           'Last bar UP → SHORT (simple mean reversion)',
           1, '{"direction(t-1)": "UP"}', 'short', 1, count(*),
           countIf(dir_1 = 1),
           countIf(direction = 0 AND dir_1 = 1),
           countIf(direction = 0 AND dir_1 = 1) / nullIf(countIf(dir_1 = 1), 0)
    FROM lagged WHERE dir_1 IS NOT NULL

    UNION ALL
    -- Single alternating: Last bar DOWN → LONG (simple mean reversion)
    SELECT 'single_down_long',
           'Last bar DOWN → LONG (simple mean reversion)',
           1, '{"direction(t-1)": "DOWN"}', 'long', 1, count(*),
           countIf(dir_1 = 0),
           countIf(direction = 1 AND dir_1 = 0),
           countIf(direction = 1 AND dir_1 = 0) / nullIf(countIf(dir_1 = 0), 0)
    FROM lagged WHERE dir_1 IS NOT NULL
);
