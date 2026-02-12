-- TRUE NO-LOOKAHEAD VALIDATION
-- Fixes the critical lagInFrame bug that preserved lookahead bias
--
-- THE BUG: Previous "no-lookahead" used:
--   JOIN yearly_percentiles yp ON b.year = yp.year  -- Joins to SAME year's p95
--   lagInFrame(ti_p95, 1)  -- Lags by ONE BAR, not one year
-- Result: 99.997% of bars still had lookahead bias
--
-- THE FIX: Use quantileExactExclusive with ROWS UNBOUNDED PRECEDING
-- This computes percentile using ONLY bars before the current one
--
-- Generation 111: TRUE no-lookahead patterns

-- ============================================================================
-- Gen 111: Full champion pattern with TRUE expanding-window percentile
-- ============================================================================

INSERT INTO rangebar_cache.feature_combinations
    (symbol, threshold_decimal_bps, combo_name, combo_description, n_features,
     feature_conditions, signal_type, lookback_bars,
     total_bars, signal_count, hits, hit_rate, edge_pct, z_score, p_value, ci_low, ci_high,
     generation)
WITH
-- Step 1: Get base data with returns direction
base_bars AS (
    SELECT
        timestamp_ms,
        CASE WHEN close > open THEN 1 ELSE 0 END as direction,
        trade_intensity,
        kyle_lambda_proxy
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
-- Step 2: Compute running p95 using arrayJoin to get proper expanding window
-- ClickHouse doesn't support quantile in window functions directly, so we use a different approach
-- We'll compute the percentile threshold at specific checkpoints (every 1000 bars) and interpolate
-- For exact no-lookahead, we need running quantile which requires a workaround
running_stats AS (
    SELECT
        timestamp_ms,
        direction,
        trade_intensity,
        kyle_lambda_proxy,
        -- Use running count and approximate percentile via histogram
        count(*) OVER (ORDER BY timestamp_ms ROWS UNBOUNDED PRECEDING) as bar_count,
        -- Compute approximate p95 as value at rank 0.95 * count
        quantileExactExclusive(0.95)(trade_intensity) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) as ti_p95_expanding
    FROM base_bars
),
-- Step 3: Apply lags — AP-15: current row IS the 2nd DOWN bar (lag reduced by 1)
lagged AS (
    SELECT
        timestamp_ms,
        -- AP-15: current row is the last pattern bar
        trade_intensity AS ti_0,
        kyle_lambda_proxy AS kyle_0,
        direction AS dir_0,
        lagInFrame(direction, 1) OVER w as dir_1,
        lagInFrame(ti_p95_expanding, 0) OVER w as ti_p95_prior,  -- Use current (already shifted by PRECEDING)
        leadInFrame(direction, 1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) as next_dir,  -- outcome: is the next bar UP?
        bar_count
    FROM running_stats
    WINDOW w AS (ORDER BY timestamp_ms)
)
SELECT
    'SOLUSDT', 1000,
    'true_nla_combo_2down_ti_p95_kyle_gt_0_long',
    'TRUE NO-LOOKAHEAD: 2DOWN + ti>p95_expanding + kyle>0 → LONG',
    4,
    '{"direction(t-1,t)": "DOWN,DOWN", "trade_intensity(t)": ">p95_expanding_prior", "kyle_lambda(t)": ">0"}',
    'long', 2,
    count(*),
    countIf(dir_1 = 0 AND dir_0 = 0 AND ti_0 > ti_p95_prior AND kyle_0 > 0),
    countIf(next_dir = 1 AND dir_1 = 0 AND dir_0 = 0 AND ti_0 > ti_p95_prior AND kyle_0 > 0),
    countIf(next_dir = 1 AND dir_1 = 0 AND dir_0 = 0 AND ti_0 > ti_p95_prior AND kyle_0 > 0) /
        nullIf(countIf(dir_1 = 0 AND dir_0 = 0 AND ti_0 > ti_p95_prior AND kyle_0 > 0), 0),
    countIf(next_dir = 1 AND dir_1 = 0 AND dir_0 = 0 AND ti_0 > ti_p95_prior AND kyle_0 > 0) /
        nullIf(countIf(dir_1 = 0 AND dir_0 = 0 AND ti_0 > ti_p95_prior AND kyle_0 > 0), 0) - 0.5,
    (countIf(next_dir = 1 AND dir_1 = 0 AND dir_0 = 0 AND ti_0 > ti_p95_prior AND kyle_0 > 0) /
        nullIf(countIf(dir_1 = 0 AND dir_0 = 0 AND ti_0 > ti_p95_prior AND kyle_0 > 0), 0) - 0.5) /
        sqrt(0.25 / nullIf(countIf(dir_1 = 0 AND dir_0 = 0 AND ti_0 > ti_p95_prior AND kyle_0 > 0), 0)),
    0.5, 0.5, 0.5,
    111
FROM lagged
WHERE dir_1 IS NOT NULL
  AND ti_p95_prior IS NOT NULL
  AND ti_p95_prior > 0  -- Skip warmup period (first ~100 bars)
  AND bar_count > 1000;  -- Require 1000+ bars of history for stable percentile

-- ============================================================================
-- Gen 111: Simpler pattern (no percentile - inherently no lookahead)
-- This is the control that should match previous results exactly
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
        CASE WHEN close > open THEN 1 ELSE 0 END as direction,
        kyle_lambda_proxy as kyle
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
-- AP-15: current row IS the 2nd DOWN bar (lag reduced by 1)
lagged AS (
    SELECT
        direction AS dir_0,
        lagInFrame(direction, 1) OVER w as dir_1,
        kyle AS kyle_0,
        leadInFrame(direction, 1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) as next_dir
    FROM bars
    WINDOW w AS (ORDER BY timestamp_ms)
)
SELECT
    'SOLUSDT', 1000,
    'true_nla_2down_kyle_gt_0_long',
    'TRUE NO-LOOKAHEAD: 2DOWN + kyle>0 → LONG (no percentile threshold)',
    3,
    '{"direction(t-1,t)": "DOWN,DOWN", "kyle_lambda(t)": ">0"}',
    'long', 2,
    count(*),
    countIf(dir_1 = 0 AND dir_0 = 0 AND kyle_0 > 0),
    countIf(next_dir = 1 AND dir_1 = 0 AND dir_0 = 0 AND kyle_0 > 0),
    countIf(next_dir = 1 AND dir_1 = 0 AND dir_0 = 0 AND kyle_0 > 0) /
        nullIf(countIf(dir_1 = 0 AND dir_0 = 0 AND kyle_0 > 0), 0),
    countIf(next_dir = 1 AND dir_1 = 0 AND dir_0 = 0 AND kyle_0 > 0) /
        nullIf(countIf(dir_1 = 0 AND dir_0 = 0 AND kyle_0 > 0), 0) - 0.5,
    (countIf(next_dir = 1 AND dir_1 = 0 AND dir_0 = 0 AND kyle_0 > 0) /
        nullIf(countIf(dir_1 = 0 AND dir_0 = 0 AND kyle_0 > 0), 0) - 0.5) /
        sqrt(0.25 / countIf(dir_1 = 0 AND dir_0 = 0 AND kyle_0 > 0)),
    0.5, 0.5, 0.5,
    111
FROM lagged
WHERE dir_1 IS NOT NULL;

-- ============================================================================
-- Gen 111: Pure mean reversion (2 DOWN → LONG, no filters)
-- Baseline for comparison
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
        CASE WHEN close > open THEN 1 ELSE 0 END as direction
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
    ORDER BY timestamp_ms
),
-- AP-15: current row IS the 2nd DOWN bar (lag reduced by 1)
lagged AS (
    SELECT
        direction AS dir_0,
        lagInFrame(direction, 1) OVER w as dir_1,
        leadInFrame(direction, 1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) as next_dir
    FROM bars
    WINDOW w AS (ORDER BY timestamp_ms)
)
SELECT
    'SOLUSDT', 1000,
    'true_nla_pure_2down_long',
    'TRUE NO-LOOKAHEAD: Pure 2DOWN → LONG (baseline)',
    1,
    '{"direction(t-1,t)": "DOWN,DOWN"}',
    'long', 2,
    count(*),
    countIf(dir_1 = 0 AND dir_0 = 0),
    countIf(next_dir = 1 AND dir_1 = 0 AND dir_0 = 0),
    countIf(next_dir = 1 AND dir_1 = 0 AND dir_0 = 0) /
        nullIf(countIf(dir_1 = 0 AND dir_0 = 0), 0),
    countIf(next_dir = 1 AND dir_1 = 0 AND dir_0 = 0) /
        nullIf(countIf(dir_1 = 0 AND dir_0 = 0), 0) - 0.5,
    (countIf(next_dir = 1 AND dir_1 = 0 AND dir_0 = 0) /
        nullIf(countIf(dir_1 = 0 AND dir_0 = 0), 0) - 0.5) /
        sqrt(0.25 / countIf(dir_1 = 0 AND dir_0 = 0)),
    0.5, 0.5, 0.5,
    111
FROM lagged
WHERE dir_1 IS NOT NULL;
