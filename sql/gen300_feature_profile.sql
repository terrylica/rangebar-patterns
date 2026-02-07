-- ============================================================================
-- Gen 300 Phase 0: Feature Profile on Champion Signal Set
--
-- PURPOSE: Compute global quantiles (p10, p25, p50, p75, p90) for all 8
-- candidate features on the champion signal set. Inspect distributions
-- before running the full sweep.
--
-- ANTI-PATTERN COMPLIANCE:
--   AP-07: leadInFrame with UNBOUNDED FOLLOWING
--   AP-10: Rolling 1000-bar window for ti_p95 (NEVER expanding)
--   Warmup: rn > 1000 guard for rolling window stability
-- ============================================================================

WITH
-- CTE 1: Base bars with all candidate features
base_bars AS (
    SELECT
        timestamp_ms,
        open, high, low, close,
        trade_intensity,
        kyle_lambda_proxy,
        ofi,
        aggression_ratio,
        turnover_imbalance,
        price_impact,
        vwap_close_deviation,
        volume_per_trade,
        aggregation_density,
        duration_us,
        CASE WHEN close > open THEN 1 ELSE 0 END AS direction,
        row_number() OVER (ORDER BY timestamp_ms) AS rn
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 500
    ORDER BY timestamp_ms
),
-- CTE 2: Running stats — rolling 1000-bar p95 for trade_intensity (no-lookahead)
running_stats AS (
    SELECT
        *,
        quantileExactExclusive(0.95)(trade_intensity) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
        ) AS ti_p95_rolling
    FROM base_bars
),
-- CTE 3: Signal detection — lag features + entry price
signal_detection AS (
    SELECT
        timestamp_ms,
        rn,
        -- Champion pattern features (lagged)
        lagInFrame(trade_intensity, 1) OVER w AS ti_1,
        lagInFrame(kyle_lambda_proxy, 1) OVER w AS kyle_1,
        lagInFrame(direction, 1) OVER w AS dir_1,
        lagInFrame(direction, 2) OVER w AS dir_2,
        lagInFrame(ti_p95_rolling, 0) OVER w AS ti_p95_prior,
        -- 8 candidate features (lagged by 1 — prior bar's value)
        lagInFrame(ofi, 1) OVER w AS ofi_lag1,
        lagInFrame(aggression_ratio, 1) OVER w AS aggression_ratio_lag1,
        lagInFrame(turnover_imbalance, 1) OVER w AS turnover_imbalance_lag1,
        lagInFrame(price_impact, 1) OVER w AS price_impact_lag1,
        lagInFrame(vwap_close_deviation, 1) OVER w AS vwap_close_deviation_lag1,
        lagInFrame(volume_per_trade, 1) OVER w AS volume_per_trade_lag1,
        lagInFrame(aggregation_density, 1) OVER w AS aggregation_density_lag1,
        lagInFrame(duration_us, 1) OVER w AS duration_us_lag1
    FROM running_stats
    WINDOW w AS (ORDER BY timestamp_ms)
),
-- CTE 4: Champion signals only
signals AS (
    SELECT *
    FROM signal_detection
    WHERE dir_2 = 0 AND dir_1 = 0
      AND ti_1 > ti_p95_prior
      AND kyle_1 > 0
      AND rn > 1000
      AND ti_p95_prior IS NOT NULL
      AND ti_p95_prior > 0
)
SELECT
    'FEATURE PROFILE ON CHAMPION SIGNALS' AS header,
    count(*) AS total_signals,
    -- OFI
    quantileExactExclusive(0.10)(ofi_lag1) AS ofi_p10,
    quantileExactExclusive(0.25)(ofi_lag1) AS ofi_p25,
    quantileExactExclusive(0.50)(ofi_lag1) AS ofi_p50,
    quantileExactExclusive(0.75)(ofi_lag1) AS ofi_p75,
    quantileExactExclusive(0.90)(ofi_lag1) AS ofi_p90,
    -- Aggression ratio
    quantileExactExclusive(0.10)(aggression_ratio_lag1) AS aggr_p10,
    quantileExactExclusive(0.25)(aggression_ratio_lag1) AS aggr_p25,
    quantileExactExclusive(0.50)(aggression_ratio_lag1) AS aggr_p50,
    quantileExactExclusive(0.75)(aggression_ratio_lag1) AS aggr_p75,
    quantileExactExclusive(0.90)(aggression_ratio_lag1) AS aggr_p90,
    -- Turnover imbalance
    quantileExactExclusive(0.10)(turnover_imbalance_lag1) AS turn_p10,
    quantileExactExclusive(0.25)(turnover_imbalance_lag1) AS turn_p25,
    quantileExactExclusive(0.50)(turnover_imbalance_lag1) AS turn_p50,
    quantileExactExclusive(0.75)(turnover_imbalance_lag1) AS turn_p75,
    quantileExactExclusive(0.90)(turnover_imbalance_lag1) AS turn_p90,
    -- Price impact
    quantileExactExclusive(0.10)(price_impact_lag1) AS pi_p10,
    quantileExactExclusive(0.25)(price_impact_lag1) AS pi_p25,
    quantileExactExclusive(0.50)(price_impact_lag1) AS pi_p50,
    quantileExactExclusive(0.75)(price_impact_lag1) AS pi_p75,
    quantileExactExclusive(0.90)(price_impact_lag1) AS pi_p90,
    -- VWAP deviation
    quantileExactExclusive(0.10)(vwap_close_deviation_lag1) AS vwap_p10,
    quantileExactExclusive(0.25)(vwap_close_deviation_lag1) AS vwap_p25,
    quantileExactExclusive(0.50)(vwap_close_deviation_lag1) AS vwap_p50,
    quantileExactExclusive(0.75)(vwap_close_deviation_lag1) AS vwap_p75,
    quantileExactExclusive(0.90)(vwap_close_deviation_lag1) AS vwap_p90,
    -- Volume per trade
    quantileExactExclusive(0.10)(volume_per_trade_lag1) AS vpt_p10,
    quantileExactExclusive(0.25)(volume_per_trade_lag1) AS vpt_p25,
    quantileExactExclusive(0.50)(volume_per_trade_lag1) AS vpt_p50,
    quantileExactExclusive(0.75)(volume_per_trade_lag1) AS vpt_p75,
    quantileExactExclusive(0.90)(volume_per_trade_lag1) AS vpt_p90,
    -- Aggregation density
    quantileExactExclusive(0.10)(aggregation_density_lag1) AS ad_p10,
    quantileExactExclusive(0.25)(aggregation_density_lag1) AS ad_p25,
    quantileExactExclusive(0.50)(aggregation_density_lag1) AS ad_p50,
    quantileExactExclusive(0.75)(aggregation_density_lag1) AS ad_p75,
    quantileExactExclusive(0.90)(aggregation_density_lag1) AS ad_p90,
    -- Duration
    quantileExactExclusive(0.10)(duration_us_lag1) AS dur_p10,
    quantileExactExclusive(0.25)(duration_us_lag1) AS dur_p25,
    quantileExactExclusive(0.50)(duration_us_lag1) AS dur_p50,
    quantileExactExclusive(0.75)(duration_us_lag1) AS dur_p75,
    quantileExactExclusive(0.90)(duration_us_lag1) AS dur_p90
FROM signals
FORMAT Vertical;
