-- ============================================================================
-- Gen 300 Phase 3: Barrier Grid Validation on price_impact_lt_p50 Winner
--
-- ADR: docs/adr/2026-02-06-repository-creation.md
--
-- PURPOSE: Sweep TP/SL/max_bars combos on the price_impact_lt_p50 filtered
-- signal set to find if a different barrier configuration improves Kelly.
-- Feature filter is FIXED (price_impact < rolling p50, signal-relative).
--
-- BARRIER GRID (6 combos):
--   TP_MULT: 0.25, 0.50, 0.75, 1.00
--   SL_MULT: 0.125, 0.25, 0.50
--   MAX_BARS: 20, 50, 100
--   Total: 4 × 3 × 3 = 36 combos via arrayJoin
--
-- QUANTILE: Rolling 1000-bar/signal windows (matches backtesting.py)
-- ANTI-PATTERN COMPLIANCE: Same as gen300_template.sql (all 13 + 3)
-- ============================================================================

WITH
-- CTE 1: Base bars
base_bars AS (
    SELECT
        timestamp_ms,
        open, high, low, close,
        trade_intensity,
        kyle_lambda_proxy,
        price_impact,
        CASE WHEN close > open THEN 1 ELSE 0 END AS direction,
        row_number() OVER (ORDER BY timestamp_ms) AS rn
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 500
    ORDER BY timestamp_ms
),
-- CTE 2: Running stats — rolling 1000-bar p95 (matches backtesting.py)
running_stats AS (
    SELECT
        *,
        quantileExactExclusive(0.95)(trade_intensity) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
        ) AS ti_p95_rolling
    FROM base_bars
),
-- CTE 3: Signal detection
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
        lagInFrame(price_impact, 1) OVER w AS feature_lag1,
        leadInFrame(open, 1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS entry_price
    FROM running_stats
    WINDOW w AS (ORDER BY timestamp_ms)
),
-- CTE 4: Champion signals
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
      AND feature_lag1 IS NOT NULL
),
-- CTE 4b: Rolling 1000-signal p50 of price_impact within signal set
signals_with_quantile AS (
    SELECT
        *,
        quantileExactExclusive(0.50)(feature_lag1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
        ) AS feature_p50_signal
    FROM champion_signals
),
-- CTE 5: Apply price_impact filter (FIXED: price_impact < p50)
signals AS (
    SELECT *
    FROM signals_with_quantile
    WHERE feature_p50_signal IS NOT NULL
      AND feature_lag1 < feature_p50_signal
),
-- CTE 6: Forward array collection (need max 101 bars for max_bars=100)
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
        ON b.rn BETWEEN s.rn + 1 AND s.rn + 101
    GROUP BY s.timestamp_ms, s.entry_price, s.rn
),
-- CTE 7: Barrier grid via arrayJoin
-- AP-09: Threshold-relative multipliers. @500dbps: threshold_pct = 0.05
-- AP-02: Pre-compute tp_price/sl_price as columns
param_grid AS (
    SELECT
        fa.*,
        tp_m AS tp_mult,
        sl_m AS sl_mult,
        mb AS max_bars,
        fa.entry_price * (1.0 + tp_m * 0.05) AS tp_price,
        fa.entry_price * (1.0 - sl_m * 0.05) AS sl_price
    FROM forward_arrays fa
    CROSS JOIN (
        SELECT
            arrayJoin([0.25, 0.50, 0.75, 1.00]) AS tp_m,
            arrayJoin([0.125, 0.25, 0.50]) AS sl_m,
            arrayJoin([toUInt32(20), toUInt32(50), toUInt32(100)]) AS mb
    ) params
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
    FROM param_grid
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
-- Final: Aggregate metrics per barrier config
SELECT
    'price_impact_lt_p50' AS feature_filter,
    tp_mult,
    sl_mult,
    max_bars,
    tp_mult * 0.05 AS tp_pct,
    sl_mult * 0.05 AS sl_pct,
    tp_mult / sl_mult AS rr_ratio,
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
GROUP BY tp_mult, sl_mult, max_bars
ORDER BY kelly_fraction DESC
FORMAT TabSeparatedWithNames;
