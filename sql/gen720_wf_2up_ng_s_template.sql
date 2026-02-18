-- ============================================================================
-- Gen 720: Walk-Forward Barrier Optimization — 2up_ng Formation (SHORT)
--
-- PURPOSE: Extract all (signal × barrier) outcomes for walk-forward validation.
-- Each row = one trade (signal + barrier combo) with per-trade return.
-- Python WFO engine (walk_forward.py) handles windowing, CV, bootstrap.
--
-- FORMATION: 2 consecutive UP bars (no gate)
-- DIRECTION: SHORT (sell on next-bar open after signal)
-- STRATEGY: A (LONG-mirrored time-decay — wide SL first, then tight)
-- NO 2F FEATURE FILTER — raw formation signals for maximum WFO data.
--
-- BARRIER GRID: 434 combos inline via arrayJoin CROSS JOIN
--   phase1_bars:  [2, 3, 5, 7, 10, 15, 20, 30]     (8 values)
--   sl_tight_mult: [0.75, 0.50, 0.35, 0.25, 0.10, 0.05, 0.00] (7 values)
--   max_bars:     [10, 15, 20, 30, 50, 75, 100, 150, 200]      (9 values)
--   WHERE phase1_bars < max_bars = 434 valid combos
--
-- PARAMETERS (substituted by generate.sh via sed):
--   __SYMBOL__           — Trading pair (e.g., SOLUSDT)
--   __THRESHOLD_DBPS__   — Range bar threshold in decimal bps (e.g., 500)
--   __END_TS_MS__        — Common end timestamp for cross-asset alignment
--   __BAR_COUNT__        — Aligned bar count (200000/85000/45000)
--
-- COMPLIANCE:
--   AP-14: Window-based forward arrays (NOT self-join)
--   AP-15: Current row IS the last pattern bar
--   Rolling 1000-bar quantile for trade_intensity (never expanding)
--
-- GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/28
-- ============================================================================

WITH
-- Aligned bar selection: last __BAR_COUNT__ bars before __END_TS_MS__
aligned_bars AS (
    SELECT *
    FROM (
        SELECT *
        FROM rangebar_cache.range_bars
        WHERE symbol = '__SYMBOL__'
          AND threshold_decimal_bps = __THRESHOLD_DBPS__
          AND timestamp_ms <= __END_TS_MS__
        ORDER BY timestamp_ms DESC
        LIMIT __BAR_COUNT__
    )
    ORDER BY timestamp_ms ASC
),
base_bars AS (
    SELECT
        timestamp_ms,
        open, high, low, close,
        trade_intensity,
        kyle_lambda_proxy,
        -- Forward arrays (AP-14: window-based, NOT self-join)
        -- max max_bars = 200, so 201 FOLLOWING captures all
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
    FROM aligned_bars
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
-- 2up_ng formation: 2 consecutive UP bars (no gate) — SHORT
formation_signals AS (
    SELECT *
    FROM signal_detection
    WHERE dir_1 = 1 AND dir_0 = 1
      AND rn > 1000
      AND entry_price IS NOT NULL
      AND entry_price > 0
),
-- 434-combo barrier grid (inline, no external params)
barrier_grid AS (
    SELECT
        phase1_bars,
        sl_tight_mult,
        max_bars,
        concat('p', toString(phase1_bars),
               '_slt', lpad(toString(toUInt32(sl_tight_mult * 10)), 3, '0'),
               '_mb', toString(max_bars)) AS barrier_id
    FROM (
        SELECT
            arrayJoin([2, 3, 5, 7, 10, 15, 20, 30]) AS phase1_bars,
            arrayJoin([7.5, 5.0, 3.5, 2.5, 1.0, 0.5, 0.0]) AS sl_tight_mult,
            arrayJoin([10, 15, 20, 30, 50, 75, 100, 150, 200]) AS max_bars
    )
    WHERE phase1_bars < max_bars
),
-- CROSS JOIN: each signal × each barrier config
signal_barrier AS (
    SELECT
        s.timestamp_ms AS signal_ts_ms,
        s.entry_price,
        s.fwd_highs,
        s.fwd_lows,
        s.fwd_opens,
        s.fwd_closes,
        s.rn AS signal_rn,
        g.barrier_id,
        g.phase1_bars,
        g.sl_tight_mult,
        g.max_bars,
        -- Barrier prices (SHORT direction)
        s.entry_price * (1.0 - 2.5 * (__THRESHOLD_DBPS__ / 100000.0)) AS tp_price,
        s.entry_price * (1.0 + 5.0 * (__THRESHOLD_DBPS__ / 100000.0)) AS sl_wide_price,
        s.entry_price * (1.0 + g.sl_tight_mult * (__THRESHOLD_DBPS__ / 100000.0)) AS sl_tight_price
    FROM formation_signals s
    CROSS JOIN barrier_grid g
),
barrier_scan AS (
    SELECT
        signal_ts_ms,
        entry_price,
        barrier_id,
        phase1_bars,
        max_bars,
        tp_price,
        sl_wide_price,
        sl_tight_price,
        fwd_opens,
        fwd_closes,
        length(fwd_highs) AS available_bars,
        -- TP scans full window (SHORT: price must fall to tp_price)
        arrayFirstIndex(x -> x <= tp_price, arraySlice(fwd_lows, 1, max_bars)) AS raw_tp_bar,
        -- Segment 1: bars 1..phase1_bars with WIDE SL (SHORT: price rises to sl)
        arrayFirstIndex(x -> x >= sl_wide_price, arraySlice(fwd_highs, 1, phase1_bars)) AS raw_sl_seg1,
        -- Segment 2: bars phase1_bars+1..max_bars with TIGHT SL
        arrayFirstIndex(x -> x >= sl_tight_price,
            arraySlice(fwd_highs, phase1_bars + 1, max_bars - phase1_bars)
        ) AS raw_sl_seg2_local,
        length(arraySlice(fwd_highs, 1, max_bars)) AS window_bars
    FROM signal_barrier
),
barrier_merged AS (
    SELECT
        *,
        -- Combine SL segments: seg1 hit takes priority (earlier), then seg2 offset
        CASE
            WHEN raw_sl_seg1 > 0 THEN raw_sl_seg1
            WHEN raw_sl_seg2_local > 0 THEN raw_sl_seg2_local + phase1_bars
            ELSE 0
        END AS raw_sl_bar,
        -- Track which SL price was hit (for exit_price)
        CASE
            WHEN raw_sl_seg1 > 0 THEN sl_wide_price
            WHEN raw_sl_seg2_local > 0 THEN sl_tight_price
            ELSE 0
        END AS effective_sl_price
    FROM barrier_scan
),
trade_outcomes AS (
    SELECT
        signal_ts_ms,
        entry_price,
        barrier_id,
        tp_price,
        sl_wide_price,
        sl_tight_price,
        phase1_bars,
        max_bars,
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
            -- AP-13 mirror: Gap-up SL execution = greatest(open, sl_price)
            WHEN raw_sl_bar > 0 AND (raw_tp_bar = 0 OR raw_sl_bar <= raw_tp_bar)
                THEN greatest(fwd_opens[raw_sl_bar], effective_sl_price)
            WHEN raw_tp_bar > 0 AND (raw_sl_bar = 0 OR raw_tp_bar < raw_sl_bar)
                THEN tp_price
            WHEN window_bars >= max_bars
                THEN fwd_closes[max_bars]
            ELSE 0
        END AS exit_price
    FROM barrier_merged
)
SELECT
    '2up_ng_s' AS formation,
    barrier_id,
    signal_ts_ms,
    entry_price,
    exit_type,
    exit_bar,
    exit_price,
    (entry_price - exit_price) / entry_price AS return_pct,
    tp_price,
    sl_wide_price,
    sl_tight_price,
    phase1_bars,
    max_bars
FROM trade_outcomes
WHERE exit_type != 'INCOMPLETE'
FORMAT TabSeparatedWithNames;
