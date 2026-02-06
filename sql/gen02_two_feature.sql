-- GENERATION 2: Two-feature combinations
-- Based on Gen1 findings: trade_intensity is key filter, combine with directional features

WITH percentiles AS (
    SELECT
        quantile(0.8)(trade_intensity) as ti_p80,
        quantile(0.9)(trade_intensity) as ti_p90,
        quantile(0.95)(trade_intensity) as ti_p95,
        quantile(0.1)(kyle_lambda_proxy) as kyle_p10,
        quantile(0.9)(kyle_lambda_proxy) as kyle_p90,
        quantile(0.1)(ofi) as ofi_p10,
        quantile(0.9)(ofi) as ofi_p90,
        quantile(0.1)(turnover_imbalance) as ti_imb_p10,
        quantile(0.9)(turnover_imbalance) as ti_imb_p90,
        quantile(0.9)(price_impact) as pi_p90,
        quantile(0.9)(aggression_ratio) as agg_p90,
        quantile(0.1)(aggression_ratio) as agg_p10
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
),
bars AS (
    SELECT
        timestamp_ms,
        CASE WHEN close > open THEN 1 ELSE 0 END as direction,
        ofi, trade_intensity as ti, kyle_lambda_proxy as kyle, price_impact as pi,
        turnover_imbalance as ti_imb, aggression_ratio as agg
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
lagged AS (
    SELECT
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
    2 as n_features,
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
    2 as generation
FROM (
    -- High intensity (p90) + kyle positive -> LONG
    SELECT 'ti_p90_kyle_gt_0' as combo_name,
           'Intensity>p90 AND Kyle>0 -> UP' as combo_description,
           '{"trade_intensity": ">p90", "kyle_lambda": ">0"}' as feature_conditions,
           'long' as signal_type,
           count(*) as total_bars,
           countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0) as signal_count,
           countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 > 0) as hits,
           hits / nullIf(signal_count, 0) as hit_rate
    FROM lagged WHERE ti_1 IS NOT NULL

    UNION ALL
    SELECT 'ti_p90_kyle_lt_0', 'Intensity>p90 AND Kyle<0 -> DOWN',
           '{"trade_intensity": ">p90", "kyle_lambda": "<0"}', 'short', count(*),
           countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 < 0),
           countIf(direction = 0 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 < 0),
           countIf(direction = 0 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 < 0) /
               nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND kyle_1 < 0), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    UNION ALL
    SELECT 'ti_p95_kyle_gt_0', 'Intensity>p95 AND Kyle>0 -> UP',
           '{"trade_intensity": ">p95", "kyle_lambda": ">0"}', 'long', count(*),
           countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0) /
               nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 > 0), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    UNION ALL
    SELECT 'ti_p95_kyle_lt_0', 'Intensity>p95 AND Kyle<0 -> DOWN',
           '{"trade_intensity": ">p95", "kyle_lambda": "<0"}', 'short', count(*),
           countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 < 0),
           countIf(direction = 0 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 < 0),
           countIf(direction = 0 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 < 0) /
               nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND kyle_1 < 0), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    -- High intensity + OFI combinations
    UNION ALL
    SELECT 'ti_p90_ofi_gt_0', 'Intensity>p90 AND OFI>0 -> UP',
           '{"trade_intensity": ">p90", "ofi": ">0"}', 'long', count(*),
           countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND ofi_1 > 0),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND ofi_1 > 0),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND ofi_1 > 0) /
               nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND ofi_1 > 0), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    UNION ALL
    SELECT 'ti_p90_ofi_lt_0', 'Intensity>p90 AND OFI<0 -> DOWN',
           '{"trade_intensity": ">p90", "ofi": "<0"}', 'short', count(*),
           countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND ofi_1 < 0),
           countIf(direction = 0 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND ofi_1 < 0),
           countIf(direction = 0 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND ofi_1 < 0) /
               nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND ofi_1 < 0), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    UNION ALL
    SELECT 'ti_p95_ofi_gt_p90', 'Intensity>p95 AND OFI>p90 -> UP (extreme)',
           '{"trade_intensity": ">p95", "ofi": ">p90"}', 'long', count(*),
           countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND ofi_1 > (SELECT ofi_p90 FROM percentiles)),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND ofi_1 > (SELECT ofi_p90 FROM percentiles)),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND ofi_1 > (SELECT ofi_p90 FROM percentiles)) /
               nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND ofi_1 > (SELECT ofi_p90 FROM percentiles)), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    UNION ALL
    SELECT 'ti_p95_ofi_lt_p10', 'Intensity>p95 AND OFI<p10 -> DOWN (extreme)',
           '{"trade_intensity": ">p95", "ofi": "<p10"}', 'short', count(*),
           countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND ofi_1 < (SELECT ofi_p10 FROM percentiles)),
           countIf(direction = 0 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND ofi_1 < (SELECT ofi_p10 FROM percentiles)),
           countIf(direction = 0 AND ti_1 > (SELECT ti_p95 FROM percentiles) AND ofi_1 < (SELECT ofi_p10 FROM percentiles)) /
               nullIf(countIf(ti_1 > (SELECT ti_p95 FROM percentiles) AND ofi_1 < (SELECT ofi_p10 FROM percentiles)), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    -- High intensity + turnover imbalance
    UNION ALL
    SELECT 'ti_p90_ti_imb_gt_0', 'Intensity>p90 AND TurnoverImb>0 -> UP',
           '{"trade_intensity": ">p90", "turnover_imbalance": ">0"}', 'long', count(*),
           countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND ti_imb_1 > 0),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND ti_imb_1 > 0),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND ti_imb_1 > 0) /
               nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND ti_imb_1 > 0), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    UNION ALL
    SELECT 'ti_p90_ti_imb_lt_0', 'Intensity>p90 AND TurnoverImb<0 -> DOWN',
           '{"trade_intensity": ">p90", "turnover_imbalance": "<0"}', 'short', count(*),
           countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND ti_imb_1 < 0),
           countIf(direction = 0 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND ti_imb_1 < 0),
           countIf(direction = 0 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND ti_imb_1 < 0) /
               nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND ti_imb_1 < 0), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    -- High intensity + aggression ratio
    UNION ALL
    SELECT 'ti_p90_agg_gt_p90', 'Intensity>p90 AND Aggression>p90 -> UP',
           '{"trade_intensity": ">p90", "aggression_ratio": ">p90"}', 'long', count(*),
           countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND agg_1 > (SELECT agg_p90 FROM percentiles)),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND agg_1 > (SELECT agg_p90 FROM percentiles)),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND agg_1 > (SELECT agg_p90 FROM percentiles)) /
               nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND agg_1 > (SELECT agg_p90 FROM percentiles)), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    UNION ALL
    SELECT 'ti_p90_agg_lt_p10', 'Intensity>p90 AND Aggression<p10 -> DOWN',
           '{"trade_intensity": ">p90", "aggression_ratio": "<p10"}', 'short', count(*),
           countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND agg_1 < (SELECT agg_p10 FROM percentiles)),
           countIf(direction = 0 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND agg_1 < (SELECT agg_p10 FROM percentiles)),
           countIf(direction = 0 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND agg_1 < (SELECT agg_p10 FROM percentiles)) /
               nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND agg_1 < (SELECT agg_p10 FROM percentiles)), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    -- High intensity + price impact
    UNION ALL
    SELECT 'ti_p90_pi_gt_p90', 'Intensity>p90 AND PriceImpact>p90 -> UP',
           '{"trade_intensity": ">p90", "price_impact": ">p90"}', 'long', count(*),
           countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND pi_1 > (SELECT pi_p90 FROM percentiles)),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND pi_1 > (SELECT pi_p90 FROM percentiles)),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles) AND pi_1 > (SELECT pi_p90 FROM percentiles)) /
               nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles) AND pi_1 > (SELECT pi_p90 FROM percentiles)), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    -- Kyle + OFI agreement (no intensity filter)
    UNION ALL
    SELECT 'kyle_gt_0_ofi_gt_0', 'Kyle>0 AND OFI>0 -> UP',
           '{"kyle_lambda": ">0", "ofi": ">0"}', 'long', count(*),
           countIf(kyle_1 > 0 AND ofi_1 > 0),
           countIf(direction = 1 AND kyle_1 > 0 AND ofi_1 > 0),
           countIf(direction = 1 AND kyle_1 > 0 AND ofi_1 > 0) / nullIf(countIf(kyle_1 > 0 AND ofi_1 > 0), 0)
    FROM lagged WHERE kyle_1 IS NOT NULL

    UNION ALL
    SELECT 'kyle_lt_0_ofi_lt_0', 'Kyle<0 AND OFI<0 -> DOWN',
           '{"kyle_lambda": "<0", "ofi": "<0"}', 'short', count(*),
           countIf(kyle_1 < 0 AND ofi_1 < 0),
           countIf(direction = 0 AND kyle_1 < 0 AND ofi_1 < 0),
           countIf(direction = 0 AND kyle_1 < 0 AND ofi_1 < 0) / nullIf(countIf(kyle_1 < 0 AND ofi_1 < 0), 0)
    FROM lagged WHERE kyle_1 IS NOT NULL

    -- Extreme percentile combinations
    UNION ALL
    SELECT 'kyle_gt_p90_ofi_gt_p90', 'Kyle>p90 AND OFI>p90 -> UP (extreme)',
           '{"kyle_lambda": ">p90", "ofi": ">p90"}', 'long', count(*),
           countIf(kyle_1 > (SELECT kyle_p90 FROM percentiles) AND ofi_1 > (SELECT ofi_p90 FROM percentiles)),
           countIf(direction = 1 AND kyle_1 > (SELECT kyle_p90 FROM percentiles) AND ofi_1 > (SELECT ofi_p90 FROM percentiles)),
           countIf(direction = 1 AND kyle_1 > (SELECT kyle_p90 FROM percentiles) AND ofi_1 > (SELECT ofi_p90 FROM percentiles)) /
               nullIf(countIf(kyle_1 > (SELECT kyle_p90 FROM percentiles) AND ofi_1 > (SELECT ofi_p90 FROM percentiles)), 0)
    FROM lagged WHERE kyle_1 IS NOT NULL

    UNION ALL
    SELECT 'kyle_lt_p10_ofi_lt_p10', 'Kyle<p10 AND OFI<p10 -> DOWN (extreme)',
           '{"kyle_lambda": "<p10", "ofi": "<p10"}', 'short', count(*),
           countIf(kyle_1 < (SELECT kyle_p10 FROM percentiles) AND ofi_1 < (SELECT ofi_p10 FROM percentiles)),
           countIf(direction = 0 AND kyle_1 < (SELECT kyle_p10 FROM percentiles) AND ofi_1 < (SELECT ofi_p10 FROM percentiles)),
           countIf(direction = 0 AND kyle_1 < (SELECT kyle_p10 FROM percentiles) AND ofi_1 < (SELECT ofi_p10 FROM percentiles)) /
               nullIf(countIf(kyle_1 < (SELECT kyle_p10 FROM percentiles) AND ofi_1 < (SELECT ofi_p10 FROM percentiles)), 0)
    FROM lagged WHERE kyle_1 IS NOT NULL

    -- High intensity (p80 threshold for more samples) + directional
    UNION ALL
    SELECT 'ti_p80_kyle_gt_0', 'Intensity>p80 AND Kyle>0 -> UP (more samples)',
           '{"trade_intensity": ">p80", "kyle_lambda": ">0"}', 'long', count(*),
           countIf(ti_1 > (SELECT ti_p80 FROM percentiles) AND kyle_1 > 0),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p80 FROM percentiles) AND kyle_1 > 0),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p80 FROM percentiles) AND kyle_1 > 0) /
               nullIf(countIf(ti_1 > (SELECT ti_p80 FROM percentiles) AND kyle_1 > 0), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    UNION ALL
    SELECT 'ti_p80_kyle_lt_0', 'Intensity>p80 AND Kyle<0 -> DOWN (more samples)',
           '{"trade_intensity": ">p80", "kyle_lambda": "<0"}', 'short', count(*),
           countIf(ti_1 > (SELECT ti_p80 FROM percentiles) AND kyle_1 < 0),
           countIf(direction = 0 AND ti_1 > (SELECT ti_p80 FROM percentiles) AND kyle_1 < 0),
           countIf(direction = 0 AND ti_1 > (SELECT ti_p80 FROM percentiles) AND kyle_1 < 0) /
               nullIf(countIf(ti_1 > (SELECT ti_p80 FROM percentiles) AND kyle_1 < 0), 0)
    FROM lagged WHERE ti_1 IS NOT NULL
);
