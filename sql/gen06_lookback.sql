-- GENERATION 6: LOOKBACK PATTERNS (2-bar and 3-bar lag)
-- Novel hypothesis: Does the microstructure state 2-3 bars ago have predictive power?
-- If yes, this suggests momentum/mean-reversion regimes in microstructure

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
        trade_intensity as ti, kyle_lambda_proxy as kyle, ofi
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
lagged AS (
    SELECT
        direction,
        lagInFrame(ti, 1) OVER w as ti_1,
        lagInFrame(ti, 2) OVER w as ti_2,
        lagInFrame(ti, 3) OVER w as ti_3,
        lagInFrame(kyle, 1) OVER w as kyle_1,
        lagInFrame(kyle, 2) OVER w as kyle_2,
        lagInFrame(ofi, 1) OVER w as ofi_1,
        lagInFrame(ofi, 2) OVER w as ofi_2,
        lagInFrame(direction, 1) OVER w as dir_1,
        lagInFrame(direction, 2) OVER w as dir_2
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
    6 as generation
FROM (
    -- 2-bar lookback: High intensity persists → continuation
    SELECT 'ti_p95_lag2_kyle_gt_0_lag1' as combo_name,
           'High intensity 2 bars ago + Kyle>0 last bar → UP' as combo_description,
           2 as n_features,
           '{"trade_intensity(t-2)": ">p95", "kyle_lambda(t-1)": ">0"}' as feature_conditions,
           'long' as signal_type,
           2 as lookback_bars,
           count(*) as total_bars,
           countIf(ti_2 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0) as signal_count,
           countIf(direction = 1 AND ti_2 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0) as hits,
           hits / nullIf(signal_count, 0) as hit_rate
    FROM lagged WHERE ti_2 IS NOT NULL

    UNION ALL
    -- Intensity momentum: High intensity 2 bars ago AND last bar → strong continuation
    SELECT 'ti_p90_lag2_AND_ti_p90_lag1',
           'Consecutive high intensity bars → UP (momentum)',
           2, '{"trade_intensity(t-2)": ">p90", "trade_intensity(t-1)": ">p90"}', 'long', 2, count(*),
           countIf(ti_2 > (SELECT ti_p90 FROM percentiles) AND ti_1 > (SELECT ti_p90 FROM percentiles)),
           countIf(direction = 1 AND ti_2 > (SELECT ti_p90 FROM percentiles) AND ti_1 > (SELECT ti_p90 FROM percentiles)),
           countIf(direction = 1 AND ti_2 > (SELECT ti_p90 FROM percentiles) AND ti_1 > (SELECT ti_p90 FROM percentiles)) /
               nullIf(countIf(ti_2 > (SELECT ti_p90 FROM percentiles) AND ti_1 > (SELECT ti_p90 FROM percentiles)), 0)
    FROM lagged WHERE ti_2 IS NOT NULL

    UNION ALL
    -- Kyle momentum: Persistent positive Kyle → continuation
    SELECT 'kyle_gt_0_lag2_AND_kyle_gt_0_lag1',
           'Consecutive Kyle>0 → UP (momentum)',
           2, '{"kyle_lambda(t-2)": ">0", "kyle_lambda(t-1)": ">0"}', 'long', 2, count(*),
           countIf(kyle_2 > 0 AND kyle_1 > 0),
           countIf(direction = 1 AND kyle_2 > 0 AND kyle_1 > 0),
           countIf(direction = 1 AND kyle_2 > 0 AND kyle_1 > 0) / nullIf(countIf(kyle_2 > 0 AND kyle_1 > 0), 0)
    FROM lagged WHERE kyle_2 IS NOT NULL

    UNION ALL
    -- OFI momentum: Persistent positive OFI → continuation
    SELECT 'ofi_gt_0_lag2_AND_ofi_gt_0_lag1',
           'Consecutive OFI>0 → UP (momentum)',
           2, '{"ofi(t-2)": ">0", "ofi(t-1)": ">0"}', 'long', 2, count(*),
           countIf(ofi_2 > 0 AND ofi_1 > 0),
           countIf(direction = 1 AND ofi_2 > 0 AND ofi_1 > 0),
           countIf(direction = 1 AND ofi_2 > 0 AND ofi_1 > 0) / nullIf(countIf(ofi_2 > 0 AND ofi_1 > 0), 0)
    FROM lagged WHERE ofi_2 IS NOT NULL

    UNION ALL
    -- Reversal: Kyle flip from negative to positive → UP
    SELECT 'kyle_reversal_neg_to_pos',
           'Kyle flip: <0 two bars ago, >0 last bar → UP',
           2, '{"kyle_lambda(t-2)": "<0", "kyle_lambda(t-1)": ">0"}', 'long', 2, count(*),
           countIf(kyle_2 < 0 AND kyle_1 > 0),
           countIf(direction = 1 AND kyle_2 < 0 AND kyle_1 > 0),
           countIf(direction = 1 AND kyle_2 < 0 AND kyle_1 > 0) / nullIf(countIf(kyle_2 < 0 AND kyle_1 > 0), 0)
    FROM lagged WHERE kyle_2 IS NOT NULL

    UNION ALL
    -- Reversal: Kyle flip from positive to negative → DOWN
    SELECT 'kyle_reversal_pos_to_neg',
           'Kyle flip: >0 two bars ago, <0 last bar → DOWN',
           2, '{"kyle_lambda(t-2)": ">0", "kyle_lambda(t-1)": "<0"}', 'short', 2, count(*),
           countIf(kyle_2 > 0 AND kyle_1 < 0),
           countIf(direction = 0 AND kyle_2 > 0 AND kyle_1 < 0),
           countIf(direction = 0 AND kyle_2 > 0 AND kyle_1 < 0) / nullIf(countIf(kyle_2 > 0 AND kyle_1 < 0), 0)
    FROM lagged WHERE kyle_2 IS NOT NULL

    UNION ALL
    -- 3-bar lookback: Triple intensity confirmation
    SELECT 'ti_p90_3bar_streak',
           '3 consecutive high intensity bars → UP',
           3, '{"trade_intensity(t-3,t-2,t-1)": "all >p90"}', 'long', 3, count(*),
           countIf(ti_3 > (SELECT ti_p90 FROM percentiles) AND ti_2 > (SELECT ti_p90 FROM percentiles) AND ti_1 > (SELECT ti_p90 FROM percentiles)),
           countIf(direction = 1 AND ti_3 > (SELECT ti_p90 FROM percentiles) AND ti_2 > (SELECT ti_p90 FROM percentiles) AND ti_1 > (SELECT ti_p90 FROM percentiles)),
           countIf(direction = 1 AND ti_3 > (SELECT ti_p90 FROM percentiles) AND ti_2 > (SELECT ti_p90 FROM percentiles) AND ti_1 > (SELECT ti_p90 FROM percentiles)) /
               nullIf(countIf(ti_3 > (SELECT ti_p90 FROM percentiles) AND ti_2 > (SELECT ti_p90 FROM percentiles) AND ti_1 > (SELECT ti_p90 FROM percentiles)), 0)
    FROM lagged WHERE ti_3 IS NOT NULL

    UNION ALL
    -- Direction persistence: 2 UP bars + high intensity → continuation vs reversal
    SELECT 'dir_up_2bar_ti_p90',
           '2 consecutive UP bars + high intensity → UP',
           3, '{"direction(t-2)": "UP", "direction(t-1)": "UP", "trade_intensity(t-1)": ">p90"}', 'long', 2, count(*),
           countIf(dir_2 = 1 AND dir_1 = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles)),
           countIf(direction = 1 AND dir_2 = 1 AND dir_1 = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles)),
           countIf(direction = 1 AND dir_2 = 1 AND dir_1 = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles)) /
               nullIf(countIf(dir_2 = 1 AND dir_1 = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles)), 0)
    FROM lagged WHERE dir_2 IS NOT NULL

    UNION ALL
    -- Direction persistence: 2 DOWN bars + high intensity → continuation vs reversal
    SELECT 'dir_down_2bar_ti_p90',
           '2 consecutive DOWN bars + high intensity → DOWN',
           3, '{"direction(t-2)": "DOWN", "direction(t-1)": "DOWN", "trade_intensity(t-1)": ">p90"}', 'short', 2, count(*),
           countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > (SELECT ti_p90 FROM percentiles)),
           countIf(direction = 0 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > (SELECT ti_p90 FROM percentiles)),
           countIf(direction = 0 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > (SELECT ti_p90 FROM percentiles)) /
               nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > (SELECT ti_p90 FROM percentiles)), 0)
    FROM lagged WHERE dir_2 IS NOT NULL

    UNION ALL
    -- High intensity + direction confirmation
    SELECT 'ti_p95_lag1_dir_up_lag1',
           'High intensity + UP bar → UP (confirms momentum)',
           2, '{"trade_intensity(t-1)": ">p95", "direction(t-1)": "UP"}', 'long', 1, count(*),
           countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND dir_1 = 1),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND dir_1 = 1),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND dir_1 = 1) /
               nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND dir_1 = 1), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    UNION ALL
    -- High intensity + direction confirmation (SHORT)
    SELECT 'ti_p95_lag1_dir_down_lag1',
           'High intensity + DOWN bar → DOWN (confirms momentum)',
           2, '{"trade_intensity(t-1)": ">p95", "direction(t-1)": "DOWN"}', 'short', 1, count(*),
           countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND dir_1 = 0),
           countIf(direction = 0 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND dir_1 = 0),
           countIf(direction = 0 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND dir_1 = 0) /
               nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND dir_1 = 0), 0)
    FROM lagged WHERE ti_1 IS NOT NULL
);
