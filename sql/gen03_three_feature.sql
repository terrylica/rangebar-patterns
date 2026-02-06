-- GENERATION 3: Three-feature combinations + temporal stability
-- Focus on best Gen2 performers: ti_p95 + kyle>0 is the anchor

WITH percentiles AS (
    SELECT
        quantile(0.8)(trade_intensity) as ti_p80,
        quantile(0.9)(trade_intensity) as ti_p90,
        quantile(0.95)(trade_intensity) as ti_p95,
        quantile(0.9)(kyle_lambda_proxy) as kyle_p90,
        quantile(0.9)(ofi) as ofi_p90,
        quantile(0.9)(turnover_imbalance) as ti_imb_p90,
        quantile(0.9)(price_impact) as pi_p90,
        quantile(0.9)(aggression_ratio) as agg_p90
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
),
bars AS (
    SELECT
        timestamp_ms,
        toYear(fromUnixTimestamp64Milli(timestamp_ms)) as year,
        CASE WHEN close > open THEN 1 ELSE 0 END as direction,
        ofi, trade_intensity as ti, kyle_lambda_proxy as kyle, price_impact as pi,
        turnover_imbalance as ti_imb, aggression_ratio as agg
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
lagged AS (
    SELECT
        year,
        direction,
        lagInFrame(ofi, 1) OVER w as ofi_1,
        lagInFrame(ti, 1) OVER w as ti_1,
        lagInFrame(kyle, 1) OVER w as kyle_1,
        lagInFrame(pi, 1) OVER w as pi_1,
        lagInFrame(ti_imb, 1) OVER w as ti_imb_1,
        lagInFrame(agg, 1) OVER w as agg_1
    FROM bars
    WINDOW w AS (ORDER BY timestamp_ms)
)
INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
SELECT
    'SOLUSDT' as symbol,
    1000 as threshold_decimal_bps,
    combo_name,
    combo_description,
    n_features,
    feature_conditions,
    signal_type,
    1 as lookback_bars,
    total_bars,
    signal_count,
    hits,
    hit_rate,
    hit_rate - 0.5 as edge_pct,
    (hit_rate - 0.5) / sqrt(0.25 / signal_count) as z_score,
    1 - 0.5 * (1 + erf((hit_rate - 0.5) / sqrt(0.25 / signal_count) / sqrt(2))) as p_value,
    hit_rate - 1.96 * sqrt(hit_rate * (1 - hit_rate) / signal_count) as ci_low,
    hit_rate + 1.96 * sqrt(hit_rate * (1 - hit_rate) / signal_count) as ci_high,
    3 as generation
FROM (
    -- 3-feature: ti_p95 + kyle>0 + ofi>0 (add OFI direction)
    SELECT 'ti_p95_kyle_gt_0_ofi_gt_0' as combo_name,
           'Intensity>p95 AND Kyle>0 AND OFI>0 -> UP (triple confirm)' as combo_description,
           3 as n_features,
           '{"trade_intensity": ">p95", "kyle_lambda": ">0", "ofi": ">0"}' as feature_conditions,
           'long' as signal_type,
           count(*) as total_bars,
           countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0 AND ofi_1 > 0) as signal_count,
           countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0 AND ofi_1 > 0) as hits,
           hits / nullIf(signal_count, 0) as hit_rate
    FROM lagged WHERE ti_1 IS NOT NULL

    UNION ALL
    -- 3-feature: ti_p95 + kyle>0 + agg>p90 (add aggression filter)
    SELECT 'ti_p95_kyle_gt_0_agg_gt_p90',
           'Intensity>p95 AND Kyle>0 AND Aggression>p90 -> UP',
           3, '{"trade_intensity": ">p95", "kyle_lambda": ">0", "aggression_ratio": ">p90"}', 'long', count(*),
           countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0 AND agg_1 > (SELECT agg_p90 FROM percentiles)),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0 AND agg_1 > (SELECT agg_p90 FROM percentiles)),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0 AND agg_1 > (SELECT agg_p90 FROM percentiles)) /
               nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0 AND agg_1 > (SELECT agg_p90 FROM percentiles)), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    UNION ALL
    -- 3-feature: ti_p95 + kyle>0 + ti_imb>0 (add turnover direction)
    SELECT 'ti_p95_kyle_gt_0_ti_imb_gt_0',
           'Intensity>p95 AND Kyle>0 AND TurnoverImb>0 -> UP',
           3, '{"trade_intensity": ">p95", "kyle_lambda": ">0", "turnover_imbalance": ">0"}', 'long', count(*),
           countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0 AND ti_imb_1 > 0),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0 AND ti_imb_1 > 0),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0 AND ti_imb_1 > 0) /
               nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0 AND ti_imb_1 > 0), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    UNION ALL
    -- 3-feature: ti_p95 + kyle>0 + pi>p90 (add price impact filter)
    SELECT 'ti_p95_kyle_gt_0_pi_gt_p90',
           'Intensity>p95 AND Kyle>0 AND PriceImpact>p90 -> UP',
           3, '{"trade_intensity": ">p95", "kyle_lambda": ">0", "price_impact": ">p90"}', 'long', count(*),
           countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0 AND pi_1 > (SELECT pi_p90 FROM percentiles)),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0 AND pi_1 > (SELECT pi_p90 FROM percentiles)),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0 AND pi_1 > (SELECT pi_p90 FROM percentiles)) /
               nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0 AND pi_1 > (SELECT pi_p90 FROM percentiles)), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    UNION ALL
    -- 3-feature: ti_p90 + kyle>0 + ofi>p90 (extreme OFI)
    SELECT 'ti_p90_kyle_gt_0_ofi_gt_p90',
           'Intensity>p90 AND Kyle>0 AND OFI>p90 -> UP (extreme)',
           3, '{"trade_intensity": ">p90", "kyle_lambda": ">0", "ofi": ">p90"}', 'long', count(*),
           countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0 AND ofi_1 > (SELECT ofi_p90 FROM percentiles)),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0 AND ofi_1 > (SELECT ofi_p90 FROM percentiles)),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0 AND ofi_1 > (SELECT ofi_p90 FROM percentiles)) /
               nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0 AND ofi_1 > (SELECT ofi_p90 FROM percentiles)), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    UNION ALL
    -- 3-feature: ti_p80 + kyle>0 + ofi>0 (more samples, relaxed intensity)
    SELECT 'ti_p80_kyle_gt_0_ofi_gt_0',
           'Intensity>p80 AND Kyle>0 AND OFI>0 -> UP (more samples)',
           3, '{"trade_intensity": ">p80", "kyle_lambda": ">0", "ofi": ">0"}', 'long', count(*),
           countIf(ti_1 > (SELECT ti_p80 FROM percentiles) AND kyle_1 > 0 AND ofi_1 > 0),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p80 FROM percentiles) AND kyle_1 > 0 AND ofi_1 > 0),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p80 FROM percentiles) AND kyle_1 > 0 AND ofi_1 > 0) /
               nullIf(countIf(ti_1 > (SELECT ti_p80 FROM percentiles) AND kyle_1 > 0 AND ofi_1 > 0), 0)
    FROM lagged WHERE ti_1 IS NOT NULL
);
