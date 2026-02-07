-- ============================================================================
-- Gen 400: Four-Feature Combination Sweep — Parameterized Template
--
-- PURPOSE: Apply FOUR simultaneous microstructure feature filters on top of
-- the champion pattern, with fixed 2:1 R:R barriers (TP=0.5x, SL=0.25x,
-- max_bars=50). Tests whether 4-feature combinations push Kelly positive.
--
-- NOTE: Phase 3 uses p50 only (gt/lt), so 2^4=16 direction combos per
-- C(8,4)=70 feature combos = 1,120 total configs.
--
-- PARAMETERS (substituted by mise task via sed):
--   __FEATURE_COL_1__    — First feature column
--   __FEATURE_COL_2__    — Second feature column
--   __FEATURE_COL_3__    — Third feature column
--   __FEATURE_COL_4__    — Fourth feature column
--   __QUANTILE_PCT_1__   — First quantile level
--   __QUANTILE_PCT_2__   — Second quantile level
--   __QUANTILE_PCT_3__   — Third quantile level
--   __QUANTILE_PCT_4__   — Fourth quantile level
--   __DIRECTION_1__      — First filter direction: > or <
--   __DIRECTION_2__      — Second filter direction: > or <
--   __DIRECTION_3__      — Third filter direction: > or <
--   __DIRECTION_4__      — Fourth filter direction: > or <
--   __CONFIG_ID__        — Config identifier
--
-- BARRIERS (fixed):
--   TP = 0.5x threshold = entry + 2.5% at @500dbps
--   SL = 0.25x threshold = entry - 1.25% at @500dbps
--   R:R = 2:1 (TP > SL), max_bars = 50
--
-- QUANTILE: Rolling 1000-bar/signal windows (AP-10 CRITICAL, never expanding)
-- ANTI-PATTERN COMPLIANCE: All 13 + 3 (same as Gen300)
-- ============================================================================

WITH
-- CTE 1: Base bars — OHLCV + all four feature columns + row numbering
base_bars AS (
    SELECT
        timestamp_ms,
        open, high, low, close,
        trade_intensity,
        kyle_lambda_proxy,
        __FEATURE_COL_1__,
        __FEATURE_COL_2__,
        __FEATURE_COL_3__,
        __FEATURE_COL_4__,
        CASE WHEN close > open THEN 1 ELSE 0 END AS direction,
        row_number() OVER (ORDER BY timestamp_ms) AS rn
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 500
    ORDER BY timestamp_ms
),
-- CTE 2: Running stats — rolling 1000-bar p95 for trade_intensity
running_stats AS (
    SELECT
        *,
        quantileExactExclusive(0.95)(trade_intensity) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
        ) AS ti_p95_rolling
    FROM base_bars
),
-- CTE 3: Signal detection — lag all four features + entry price
signal_detection AS (
    SELECT
        timestamp_ms,
        open, high, low, close,
        direction,
        rn,
        lagInFrame(trade_intensity, 1) OVER w AS ti_1,
        lagInFrame(kyle_lambda_proxy, 1) OVER w AS kyle_1,
        lagInFrame(direction, 1) OVER w AS dir_1,
        lagInFrame(direction, 2) OVER w AS dir_2,
        lagInFrame(ti_p95_rolling, 0) OVER w AS ti_p95_prior,
        lagInFrame(__FEATURE_COL_1__, 1) OVER w AS feature1_lag1,
        lagInFrame(__FEATURE_COL_2__, 1) OVER w AS feature2_lag1,
        lagInFrame(__FEATURE_COL_3__, 1) OVER w AS feature3_lag1,
        lagInFrame(__FEATURE_COL_4__, 1) OVER w AS feature4_lag1,
        leadInFrame(open, 1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS entry_price
    FROM running_stats
    WINDOW w AS (ORDER BY timestamp_ms)
),
-- CTE 4: Champion signals (before feature filters)
champion_signals AS (
    SELECT *
    FROM signal_detection
    WHERE dir_2 = 0 AND dir_1 = 0
      AND ti_1 > ti_p95_prior
      AND kyle_1 > 0
      AND rn > 1000
      AND ti_p95_prior IS NOT NULL
      AND ti_p95_prior > 0
      AND entry_price IS NOT NULL
      AND entry_price > 0
      AND feature1_lag1 IS NOT NULL
      AND feature2_lag1 IS NOT NULL
      AND feature3_lag1 IS NOT NULL
      AND feature4_lag1 IS NOT NULL
),
-- CTE 4b1: Rolling 1000-signal quantile for feature 1
feature1_with_quantile AS (
    SELECT
        *,
        quantileExactExclusive(__QUANTILE_PCT_1__)(feature1_lag1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
        ) AS feature1_q
    FROM champion_signals
),
-- CTE 4b2: Rolling 1000-signal quantile for feature 2
feature2_with_quantile AS (
    SELECT
        *,
        quantileExactExclusive(__QUANTILE_PCT_2__)(feature2_lag1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
        ) AS feature2_q
    FROM feature1_with_quantile
),
-- CTE 4b3: Rolling 1000-signal quantile for feature 3
feature3_with_quantile AS (
    SELECT
        *,
        quantileExactExclusive(__QUANTILE_PCT_3__)(feature3_lag1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
        ) AS feature3_q
    FROM feature2_with_quantile
),
-- CTE 4b4: Rolling 1000-signal quantile for feature 4
feature4_with_quantile AS (
    SELECT
        *,
        quantileExactExclusive(__QUANTILE_PCT_4__)(feature4_lag1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
        ) AS feature4_q
    FROM feature3_with_quantile
),
-- CTE 5: Apply ALL FOUR feature filters (AND condition)
signals AS (
    SELECT *
    FROM feature4_with_quantile
    WHERE feature1_q IS NOT NULL
      AND feature2_q IS NOT NULL
      AND feature3_q IS NOT NULL
      AND feature4_q IS NOT NULL
      AND feature1_lag1 __DIRECTION_1__ feature1_q
      AND feature2_lag1 __DIRECTION_2__ feature2_q
      AND feature3_lag1 __DIRECTION_3__ feature3_q
      AND feature4_lag1 __DIRECTION_4__ feature4_q
),
-- CTE 6: Forward array collection via self-join
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
-- CTE 7: Fixed barrier parameters
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
SELECT
    '__CONFIG_ID__' AS config_id,
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
