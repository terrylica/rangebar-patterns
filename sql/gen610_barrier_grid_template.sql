-- ============================================================================
-- Gen 610: Barrier Grid Optimization on Cross-Asset Survivors
--
-- PURPOSE: Test variable barrier parameters on configs that survived Gen600
-- cross-asset consistency screening. Each SQL file = 1 config x 1 barrier combo.
--
-- DIFFERENCE FROM Gen600: Single parameterized barrier instead of 3-profile CROSS JOIN.
-- Inherits AP-15 compliant signal detection from Gen600 2down template.
--
-- BASE PATTERN: 2 consecutive DOWN bars + ti>p95 + kyle>0 → LONG
-- SHORT ID: 2down
--
-- PARAMETERS (substituted by generate.sh via sed):
--   __SYMBOL__           — Trading pair (e.g., SOLUSDT)
--   __THRESHOLD_DBPS__   — Range bar threshold in decimal bps (e.g., 750)
--   __FEATURE_COL_1__    — First feature column (bar-level, e.g., ofi)
--   __FEATURE_COL_2__    — Second feature column (lookback/intra, e.g., lookback_hurst)
--   __QUANTILE_PCT_1__   — First quantile level (e.g., 0.50)
--   __QUANTILE_PCT_2__   — Second quantile level (e.g., 0.50)
--   __DIRECTION_1__      — First filter direction: > or <
--   __DIRECTION_2__      — Second filter direction: > or <
--   __CONFIG_ID__        — Config identifier
--   __TP_MULT__          — Take-profit multiplier (e.g., 0.25)
--   __SL_MULT__          — Stop-loss multiplier (e.g., 0.50)
--   __MAX_BARS__         — Time barrier (e.g., 100)
--   __BARRIER_ID__       — Barrier identifier (e.g., tp025_sl050_mb100)
--
-- QUANTILE: Rolling 1000-signal windows (AP-10 compliant)
-- TIMING: AP-15 compliant — current row IS the last pattern bar
-- DATE CUTOFF: timestamp_ms <= 1738713600000 (2026-02-05 00:00:00 UTC)
-- ============================================================================

WITH
base_bars AS (
    SELECT
        timestamp_ms,
        open, high, low, close,
        trade_intensity,
        kyle_lambda_proxy,
        __FEATURE_COL_1__,
        __FEATURE_COL_2__,
        CASE
            WHEN close <= open THEN (high - open) / nullIf(high - low, 0)
            ELSE (open - low) / nullIf(high - low, 0)
        END AS opposite_wick_pct,
        -- Forward arrays (AP-14: window-based, NOT self-join)
        -- Window size: max_bars + 1 for arraySlice offset
        arraySlice(groupArray(high) OVER (
            ORDER BY timestamp_ms ROWS BETWEEN CURRENT ROW AND 201 FOLLOWING
        ), 2, 200) AS fwd_highs,
        arraySlice(groupArray(low) OVER (
            ORDER BY timestamp_ms ROWS BETWEEN CURRENT ROW AND 201 FOLLOWING
        ), 2, 200) AS fwd_lows,
        arraySlice(groupArray(open) OVER (
            ORDER BY timestamp_ms ROWS BETWEEN CURRENT ROW AND 201 FOLLOWING
        ), 2, 200) AS fwd_opens,
        arraySlice(groupArray(close) OVER (
            ORDER BY timestamp_ms ROWS BETWEEN CURRENT ROW AND 201 FOLLOWING
        ), 2, 200) AS fwd_closes,
        CASE WHEN close > open THEN 1 ELSE 0 END AS direction,
        row_number() OVER (ORDER BY timestamp_ms) AS rn
    FROM rangebar_cache.range_bars
    WHERE symbol = '__SYMBOL__'
      AND threshold_decimal_bps = __THRESHOLD_DBPS__
      AND timestamp_ms <= 1738713600000
    ORDER BY timestamp_ms
),
running_stats AS (
    SELECT
        *,
        quantileExactExclusive(0.95)(trade_intensity) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
        ) AS ti_p95_rolling
    FROM base_bars
),
signal_detection AS (
    SELECT
        timestamp_ms,
        open, high, low, close,
        direction,
        rn,
        trade_intensity AS ti_0,
        kyle_lambda_proxy AS kyle_0,
        direction AS dir_0,
        lagInFrame(direction, 1) OVER w AS dir_1,
        lagInFrame(ti_p95_rolling, 0) OVER w AS ti_p95_prior,
        __FEATURE_COL_1__ AS feature1_val,
        __FEATURE_COL_2__ AS feature2_val,
        leadInFrame(open, 1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS entry_price,
        fwd_highs,
        fwd_lows,
        fwd_opens,
        fwd_closes
    FROM running_stats
    WINDOW w AS (ORDER BY timestamp_ms)
),
champion_signals AS (
    SELECT *
    FROM signal_detection
    WHERE dir_1 = 0 AND dir_0 = 0
      AND ti_0 > ti_p95_prior
      AND kyle_0 > 0
      AND rn > 1000
      AND ti_p95_prior IS NOT NULL
      AND ti_p95_prior > 0
      AND entry_price IS NOT NULL
      AND entry_price > 0
      AND feature1_val IS NOT NULL
      AND feature2_val IS NOT NULL
),
feature1_with_quantile AS (
    SELECT
        *,
        quantileExactExclusive(__QUANTILE_PCT_1__)(feature1_val) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
        ) AS feature1_q
    FROM champion_signals
),
feature2_with_quantile AS (
    SELECT
        *,
        quantileExactExclusive(__QUANTILE_PCT_2__)(feature2_val) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
        ) AS feature2_q
    FROM feature1_with_quantile
),
signals AS (
    SELECT *
    FROM feature2_with_quantile
    WHERE feature1_q IS NOT NULL
      AND feature2_q IS NOT NULL
      AND feature1_val __DIRECTION_1__ feature1_q
      AND feature2_val __DIRECTION_2__ feature2_q
),
barrier_params AS (
    SELECT
        s.timestamp_ms,
        s.entry_price,
        s.fwd_highs, s.fwd_lows, s.fwd_opens, s.fwd_closes,
        s.entry_price * (1.0 + __TP_MULT__ * (__THRESHOLD_DBPS__ / 100000.0)) AS tp_price,
        s.entry_price * (1.0 - __SL_MULT__ * (__THRESHOLD_DBPS__ / 100000.0)) AS sl_price,
        toUInt32(__MAX_BARS__) AS max_bars
    FROM signals s
),
barrier_scan AS (
    SELECT
        timestamp_ms,
        entry_price,
        max_bars,
        tp_price,
        sl_price,
        fwd_opens,
        fwd_closes,
        length(fwd_highs) AS available_bars,
        arrayFirstIndex(x -> x >= tp_price, arraySlice(fwd_highs, 1, max_bars)) AS raw_tp_bar,
        arrayFirstIndex(x -> x <= sl_price, arraySlice(fwd_lows, 1, max_bars)) AS raw_sl_bar,
        length(arraySlice(fwd_highs, 1, max_bars)) AS window_bars
    FROM barrier_params
),
trade_outcomes AS (
    SELECT
        timestamp_ms,
        entry_price,
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
SELECT
    '__CONFIG_ID__' AS config_id,
    '2down' AS base_pattern,
    '__BARRIER_ID__' AS barrier_id,
    __TP_MULT__ AS tp_mult,
    __SL_MULT__ AS sl_mult,
    toUInt32(__MAX_BARS__) AS max_bars,
    -- Signal funnel
    (SELECT count(*) FROM base_bars WHERE rn > 1000) AS total_bars,
    (SELECT count(*) FROM champion_signals) AS base_pattern_signals,
    toUInt32(count(*)) AS filtered_signals,
    count(*) / nullIf((SELECT count(*) FROM base_bars WHERE rn > 1000), 0) AS signal_coverage,
    -- Exit type breakdown
    toUInt32(countIf(exit_type = 'TP')) AS tp_count,
    toUInt32(countIf(exit_type = 'SL')) AS sl_count,
    toUInt32(countIf(exit_type = 'TIME')) AS time_count,
    toUInt32(countIf(exit_type = 'INCOMPLETE')) AS incomplete_count,
    -- Performance metrics
    countIf(exit_type = 'TP') / nullIf(countIf(exit_type IN ('TP', 'SL', 'TIME')), 0) AS win_rate,
    sumIf((exit_price - entry_price) / entry_price, exit_type = 'TP' OR (exit_type = 'TIME' AND exit_price > entry_price))
        / nullIf(abs(sumIf((exit_price - entry_price) / entry_price, exit_type = 'SL' OR (exit_type = 'TIME' AND exit_price <= entry_price))), 0) AS profit_factor,
    avgIf((exit_price - entry_price) / entry_price, exit_type = 'TP' OR (exit_type = 'TIME' AND exit_price > entry_price)) AS avg_win_pct,
    avgIf((exit_price - entry_price) / entry_price, exit_type = 'SL' OR (exit_type = 'TIME' AND exit_price <= entry_price)) AS avg_loss_pct,
    avgIf((exit_price - entry_price) / entry_price, exit_type != 'INCOMPLETE') AS expected_value_pct,
    -- Kelly fraction
    countIf(exit_type = 'TP') / nullIf(countIf(exit_type IN ('TP', 'SL', 'TIME')), 0)
        - (1.0 - countIf(exit_type = 'TP') / nullIf(countIf(exit_type IN ('TP', 'SL', 'TIME')), 0))
          / nullIf(
              avgIf((exit_price - entry_price) / entry_price, exit_type = 'TP' OR (exit_type = 'TIME' AND exit_price > entry_price))
              / nullIf(abs(avgIf((exit_price - entry_price) / entry_price, exit_type = 'SL' OR (exit_type = 'TIME' AND exit_price <= entry_price))), 0)
            , 0) AS kelly_fraction,
    -- Timing + temporal span
    avgIf(exit_bar, exit_type != 'INCOMPLETE') AS avg_bars_held,
    medianIf(exit_bar, exit_type != 'INCOMPLETE') AS median_exit_bar,
    minIf(timestamp_ms, exit_type != 'INCOMPLETE') AS signal_min_ts_ms,
    maxIf(timestamp_ms, exit_type != 'INCOMPLETE') AS signal_max_ts_ms,
    -- Total return
    sumIf((exit_price - entry_price) / entry_price, exit_type != 'INCOMPLETE') AS total_return
FROM trade_outcomes
WHERE exit_type != 'INCOMPLETE'
FORMAT TabSeparatedWithNames;
