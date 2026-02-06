-- GENERATION 1: Single feature predictability across quantile thresholds
-- Test each feature at various thresholds

WITH percentiles AS (
    SELECT
        -- OFI percentiles
        quantile(0.1)(ofi) as ofi_p10, quantile(0.2)(ofi) as ofi_p20,
        quantile(0.8)(ofi) as ofi_p80, quantile(0.9)(ofi) as ofi_p90,
        -- Trade intensity percentiles
        quantile(0.2)(trade_intensity) as ti_p20, quantile(0.5)(trade_intensity) as ti_p50,
        quantile(0.8)(trade_intensity) as ti_p80, quantile(0.9)(trade_intensity) as ti_p90,
        -- Kyle lambda percentiles
        quantile(0.1)(kyle_lambda_proxy) as kyle_p10, quantile(0.9)(kyle_lambda_proxy) as kyle_p90,
        -- Price impact percentiles
        quantile(0.9)(price_impact) as pi_p90,
        -- Turnover imbalance percentiles
        quantile(0.1)(turnover_imbalance) as ti_imb_p10, quantile(0.9)(turnover_imbalance) as ti_imb_p90,
        -- Aggression ratio percentiles
        quantile(0.1)(aggression_ratio) as agg_p10, quantile(0.9)(aggression_ratio) as agg_p90
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
),
bars AS (
    SELECT
        timestamp_ms,
        CASE WHEN close > open THEN 1 ELSE 0 END as direction,
        ofi, trade_intensity, kyle_lambda_proxy as kyle, price_impact as pi,
        turnover_imbalance as ti_imb, aggression_ratio as agg
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
lagged AS (
    SELECT
        direction,
        lagInFrame(ofi, 1) OVER w as ofi_1,
        lagInFrame(trade_intensity, 1) OVER w as ti_1,
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
    1 as n_features,
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
    1 as generation
FROM (
    SELECT 'ofi_gt_p90' as combo_name, 'OFI > 90th pct -> UP' as combo_description,
           '{"ofi": ">p90"}' as feature_conditions, 'long' as signal_type,
           count(*) as total_bars,
           countIf(ofi_1 > (SELECT ofi_p90 FROM percentiles)) as signal_count,
           countIf(direction = 1 AND ofi_1 > (SELECT ofi_p90 FROM percentiles)) as hits,
           hits / nullIf(signal_count, 0) as hit_rate
    FROM lagged WHERE ofi_1 IS NOT NULL

    UNION ALL
    SELECT 'ofi_lt_p10', 'OFI < 10th pct -> DOWN',
           '{"ofi": "<p10"}', 'short', count(*),
           countIf(ofi_1 < (SELECT ofi_p10 FROM percentiles)),
           countIf(direction = 0 AND ofi_1 < (SELECT ofi_p10 FROM percentiles)),
           countIf(direction = 0 AND ofi_1 < (SELECT ofi_p10 FROM percentiles)) / nullIf(countIf(ofi_1 < (SELECT ofi_p10 FROM percentiles)), 0)
    FROM lagged WHERE ofi_1 IS NOT NULL

    UNION ALL
    SELECT 'ofi_gt_p80', 'OFI > 80th pct -> UP',
           '{"ofi": ">p80"}', 'long', count(*),
           countIf(ofi_1 > (SELECT ofi_p80 FROM percentiles)),
           countIf(direction = 1 AND ofi_1 > (SELECT ofi_p80 FROM percentiles)),
           countIf(direction = 1 AND ofi_1 > (SELECT ofi_p80 FROM percentiles)) / nullIf(countIf(ofi_1 > (SELECT ofi_p80 FROM percentiles)), 0)
    FROM lagged WHERE ofi_1 IS NOT NULL

    UNION ALL
    SELECT 'ofi_lt_p20', 'OFI < 20th pct -> DOWN',
           '{"ofi": "<p20"}', 'short', count(*),
           countIf(ofi_1 < (SELECT ofi_p20 FROM percentiles)),
           countIf(direction = 0 AND ofi_1 < (SELECT ofi_p20 FROM percentiles)),
           countIf(direction = 0 AND ofi_1 < (SELECT ofi_p20 FROM percentiles)) / nullIf(countIf(ofi_1 < (SELECT ofi_p20 FROM percentiles)), 0)
    FROM lagged WHERE ofi_1 IS NOT NULL

    UNION ALL
    SELECT 'ti_gt_p90', 'Intensity > 90th pct -> UP',
           '{"trade_intensity": ">p90"}', 'long', count(*),
           countIf(ti_1 > (SELECT ti_p90 FROM percentiles)),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles)),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p90 FROM percentiles)) / nullIf(countIf(ti_1 > (SELECT ti_p90 FROM percentiles)), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    UNION ALL
    SELECT 'ti_gt_p80', 'Intensity > 80th pct -> UP',
           '{"trade_intensity": ">p80"}', 'long', count(*),
           countIf(ti_1 > (SELECT ti_p80 FROM percentiles)),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p80 FROM percentiles)),
           countIf(direction = 1 AND ti_1 > (SELECT ti_p80 FROM percentiles)) / nullIf(countIf(ti_1 > (SELECT ti_p80 FROM percentiles)), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    UNION ALL
    SELECT 'ti_lt_p20', 'Intensity < 20th pct -> UP',
           '{"trade_intensity": "<p20"}', 'long', count(*),
           countIf(ti_1 < (SELECT ti_p20 FROM percentiles)),
           countIf(direction = 1 AND ti_1 < (SELECT ti_p20 FROM percentiles)),
           countIf(direction = 1 AND ti_1 < (SELECT ti_p20 FROM percentiles)) / nullIf(countIf(ti_1 < (SELECT ti_p20 FROM percentiles)), 0)
    FROM lagged WHERE ti_1 IS NOT NULL

    UNION ALL
    SELECT 'kyle_gt_p90', 'Kyle > 90th pct -> UP',
           '{"kyle_lambda": ">p90"}', 'long', count(*),
           countIf(kyle_1 > (SELECT kyle_p90 FROM percentiles)),
           countIf(direction = 1 AND kyle_1 > (SELECT kyle_p90 FROM percentiles)),
           countIf(direction = 1 AND kyle_1 > (SELECT kyle_p90 FROM percentiles)) / nullIf(countIf(kyle_1 > (SELECT kyle_p90 FROM percentiles)), 0)
    FROM lagged WHERE kyle_1 IS NOT NULL

    UNION ALL
    SELECT 'kyle_lt_p10', 'Kyle < 10th pct -> DOWN',
           '{"kyle_lambda": "<p10"}', 'short', count(*),
           countIf(kyle_1 < (SELECT kyle_p10 FROM percentiles)),
           countIf(direction = 0 AND kyle_1 < (SELECT kyle_p10 FROM percentiles)),
           countIf(direction = 0 AND kyle_1 < (SELECT kyle_p10 FROM percentiles)) / nullIf(countIf(kyle_1 < (SELECT kyle_p10 FROM percentiles)), 0)
    FROM lagged WHERE kyle_1 IS NOT NULL

    UNION ALL
    SELECT 'kyle_gt_0', 'Kyle > 0 -> UP',
           '{"kyle_lambda": ">0"}', 'long', count(*),
           countIf(kyle_1 > 0),
           countIf(direction = 1 AND kyle_1 > 0),
           countIf(direction = 1 AND kyle_1 > 0) / nullIf(countIf(kyle_1 > 0), 0)
    FROM lagged WHERE kyle_1 IS NOT NULL

    UNION ALL
    SELECT 'kyle_lt_0', 'Kyle < 0 -> DOWN',
           '{"kyle_lambda": "<0"}', 'short', count(*),
           countIf(kyle_1 < 0),
           countIf(direction = 0 AND kyle_1 < 0),
           countIf(direction = 0 AND kyle_1 < 0) / nullIf(countIf(kyle_1 < 0), 0)
    FROM lagged WHERE kyle_1 IS NOT NULL

    UNION ALL
    SELECT 'pi_gt_p90', 'PriceImpact > 90th pct -> UP',
           '{"price_impact": ">p90"}', 'long', count(*),
           countIf(pi_1 > (SELECT pi_p90 FROM percentiles)),
           countIf(direction = 1 AND pi_1 > (SELECT pi_p90 FROM percentiles)),
           countIf(direction = 1 AND pi_1 > (SELECT pi_p90 FROM percentiles)) / nullIf(countIf(pi_1 > (SELECT pi_p90 FROM percentiles)), 0)
    FROM lagged WHERE pi_1 IS NOT NULL

    UNION ALL
    SELECT 'ti_imb_gt_p90', 'TurnoverImb > 90th pct -> UP',
           '{"turnover_imbalance": ">p90"}', 'long', count(*),
           countIf(ti_imb_1 > (SELECT ti_imb_p90 FROM percentiles)),
           countIf(direction = 1 AND ti_imb_1 > (SELECT ti_imb_p90 FROM percentiles)),
           countIf(direction = 1 AND ti_imb_1 > (SELECT ti_imb_p90 FROM percentiles)) / nullIf(countIf(ti_imb_1 > (SELECT ti_imb_p90 FROM percentiles)), 0)
    FROM lagged WHERE ti_imb_1 IS NOT NULL

    UNION ALL
    SELECT 'ti_imb_lt_p10', 'TurnoverImb < 10th pct -> DOWN',
           '{"turnover_imbalance": "<p10"}', 'short', count(*),
           countIf(ti_imb_1 < (SELECT ti_imb_p10 FROM percentiles)),
           countIf(direction = 0 AND ti_imb_1 < (SELECT ti_imb_p10 FROM percentiles)),
           countIf(direction = 0 AND ti_imb_1 < (SELECT ti_imb_p10 FROM percentiles)) / nullIf(countIf(ti_imb_1 < (SELECT ti_imb_p10 FROM percentiles)), 0)
    FROM lagged WHERE ti_imb_1 IS NOT NULL

    UNION ALL
    SELECT 'agg_gt_p90', 'Aggression > 90th pct -> UP',
           '{"aggression_ratio": ">p90"}', 'long', count(*),
           countIf(agg_1 > (SELECT agg_p90 FROM percentiles)),
           countIf(direction = 1 AND agg_1 > (SELECT agg_p90 FROM percentiles)),
           countIf(direction = 1 AND agg_1 > (SELECT agg_p90 FROM percentiles)) / nullIf(countIf(agg_1 > (SELECT agg_p90 FROM percentiles)), 0)
    FROM lagged WHERE agg_1 IS NOT NULL

    UNION ALL
    SELECT 'agg_lt_p10', 'Aggression < 10th pct -> DOWN',
           '{"aggression_ratio": "<p10"}', 'short', count(*),
           countIf(agg_1 < (SELECT agg_p10 FROM percentiles)),
           countIf(direction = 0 AND agg_1 < (SELECT agg_p10 FROM percentiles)),
           countIf(direction = 0 AND agg_1 < (SELECT agg_p10 FROM percentiles)) / nullIf(countIf(agg_1 < (SELECT agg_p10 FROM percentiles)), 0)
    FROM lagged WHERE agg_1 IS NOT NULL

    UNION ALL
    SELECT 'ofi_gt_0', 'OFI > 0 -> UP',
           '{"ofi": ">0"}', 'long', count(*),
           countIf(ofi_1 > 0),
           countIf(direction = 1 AND ofi_1 > 0),
           countIf(direction = 1 AND ofi_1 > 0) / nullIf(countIf(ofi_1 > 0), 0)
    FROM lagged WHERE ofi_1 IS NOT NULL

    UNION ALL
    SELECT 'ofi_lt_0', 'OFI < 0 -> DOWN',
           '{"ofi": "<0"}', 'short', count(*),
           countIf(ofi_1 < 0),
           countIf(direction = 0 AND ofi_1 < 0),
           countIf(direction = 0 AND ofi_1 < 0) / nullIf(countIf(ofi_1 < 0), 0)
    FROM lagged WHERE ofi_1 IS NOT NULL
);
