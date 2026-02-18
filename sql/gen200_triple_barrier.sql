-- ============================================================================
-- Gen 200: Triple Barrier Method in ClickHouse SQL
-- GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/3
-- Copied from: gen111_true_nolookahead.sql (champion pattern base)
--
-- PURPOSE: Measure risk-adjusted outcomes (profit factor, risk-reward ratio,
-- expected value) using triple barrier method, aligned with backtesting.py
-- execution semantics.
--
-- APPROACH: Signals-only forward array collection + inline arrayJoin parameter
-- sweep. All audit corrections applied (lambda closure, 0-not-found guards,
-- leadInFrame frame, threshold-relative parameters).
--
-- AUDIT FIXES APPLIED:
--   #1: Pre-computed tp_price/sl_price columns (no lambda closure over outer cols)
--   #2: Explicit > 0 guards for arrayFirstIndex 0="not found"
--   #3: Forward arrays collected on signal bars only (self-join approach)
--   #4: leadInFrame with UNBOUNDED FOLLOWING frame
--   #7: arraySlice before arrayFirstIndex, inline arrayJoin
--   #9: Threshold-relative parameter multipliers
-- ============================================================================

-- Step 0: Create destination tables (idempotent)
CREATE TABLE IF NOT EXISTS rangebar_cache.barrier_results (
    symbol String,
    threshold_decimal_bps UInt32,
    pattern_name String,
    generation UInt32,
    tp_mult Float64,
    sl_mult Float64,
    max_bars UInt32,
    tp_pct Float64,
    sl_pct Float64,
    total_signals UInt32,
    tp_count UInt32,
    sl_count UInt32,
    time_count UInt32,
    incomplete_count UInt32,
    win_rate Float64,
    profit_factor Float64,
    avg_win_pct Float64,
    avg_loss_pct Float64,
    risk_reward Float64,
    expected_value_pct Float64,
    avg_bars_held Float64,
    kelly_fraction Float64,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (symbol, threshold_decimal_bps, generation, tp_mult, sl_mult, max_bars);

CREATE TABLE IF NOT EXISTS rangebar_cache.barrier_trade_log (
    symbol String,
    threshold_decimal_bps UInt32,
    generation UInt32,
    signal_timestamp_ms UInt64,
    entry_price Float64,
    tp_mult Float64,
    sl_mult Float64,
    max_bars UInt32,
    tp_price Float64,
    sl_price Float64,
    exit_type String,
    exit_price Float64,
    exit_bar_offset UInt32,
    pnl_pct Float64,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (symbol, threshold_decimal_bps, generation, signal_timestamp_ms);

-- ============================================================================
-- Main query: Triple barrier sweep for SOL @250dbps
-- ============================================================================

-- Clear previous Gen200 results for this threshold
ALTER TABLE rangebar_cache.barrier_results
    DELETE WHERE generation = 200 AND symbol = 'SOLUSDT' AND threshold_decimal_bps = 250;

ALTER TABLE rangebar_cache.barrier_trade_log
    DELETE WHERE generation = 200 AND symbol = 'SOLUSDT' AND threshold_decimal_bps = 250;

INSERT INTO rangebar_cache.barrier_results
    (symbol, threshold_decimal_bps, pattern_name, generation,
     tp_mult, sl_mult, max_bars, tp_pct, sl_pct,
     total_signals, tp_count, sl_count, time_count, incomplete_count,
     win_rate, profit_factor, avg_win_pct, avg_loss_pct, risk_reward,
     expected_value_pct, avg_bars_held, kelly_fraction)
WITH
-- bar_range = threshold_decimal_bps / 100000.0 = 0.0025 for @250dbps
-- CTE 1: Base bars — OHLCV + microstructure features + row numbering
base_bars AS (
    SELECT
        timestamp_ms,
        open, high, low, close,
        trade_intensity,
        kyle_lambda_proxy,
        CASE WHEN close > open THEN 1 ELSE 0 END AS direction,
        row_number() OVER (ORDER BY timestamp_ms) AS rn
    FROM rangebar_cache.range_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 250
    ORDER BY timestamp_ms
),
-- CTE 2: Running stats — expanding p95 for trade_intensity (no-lookahead)
-- Copied from Gen111: quantileExactExclusive with ROWS UNBOUNDED PRECEDING
running_stats AS (
    SELECT
        timestamp_ms,
        open, high, low, close,
        trade_intensity,
        kyle_lambda_proxy,
        direction,
        rn,
        count(*) OVER (ORDER BY timestamp_ms ROWS UNBOUNDED PRECEDING) AS bar_count,
        quantileExactExclusive(0.95)(trade_intensity) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) AS ti_p95_expanding
    FROM base_bars
),
-- CTE 3: Signal detection — lag features + entry price
-- AUDIT #4: leadInFrame uses UNBOUNDED FOLLOWING frame to access next bar's open
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
        -- AUDIT #4: Must use UNBOUNDED FOLLOWING to see next bar's open
        leadInFrame(open, 1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS entry_price
    FROM running_stats
    WINDOW w AS (ORDER BY timestamp_ms)
),
-- CTE 4: Filter to champion pattern signals ONLY (before array collection)
-- AUDIT #3: Signals-only approach — ~1000 signals vs 1.4M bars
signals AS (
    SELECT *
    FROM signal_detection
    WHERE dir_2 = 0 AND dir_1 = 0
      AND ti_1 > ti_p95_prior
      AND kyle_1 > 0
      AND bar_count > 1000
      AND ti_p95_prior IS NOT NULL
      AND ti_p95_prior > 0
      AND entry_price IS NOT NULL
      AND entry_price > 0
),
-- CTE 5: Forward array collection via self-join
-- AUDIT #3: Join signals to base_bars for forward OHLC context (51 bars max)
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
-- CTE 6: Parameter expansion via inline arrayJoin
-- AUDIT #7: Inline arrayJoin (not CROSS JOIN)
-- AUDIT #9: Threshold-relative multipliers
-- AUDIT #1: Pre-compute tp_price/sl_price as columns
param_expanded AS (
    SELECT
        timestamp_ms,
        entry_price,
        signal_rn,
        fwd_highs,
        fwd_lows,
        fwd_opens,
        fwd_closes,
        arrayJoin([5.0, 10.0, 15.0, 20.0, 30.0]) AS tp_mult,
        arrayJoin([2.5, 5.0, 7.5, 10.0, 15.0]) AS sl_mult,
        arrayJoin(CAST([5, 10, 20, 50], 'Array(UInt32)')) AS max_bars
    FROM forward_arrays
),
-- CTE 6b: Pre-compute absolute prices (separate CTE to avoid lambda closure bugs)
-- AUDIT #1: tp_price/sl_price as columns, not in lambda closures
param_with_prices AS (
    SELECT
        *,
        entry_price * (1.0 + tp_mult * 0.0025) AS tp_price,
        entry_price * (1.0 - sl_mult * 0.0025) AS sl_price
    FROM param_expanded
),
-- CTE 7: Barrier scan — arraySlice + arrayFirstIndex with 0-guards
-- AUDIT #2: Explicit 0-not-found guards
-- AUDIT #7: arraySlice before search to limit to max_bars
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
        -- Barrier detection with arraySlice limiting search window
        arrayFirstIndex(x -> x >= tp_price, arraySlice(fwd_highs, 1, max_bars)) AS raw_tp_bar,
        arrayFirstIndex(x -> x <= sl_price, arraySlice(fwd_lows, 1, max_bars)) AS raw_sl_bar,
        -- Available bars in sliced window
        length(arraySlice(fwd_highs, 1, max_bars)) AS window_bars
    FROM param_with_prices
),
-- CTE 8: Trade outcomes — exit classification + exit price
-- AUDIT #2: Full 0-not-found guard logic
trade_outcomes AS (
    SELECT
        timestamp_ms,
        entry_price,
        tp_mult,
        sl_mult,
        max_bars,
        tp_price,
        sl_price,
        -- Exit type with explicit 0-guards (AUDIT #2)
        CASE
            WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_sl_bar <= raw_tp_bar THEN 'SL'
            WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_tp_bar < raw_sl_bar THEN 'TP'
            WHEN raw_sl_bar > 0 AND raw_tp_bar = 0 THEN 'SL'
            WHEN raw_tp_bar > 0 AND raw_sl_bar = 0 THEN 'TP'
            WHEN window_bars >= max_bars THEN 'TIME'
            ELSE 'INCOMPLETE'
        END AS exit_type,
        -- Exit bar offset (1-indexed within forward window)
        CASE
            WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_sl_bar <= raw_tp_bar THEN raw_sl_bar
            WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_tp_bar < raw_sl_bar THEN raw_tp_bar
            WHEN raw_sl_bar > 0 AND raw_tp_bar = 0 THEN raw_sl_bar
            WHEN raw_tp_bar > 0 AND raw_sl_bar = 0 THEN raw_tp_bar
            WHEN window_bars >= max_bars THEN max_bars
            ELSE 0
        END AS exit_bar,
        -- Exit price (aligned with backtesting.py semantics)
        CASE
            -- SL: min(open, sl_price) for gap-down handling
            WHEN raw_sl_bar > 0 AND (raw_tp_bar = 0 OR raw_sl_bar <= raw_tp_bar)
                THEN least(fwd_opens[raw_sl_bar], sl_price)
            -- TP: exact tp_price (limit fill)
            WHEN raw_tp_bar > 0 AND (raw_sl_bar = 0 OR raw_tp_bar < raw_sl_bar)
                THEN tp_price
            -- TIME: close at time barrier
            WHEN window_bars >= max_bars
                THEN fwd_closes[max_bars]
            ELSE 0
        END AS exit_price,
        raw_tp_bar,
        raw_sl_bar,
        window_bars
    FROM barrier_scan
)
-- Final SELECT: Aggregate metrics per parameter combo
SELECT
    'SOLUSDT' AS symbol,
    250 AS threshold_decimal_bps,
    'gen200_triple_barrier' AS pattern_name,
    200 AS generation,
    tp_mult,
    sl_mult,
    max_bars,
    tp_mult * 0.0025 AS tp_pct,
    sl_mult * 0.0025 AS sl_pct,
    -- Counts
    toUInt32(count(*)) AS total_signals,
    toUInt32(countIf(exit_type = 'TP')) AS tp_count,
    toUInt32(countIf(exit_type = 'SL')) AS sl_count,
    toUInt32(countIf(exit_type = 'TIME')) AS time_count,
    toUInt32(countIf(exit_type = 'INCOMPLETE')) AS incomplete_count,
    -- Win rate (TP = win)
    countIf(exit_type = 'TP') / nullIf(countIf(exit_type IN ('TP', 'SL', 'TIME')), 0) AS win_rate,
    -- Profit factor = gross_wins / |gross_losses|
    sumIf((exit_price - entry_price) / entry_price, exit_type = 'TP' OR (exit_type = 'TIME' AND exit_price > entry_price))
        / nullIf(abs(sumIf((exit_price - entry_price) / entry_price, exit_type = 'SL' OR (exit_type = 'TIME' AND exit_price <= entry_price))), 0) AS profit_factor,
    -- Average win/loss percentages
    avgIf((exit_price - entry_price) / entry_price, exit_type = 'TP' OR (exit_type = 'TIME' AND exit_price > entry_price)) AS avg_win_pct,
    avgIf((exit_price - entry_price) / entry_price, exit_type = 'SL' OR (exit_type = 'TIME' AND exit_price <= entry_price)) AS avg_loss_pct,
    -- Risk-reward ratio
    avgIf((exit_price - entry_price) / entry_price, exit_type = 'TP' OR (exit_type = 'TIME' AND exit_price > entry_price))
        / nullIf(abs(avgIf((exit_price - entry_price) / entry_price, exit_type = 'SL' OR (exit_type = 'TIME' AND exit_price <= entry_price))), 0) AS risk_reward,
    -- Expected value per trade
    avgIf((exit_price - entry_price) / entry_price, exit_type != 'INCOMPLETE') AS expected_value_pct,
    -- Average bars held
    avgIf(exit_bar, exit_type != 'INCOMPLETE') AS avg_bars_held,
    -- Kelly fraction: WR - (1-WR)/RR
    countIf(exit_type = 'TP') / nullIf(countIf(exit_type IN ('TP', 'SL', 'TIME')), 0)
        - (1.0 - countIf(exit_type = 'TP') / nullIf(countIf(exit_type IN ('TP', 'SL', 'TIME')), 0))
          / nullIf(
              avgIf((exit_price - entry_price) / entry_price, exit_type = 'TP' OR (exit_type = 'TIME' AND exit_price > entry_price))
              / nullIf(abs(avgIf((exit_price - entry_price) / entry_price, exit_type = 'SL' OR (exit_type = 'TIME' AND exit_price <= entry_price))), 0)
            , 0) AS kelly_fraction
FROM trade_outcomes
WHERE exit_type != 'INCOMPLETE'
GROUP BY tp_mult, sl_mult, max_bars
-- Note: ORDER BY omitted for INSERT. Query results directly when needed.
