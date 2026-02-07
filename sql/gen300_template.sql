-- ============================================================================
-- Gen 300: Feature Filter Brute-Force Sweep — Parameterized Template
--
-- PURPOSE: Add a single microstructure feature filter on top of the champion
-- pattern, with fixed 2:1 R:R barriers (TP=0.5x, SL=0.25x, max_bars=50).
-- Measure whether the feature filter pushes Kelly fraction toward positive.
--
-- PARAMETERS (substituted by mise task via sed):
--   __FEATURE_COL__    — Column name (e.g., ofi, aggression_ratio)
--   __QUANTILE_PCT__   — Quantile level (e.g., 0.50, 0.75, 0.90)
--   __DIRECTION__      — Filter direction: > or <
--   __CONFIG_ID__      — Config identifier (e.g., ofi_gt_p75)
--   __FEATURE_NAME__   — Human-readable name (e.g., OFI)
--
-- BARRIERS (fixed for Phase 1):
--   TP = 0.5x threshold = entry + 2.5% at @500dbps (reward)
--   SL = 0.25x threshold = entry - 1.25% at @500dbps (risk)
--   R:R = 2:1 (TP > SL)
--   max_bars = 50
--
-- FEATURE QUANTILE APPROACH:
--   Expanding window quantile computed over CHAMPION SIGNALS only (not all bars).
--   This is correct because we want to filter signals that are extreme relative
--   to other signals, not relative to all bars (which include UP bars with very
--   different feature distributions).
--
-- ANTI-PATTERN COMPLIANCE (ALL 13 + 3):
--   AP-01: Signals-only forward arrays via self-join
--   AP-02: Pre-computed tp_price/sl_price + feature quantile as columns
--   AP-03: arrayFirstIndex 0-not-found guards in all CASE branches
--   AP-07: leadInFrame with ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
--   AP-08: arraySlice before arrayFirstIndex
--   AP-09: Threshold-relative multipliers (0.5x, 0.25x at @500dbps = 0.05)
--   AP-10: Expanding window quantiles over signal set (no lookahead)
--   AP-11: TP/SL from entry_price (next bar's open), not signal close
--   AP-12: SL wins same-bar ties (raw_sl_bar <= raw_tp_bar)
--   AP-13: Gap-down SL = least(fwd_opens[exit_bar], sl_price)
--   NLA:   lagInFrame(feature, 1) for prior-bar values
--   NLA:   bar_count > 1000 warmup guard
--   BT:    Entry at next bar's open (leadInFrame pattern)
-- ============================================================================

WITH
-- CTE 1: Base bars — OHLCV + microstructure features + row numbering
base_bars AS (
    SELECT
        timestamp_ms,
        open, high, low, close,
        trade_intensity,
        kyle_lambda_proxy,
        __FEATURE_COL__,
        CASE WHEN close > open THEN 1 ELSE 0 END AS direction,
        row_number() OVER (ORDER BY timestamp_ms) AS rn
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 500
    ORDER BY timestamp_ms
),
-- CTE 2: Running stats — expanding p95 for trade_intensity (no-lookahead)
-- AP-10: Expanding window quantile over ALL bars (only for trade_intensity)
running_stats AS (
    SELECT
        *,
        count(*) OVER (ORDER BY timestamp_ms ROWS UNBOUNDED PRECEDING) AS bar_count,
        quantileExactExclusive(0.95)(trade_intensity) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) AS ti_p95_expanding
    FROM base_bars
),
-- CTE 3: Signal detection — lag features + entry price
-- AP-07: leadInFrame MUST use UNBOUNDED FOLLOWING to access next bar's open
-- NLA: lagInFrame(feature, 1) reads PREVIOUS bar's value
signal_detection AS (
    SELECT
        timestamp_ms,
        open, high, low, close,
        direction,
        rn,
        bar_count,
        lagInFrame(trade_intensity, 1) OVER w AS ti_1,
        lagInFrame(kyle_lambda_proxy, 1) OVER w AS kyle_1,
        lagInFrame(direction, 1) OVER w AS dir_1,
        lagInFrame(direction, 2) OVER w AS dir_2,
        lagInFrame(ti_p95_expanding, 0) OVER w AS ti_p95_prior,
        -- Feature filter: prior bar's value (no lookahead)
        lagInFrame(__FEATURE_COL__, 1) OVER w AS feature_lag1,
        -- AP-07: UNBOUNDED FOLLOWING for entry price
        leadInFrame(open, 1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS entry_price
    FROM running_stats
    WINDOW w AS (ORDER BY timestamp_ms)
),
-- CTE 4: Champion signals (all ~1,895 before feature filter)
-- AP-01: Filter to signals FIRST, before forward array collection
champion_signals AS (
    SELECT *
    FROM signal_detection
    WHERE dir_2 = 0 AND dir_1 = 0           -- 2 consecutive DOWN bars
      AND ti_1 > ti_p95_prior               -- trade_intensity > p95_expanding
      AND kyle_1 > 0                        -- kyle_lambda > 0
      AND bar_count > 1000                  -- Warmup guard
      AND ti_p95_prior IS NOT NULL
      AND ti_p95_prior > 0
      AND entry_price IS NOT NULL
      AND entry_price > 0
      AND feature_lag1 IS NOT NULL
),
-- CTE 4b: Compute expanding quantile of feature WITHIN signal set (no lookahead)
-- This is the key insight: quantile is relative to OTHER champion signals,
-- not relative to all bars (which have very different feature distributions)
signals_with_quantile AS (
    SELECT
        *,
        quantileExactExclusive(__QUANTILE_PCT__)(feature_lag1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) AS feature_quantile_signal
    FROM champion_signals
),
-- CTE 5: Apply feature filter
signals AS (
    SELECT *
    FROM signals_with_quantile
    WHERE feature_quantile_signal IS NOT NULL
      AND feature_lag1 __DIRECTION__ feature_quantile_signal
),
-- CTE 6: Forward array collection via self-join (filtered signals only)
-- AP-01: Join signals (~few hundred) to base_bars, not all 225K bars
forward_arrays AS (
    SELECT
        s.timestamp_ms,
        s.entry_price,
        s.rn AS signal_rn,
        groupArray(b.high) AS fwd_highs,
        groupArray(b.low) AS fwd_lows,
        groupArray(b.open) AS fwd_opens,
        groupArray(b.close) AS fwd_closes
    FROM signals s
    INNER JOIN base_bars b
        ON b.rn BETWEEN s.rn + 1 AND s.rn + 51
    GROUP BY s.timestamp_ms, s.entry_price, s.rn
),
-- CTE 7: Fixed barrier parameters (no arrayJoin — single config)
-- AP-09: Threshold-relative multipliers. @500dbps: threshold_pct = 0.05
-- AP-02: Pre-compute tp_price/sl_price as columns
param_with_prices AS (
    SELECT
        *,
        0.5 AS tp_mult,
        0.25 AS sl_mult,
        toUInt32(50) AS max_bars,
        entry_price * (1.0 + 0.5 * 0.05) AS tp_price,
        entry_price * (1.0 - 0.25 * 0.05) AS sl_price
    FROM forward_arrays
),
-- CTE 8: Barrier scan
-- AP-08: arraySlice before arrayFirstIndex
-- AP-03: arrayFirstIndex returns 0 for not-found
barrier_scan AS (
    SELECT
        timestamp_ms,
        entry_price,
        tp_mult,
        sl_mult,
        max_bars,
        tp_price,
        sl_price,
        fwd_opens,
        fwd_closes,
        length(fwd_highs) AS available_bars,
        arrayFirstIndex(x -> x >= tp_price, arraySlice(fwd_highs, 1, max_bars)) AS raw_tp_bar,
        arrayFirstIndex(x -> x <= sl_price, arraySlice(fwd_lows, 1, max_bars)) AS raw_sl_bar,
        length(arraySlice(fwd_highs, 1, max_bars)) AS window_bars
    FROM param_with_prices
),
-- CTE 9: Trade outcomes
-- AP-03: Full 0-not-found guards
-- AP-12: SL wins same-bar ties (<=)
-- AP-13: Gap-down SL = least(open, sl_price)
-- AP-11: TP/SL from entry_price (next bar's open)
trade_outcomes AS (
    SELECT
        timestamp_ms,
        entry_price,
        tp_mult,
        sl_mult,
        max_bars,
        tp_price,
        sl_price,
        CASE
            WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_sl_bar <= raw_tp_bar THEN 'SL'
            WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_tp_bar < raw_sl_bar THEN 'TP'
            WHEN raw_sl_bar > 0 AND raw_tp_bar = 0 THEN 'SL'
            WHEN raw_tp_bar > 0 AND raw_sl_bar = 0 THEN 'TP'
            WHEN window_bars >= max_bars THEN 'TIME'
            ELSE 'INCOMPLETE'
        END AS exit_type,
        CASE
            WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_sl_bar <= raw_tp_bar THEN raw_sl_bar
            WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_tp_bar < raw_sl_bar THEN raw_tp_bar
            WHEN raw_sl_bar > 0 AND raw_tp_bar = 0 THEN raw_sl_bar
            WHEN raw_tp_bar > 0 AND raw_sl_bar = 0 THEN raw_tp_bar
            WHEN window_bars >= max_bars THEN max_bars
            ELSE 0
        END AS exit_bar,
        CASE
            WHEN raw_sl_bar > 0 AND (raw_tp_bar = 0 OR raw_sl_bar <= raw_tp_bar)
                THEN least(fwd_opens[raw_sl_bar], sl_price)
            WHEN raw_tp_bar > 0 AND (raw_sl_bar = 0 OR raw_tp_bar < raw_sl_bar)
                THEN tp_price
            WHEN window_bars >= max_bars
                THEN fwd_closes[max_bars]
            ELSE 0
        END AS exit_price,
        raw_tp_bar,
        raw_sl_bar,
        window_bars
    FROM barrier_scan
)
-- Final SELECT: Aggregate metrics for this config
-- Output as tab-separated for easy parsing by mise task
SELECT
    '__CONFIG_ID__' AS config_id,
    '__FEATURE_NAME__' AS feature_name,
    '__FEATURE_COL__' AS feature_column,
    __QUANTILE_PCT__ AS quantile_level,
    '__DIRECTION__' AS filter_direction,
    0.5 AS tp_mult,
    0.25 AS sl_mult,
    50 AS max_bars,
    0.025 AS tp_pct,
    0.0125 AS sl_pct,
    toUInt32(count(*)) AS filtered_signals,
    toUInt32(countIf(exit_type = 'TP')) AS tp_count,
    toUInt32(countIf(exit_type = 'SL')) AS sl_count,
    toUInt32(countIf(exit_type = 'TIME')) AS time_count,
    toUInt32(countIf(exit_type = 'INCOMPLETE')) AS incomplete_count,
    countIf(exit_type = 'TP') / nullIf(countIf(exit_type IN ('TP', 'SL', 'TIME')), 0) AS win_rate,
    sumIf((exit_price - entry_price) / entry_price, exit_type = 'TP' OR (exit_type = 'TIME' AND exit_price > entry_price))
        / nullIf(abs(sumIf((exit_price - entry_price) / entry_price, exit_type = 'SL' OR (exit_type = 'TIME' AND exit_price <= entry_price))), 0) AS profit_factor,
    avgIf((exit_price - entry_price) / entry_price, exit_type = 'TP' OR (exit_type = 'TIME' AND exit_price > entry_price)) AS avg_win_pct,
    avgIf((exit_price - entry_price) / entry_price, exit_type = 'SL' OR (exit_type = 'TIME' AND exit_price <= entry_price)) AS avg_loss_pct,
    avgIf((exit_price - entry_price) / entry_price, exit_type = 'TP' OR (exit_type = 'TIME' AND exit_price > entry_price))
        / nullIf(abs(avgIf((exit_price - entry_price) / entry_price, exit_type = 'SL' OR (exit_type = 'TIME' AND exit_price <= entry_price))), 0) AS risk_reward,
    avgIf((exit_price - entry_price) / entry_price, exit_type != 'INCOMPLETE') AS expected_value_pct,
    avgIf(exit_bar, exit_type != 'INCOMPLETE') AS avg_bars_held,
    countIf(exit_type = 'TP') / nullIf(countIf(exit_type IN ('TP', 'SL', 'TIME')), 0)
        - (1.0 - countIf(exit_type = 'TP') / nullIf(countIf(exit_type IN ('TP', 'SL', 'TIME')), 0))
          / nullIf(
              avgIf((exit_price - entry_price) / entry_price, exit_type = 'TP' OR (exit_type = 'TIME' AND exit_price > entry_price))
              / nullIf(abs(avgIf((exit_price - entry_price) / entry_price, exit_type = 'SL' OR (exit_type = 'TIME' AND exit_price <= entry_price))), 0)
            , 0) AS kelly_fraction
FROM trade_outcomes
WHERE exit_type != 'INCOMPLETE'
FORMAT TabSeparatedWithNames;
