-- GENERATION 8: DIVERGENCE & COMPOSITE SIGNALS
-- Novel patterns combining Gen2 champion + Gen7 mean reversion insights
-- Also: OFI/Kyle divergence, intensity spikes without conviction

INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
WITH percentiles AS (
    SELECT
        quantile(0.9)(trade_intensity) as ti_p90,
        quantile(0.95)(trade_intensity) as ti_p95,
        quantile(0.9)(ofi) as ofi_p90,
        quantile(0.1)(ofi) as ofi_p10
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
        lagInFrame(kyle, 1) OVER w as kyle_1,
        lagInFrame(ofi, 1) OVER w as ofi_1,
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
    8 as generation
FROM (
    -- DIVERGENCE: OFI positive but Kyle negative (conflicting signals) → neutral/fade
    SELECT 'divergence_ofi_pos_kyle_neg' as combo_name,
           'OFI>0 but Kyle<0 (divergence) → SHORT' as combo_description,
           2 as n_features,
           '{"ofi(t-1)": ">0", "kyle_lambda(t-1)": "<0"}' as feature_conditions,
           'short' as signal_type,
           1 as lookback_bars,
           count(*) as total_bars,
           countIf(ofi_1 > 0 AND kyle_1 < 0) as signal_count,
           countIf(direction = 0 AND ofi_1 > 0 AND kyle_1 < 0) as hits,
           hits / nullIf(signal_count, 0) as hit_rate
    FROM lagged WHERE ofi_1 IS NOT NULL

    UNION ALL
    -- DIVERGENCE: OFI negative but Kyle positive → neutral/fade
    SELECT 'divergence_ofi_neg_kyle_pos',
           'OFI<0 but Kyle>0 (divergence) → LONG',
           2, '{"ofi(t-1)": "<0", "kyle_lambda(t-1)": ">0"}', 'long', 1, count(*),
           countIf(ofi_1 < 0 AND kyle_1 > 0),
           countIf(direction = 1 AND ofi_1 < 0 AND kyle_1 > 0),
           countIf(direction = 1 AND ofi_1 < 0 AND kyle_1 > 0) / nullIf(countIf(ofi_1 < 0 AND kyle_1 > 0), 0)
    FROM lagged WHERE ofi_1 IS NOT NULL

    UNION ALL
    -- INTENSITY WITHOUT CONVICTION: High intensity but Kyle near zero
    SELECT 'intensity_no_conviction_long',
           'High intensity + Kyle near 0 → LONG (volatility without direction)',
           2, '{"trade_intensity(t-1)": ">p90", "kyle_lambda(t-1)": "near 0"}', 'long', 1, count(*),
           countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND abs(kyle_1) < 0.0001),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND abs(kyle_1) < 0.0001),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND abs(kyle_1) < 0.0001) /
               nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND abs(kyle_1) < 0.0001), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    UNION ALL
    -- COMBO: Gen2 champion + Gen7 mean reversion (2 DOWN + ti_p95 + kyle>0)
    SELECT 'combo_2down_ti_p95_kyle_gt_0_long',
           'COMBO: 2 DOWN + ti>p95 + Kyle>0 → LONG (triple confirmation)',
           4, '{"direction(t-2,t-1)": "DOWN,DOWN", "trade_intensity(t-1)": ">p95", "kyle_lambda(t-1)": ">0"}', 'long', 2, count(*),
           countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0),
           countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0),
           countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0) /
               nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0), 0)
    FROM lagged WHERE dir_2 IS NOT NULL

    UNION ALL
    -- COMBO: Gen2 champion + Gen7 mean reversion (2 DOWN + ti_p90 + kyle>0)
    SELECT 'combo_2down_ti_p90_kyle_gt_0_long',
           'COMBO: 2 DOWN + ti>p90 + Kyle>0 → LONG (more samples)',
           4, '{"direction(t-2,t-1)": "DOWN,DOWN", "trade_intensity(t-1)": ">p90", "kyle_lambda(t-1)": ">0"}', 'long', 2, count(*),
           countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0),
           countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0),
           countIf(direction = 1 AND dir_2 = 0 AND dir_1 = 0 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0) /
               nullIf(countIf(dir_2 = 0 AND dir_1 = 0 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0), 0)
    FROM lagged WHERE dir_2 IS NOT NULL

    UNION ALL
    -- EXTREME OFI: Very high OFI + high intensity → momentum continuation
    SELECT 'extreme_ofi_ti_long',
           'OFI>p90 + ti>p90 → LONG (extreme buying pressure)',
           2, '{"ofi(t-1)": ">p90", "trade_intensity(t-1)": ">p90"}', 'long', 1, count(*),
           countIf(ofi_1 > (SELECT ofi_p90 FROM percentiles) AND ti_1 > (SELECT ti_p90 FROM percentiles)),
           countIf(direction = 1 AND ofi_1 > (SELECT ofi_p90 FROM percentiles) AND ti_1 > (SELECT ti_p90 FROM percentiles)),
           countIf(direction = 1 AND ofi_1 > (SELECT ofi_p90 FROM percentiles) AND ti_1 > (SELECT ti_p90 FROM percentiles)) /
               nullIf(countIf(ofi_1 > (SELECT ofi_p90 FROM percentiles) AND ti_1 > (SELECT ti_p90 FROM percentiles)), 0)
    FROM lagged WHERE ofi_1 IS NOT NULL

    UNION ALL
    -- EXTREME OFI: Very low OFI + high intensity → SHORT
    SELECT 'extreme_ofi_neg_ti_short',
           'OFI<p10 + ti>p90 → SHORT (extreme selling pressure)',
           2, '{"ofi(t-1)": "<p10", "trade_intensity(t-1)": ">p90"}', 'short', 1, count(*),
           countIf(ofi_1 < (SELECT ofi_p10 FROM percentiles) AND ti_1 > (SELECT ti_p90 FROM percentiles)),
           countIf(direction = 0 AND ofi_1 < (SELECT ofi_p10 FROM percentiles) AND ti_1 > (SELECT ti_p90 FROM percentiles)),
           countIf(direction = 0 AND ofi_1 < (SELECT ofi_p10 FROM percentiles) AND ti_1 > (SELECT ti_p90 FROM percentiles)) /
               nullIf(countIf(ofi_1 < (SELECT ofi_p10 FROM percentiles) AND ti_1 > (SELECT ti_p90 FROM percentiles)), 0)
    FROM lagged WHERE ofi_1 IS NOT NULL

    UNION ALL
    -- ALIGNMENT: All 3 signals agree (OFI>0, Kyle>0, last bar UP) → LONG continuation
    SELECT 'triple_alignment_long',
           'OFI>0 + Kyle>0 + dir=UP → LONG (all signals agree)',
           3, '{"ofi(t-1)": ">0", "kyle_lambda(t-1)": ">0", "direction(t-1)": "UP"}', 'long', 1, count(*),
           countIf(ofi_1 > 0 AND kyle_1 > 0 AND dir_1 = 1),
           countIf(direction = 1 AND ofi_1 > 0 AND kyle_1 > 0 AND dir_1 = 1),
           countIf(direction = 1 AND ofi_1 > 0 AND kyle_1 > 0 AND dir_1 = 1) /
               nullIf(countIf(ofi_1 > 0 AND kyle_1 > 0 AND dir_1 = 1), 0)
    FROM lagged WHERE ofi_1 IS NOT NULL

    UNION ALL
    -- ALIGNMENT: All 3 signals agree (OFI<0, Kyle<0, last bar DOWN) → SHORT continuation
    SELECT 'triple_alignment_short',
           'OFI<0 + Kyle<0 + dir=DOWN → SHORT (all signals agree)',
           3, '{"ofi(t-1)": "<0", "kyle_lambda(t-1)": "<0", "direction(t-1)": "DOWN"}', 'short', 1, count(*),
           countIf(ofi_1 < 0 AND kyle_1 < 0 AND dir_1 = 0),
           countIf(direction = 0 AND ofi_1 < 0 AND kyle_1 < 0 AND dir_1 = 0),
           countIf(direction = 0 AND ofi_1 < 0 AND kyle_1 < 0 AND dir_1 = 0) /
               nullIf(countIf(ofi_1 < 0 AND kyle_1 < 0 AND dir_1 = 0), 0)
    FROM lagged WHERE ofi_1 IS NOT NULL

    UNION ALL
    -- EXHAUSTION: After UP with negative Kyle → SHORT (buyers exhausted)
    SELECT 'exhaustion_up_kyle_neg_short',
           'UP bar + Kyle<0 → SHORT (buyer exhaustion)',
           2, '{"direction(t-1)": "UP", "kyle_lambda(t-1)": "<0"}', 'short', 1, count(*),
           countIf(dir_1 = 1 AND kyle_1 < 0),
           countIf(direction = 0 AND dir_1 = 1 AND kyle_1 < 0),
           countIf(direction = 0 AND dir_1 = 1 AND kyle_1 < 0) / nullIf(countIf(dir_1 = 1 AND kyle_1 < 0), 0)
    FROM lagged WHERE dir_1 IS NOT NULL

    UNION ALL
    -- EXHAUSTION: After DOWN with positive Kyle → LONG (sellers exhausted)
    SELECT 'exhaustion_down_kyle_pos_long',
           'DOWN bar + Kyle>0 → LONG (seller exhaustion)',
           2, '{"direction(t-1)": "DOWN", "kyle_lambda(t-1)": ">0"}', 'long', 1, count(*),
           countIf(dir_1 = 0 AND kyle_1 > 0),
           countIf(direction = 1 AND dir_1 = 0 AND kyle_1 > 0),
           countIf(direction = 1 AND dir_1 = 0 AND kyle_1 > 0) / nullIf(countIf(dir_1 = 0 AND kyle_1 > 0), 0)
    FROM lagged WHERE dir_1 IS NOT NULL
);
