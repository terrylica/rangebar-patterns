-- ============================================================================
-- Gen 202: Combined Barrier (TP + Trailing SL + Time) in ClickHouse SQL
-- GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/5
-- Copied from: gen200_triple_barrier.sql
--
-- PURPOSE: Combine fixed TP (from Gen200) with trailing stop loss (from Gen201)
-- and time barrier. Tests whether the trailing SL adds value when combined
-- with the TP barrier (Gen200 used fixed SL, Gen201 used trailing SL only).
--
-- KEY DIFFERENCE FROM GEN200:
--   Fixed SL (entry_price * (1 - sl_mult * threshold))
--   → Trailing SL (running_max * (1 - trail_mult * threshold))
--   Same TP barrier as Gen200
--
-- KEY DIFFERENCE FROM GEN201:
--   Identical barrier mechanics. Gen202 exists to compare against Gen200
--   with the same parameter grid and aggregation.
--
-- All Gen200 audit fixes preserved (#1-#9)
-- ============================================================================

-- Tables already created by gen200_triple_barrier.sql
-- Gen202 reuses barrier_results (sl_mult column stores trail_mult)

-- ============================================================================
-- Main query: Combined barrier sweep for SOL @250dbps
-- ============================================================================

-- Clear previous Gen202 results for this threshold
ALTER TABLE rangebar_cache.barrier_results
    DELETE WHERE generation = 202 AND symbol = 'SOLUSDT' AND threshold_decimal_bps = 250;

INSERT INTO rangebar_cache.barrier_results
    (symbol, threshold_decimal_bps, pattern_name, generation,
     tp_mult, sl_mult, max_bars, tp_pct, sl_pct,
     total_signals, tp_count, sl_count, time_count, incomplete_count,
     win_rate, profit_factor, avg_win_pct, avg_loss_pct, risk_reward,
     expected_value_pct, avg_bars_held, kelly_fraction)
WITH
-- bar_range = threshold_decimal_bps / 100000.0 = 0.0025 for @250dbps
-- CTEs 1-5 identical to Gen200 (signal detection + forward arrays)
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
        leadInFrame(open, 1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS entry_price
    FROM running_stats
    WINDOW w AS (ORDER BY timestamp_ms)
),
-- CTE 4: Filter to champion pattern signals ONLY
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
-- CTE 6: Parameter expansion — tp_mult + trail_mult (NOT sl_mult)
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
        arrayJoin([2.5, 5.0, 7.5, 10.0, 15.0]) AS trail_mult,
        arrayJoin(CAST([5, 10, 20, 50], 'Array(UInt32)')) AS max_bars
    FROM forward_arrays
),
-- CTE 6b: Pre-compute TP price + trailing SL arrays
-- Running max at each bar i = max(entry_price, max(fwd_highs[1..i]))
-- Trailing SL at each bar i = running_max[i] * (1 - trail_mult * bar_range)
param_with_trailing AS (
    SELECT
        *,
        entry_price * (1.0 + tp_mult * 0.0025) AS tp_price,
        trail_mult * 0.0025 AS trail_pct,
        -- Per-bar running max (seeded with entry_price)
        arrayMap(
            i -> greatest(entry_price, arrayReduce('max', arraySlice(fwd_highs, 1, i))),
            arrayEnumerate(fwd_highs)
        ) AS running_maxes
    FROM param_expanded
),
-- CTE 6c: Compute per-bar trailing SL from running maxes
param_with_prices AS (
    SELECT
        timestamp_ms, entry_price, signal_rn,
        fwd_highs, fwd_lows, fwd_opens, fwd_closes,
        tp_mult, trail_mult, max_bars, tp_price, trail_pct,
        running_maxes,
        arrayMap(rm -> rm * (1.0 - trail_pct), running_maxes) AS trailing_sls
    FROM param_with_trailing
),
-- CTE 7: Barrier scan — TP fixed + trailing SL dynamic
barrier_scan AS (
    SELECT
        timestamp_ms,
        entry_price,
        tp_mult,
        trail_mult,
        max_bars,
        tp_price,
        trailing_sls,
        fwd_opens,
        fwd_closes,
        fwd_lows,
        length(fwd_highs) AS available_bars,
        -- TP barrier (same as Gen200)
        arrayFirstIndex(x -> x >= tp_price, arraySlice(fwd_highs, 1, max_bars)) AS raw_tp_bar,
        -- Trailing SL barrier: low[i] <= trailing_sl[i]
        arrayFirstIndex(
            (l, ts) -> l <= ts,
            arraySlice(fwd_lows, 1, max_bars),
            arraySlice(trailing_sls, 1, max_bars)
        ) AS raw_trail_bar,
        length(arraySlice(fwd_highs, 1, max_bars)) AS window_bars
    FROM param_with_prices
),
-- CTE 8: Trade outcomes — trailing SL wins ties (same-bar ambiguity rule)
trade_outcomes AS (
    SELECT
        timestamp_ms,
        entry_price,
        tp_mult,
        trail_mult,
        max_bars,
        tp_price,
        CASE
            WHEN raw_trail_bar > 0 AND raw_tp_bar > 0 AND raw_trail_bar <= raw_tp_bar THEN 'TRAIL'
            WHEN raw_trail_bar > 0 AND raw_tp_bar > 0 AND raw_tp_bar < raw_trail_bar THEN 'TP'
            WHEN raw_trail_bar > 0 AND raw_tp_bar = 0 THEN 'TRAIL'
            WHEN raw_tp_bar > 0 AND raw_trail_bar = 0 THEN 'TP'
            WHEN window_bars >= max_bars THEN 'TIME'
            ELSE 'INCOMPLETE'
        END AS exit_type,
        CASE
            WHEN raw_trail_bar > 0 AND raw_tp_bar > 0 AND raw_trail_bar <= raw_tp_bar THEN raw_trail_bar
            WHEN raw_trail_bar > 0 AND raw_tp_bar > 0 AND raw_tp_bar < raw_trail_bar THEN raw_tp_bar
            WHEN raw_trail_bar > 0 AND raw_tp_bar = 0 THEN raw_trail_bar
            WHEN raw_tp_bar > 0 AND raw_trail_bar = 0 THEN raw_tp_bar
            WHEN window_bars >= max_bars THEN max_bars
            ELSE 0
        END AS exit_bar,
        CASE
            -- TRAIL: min(open, trailing_sl[bar]) for gap-down handling
            WHEN raw_trail_bar > 0 AND (raw_tp_bar = 0 OR raw_trail_bar <= raw_tp_bar)
                THEN least(fwd_opens[raw_trail_bar], trailing_sls[raw_trail_bar])
            -- TP: exact tp_price (limit fill)
            WHEN raw_tp_bar > 0 AND (raw_trail_bar = 0 OR raw_tp_bar < raw_trail_bar)
                THEN tp_price
            -- TIME: close at time barrier
            WHEN window_bars >= max_bars
                THEN fwd_closes[max_bars]
            ELSE 0
        END AS exit_price,
        raw_tp_bar,
        raw_trail_bar,
        window_bars
    FROM barrier_scan
)
-- Final SELECT: Aggregate metrics per parameter combo
-- TRAIL exits can be wins or losses (price-based, unlike Gen200 where SL = always loss)
SELECT
    'SOLUSDT' AS symbol,
    250 AS threshold_decimal_bps,
    'gen202_combined' AS pattern_name,
    202 AS generation,
    tp_mult,
    trail_mult AS sl_mult,  -- Store trail_mult in sl_mult column for schema compat
    max_bars,
    tp_mult * 0.0025 AS tp_pct,
    trail_mult * 0.0025 AS sl_pct,  -- trail_pct stored in sl_pct column
    -- Counts
    toUInt32(count(*)) AS total_signals,
    toUInt32(countIf(exit_type = 'TP')) AS tp_count,
    toUInt32(countIf(exit_type = 'TRAIL')) AS sl_count,  -- TRAIL → sl_count column
    toUInt32(countIf(exit_type = 'TIME')) AS time_count,
    toUInt32(countIf(exit_type = 'INCOMPLETE')) AS incomplete_count,
    -- Win rate: TP = win, TRAIL can be win or loss depending on exit price
    countIf(exit_type = 'TP' OR (exit_type = 'TRAIL' AND exit_price > entry_price))
        / nullIf(countIf(exit_type IN ('TP', 'TRAIL', 'TIME')), 0) AS win_rate,
    -- Profit factor = gross_wins / |gross_losses|
    sumIf((exit_price - entry_price) / entry_price, exit_price > entry_price AND exit_type != 'INCOMPLETE')
        / nullIf(abs(sumIf((exit_price - entry_price) / entry_price, exit_price <= entry_price AND exit_type != 'INCOMPLETE')), 0) AS profit_factor,
    -- Average win/loss percentages
    avgIf((exit_price - entry_price) / entry_price, exit_price > entry_price AND exit_type != 'INCOMPLETE') AS avg_win_pct,
    avgIf((exit_price - entry_price) / entry_price, exit_price <= entry_price AND exit_type != 'INCOMPLETE') AS avg_loss_pct,
    -- Risk-reward ratio
    avgIf((exit_price - entry_price) / entry_price, exit_price > entry_price AND exit_type != 'INCOMPLETE')
        / nullIf(abs(avgIf((exit_price - entry_price) / entry_price, exit_price <= entry_price AND exit_type != 'INCOMPLETE')), 0) AS risk_reward,
    -- Expected value per trade
    avgIf((exit_price - entry_price) / entry_price, exit_type != 'INCOMPLETE') AS expected_value_pct,
    -- Average bars held
    avgIf(exit_bar, exit_type != 'INCOMPLETE') AS avg_bars_held,
    -- Kelly fraction: WR - (1-WR)/RR
    countIf(exit_type = 'TP' OR (exit_type = 'TRAIL' AND exit_price > entry_price))
        / nullIf(countIf(exit_type IN ('TP', 'TRAIL', 'TIME')), 0)
        - (1.0 - countIf(exit_type = 'TP' OR (exit_type = 'TRAIL' AND exit_price > entry_price))
            / nullIf(countIf(exit_type IN ('TP', 'TRAIL', 'TIME')), 0))
          / nullIf(
              avgIf((exit_price - entry_price) / entry_price, exit_price > entry_price AND exit_type != 'INCOMPLETE')
              / nullIf(abs(avgIf((exit_price - entry_price) / entry_price, exit_price <= entry_price AND exit_type != 'INCOMPLETE')), 0)
            , 0) AS kelly_fraction
FROM trade_outcomes
WHERE exit_type != 'INCOMPLETE'
GROUP BY tp_mult, trail_mult, max_bars
