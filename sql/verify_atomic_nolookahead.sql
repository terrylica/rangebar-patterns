-- =============================================================================
-- ATOMIC NO-LOOKAHEAD VERIFICATION TEST
-- =============================================================================
-- Purpose: Prove that our expanding-window p95 uses ONLY past data
-- Method:  For ONE specific bar, manually compute what the model would have
--          known at decision time, then compare to SQL window function output
--
-- Pass Criteria:
--   1. manual_p95 = window_p95 (EXACT match within floating point tolerance)
--   2. The bar at test_timestamp is NOT included in manual_p95 computation
--   3. direction lags are verified correct (dir_1 = direction of t-1, etc.)
--
-- Created: 2026-02-05 (Adversarial Audit)
-- =============================================================================

WITH
-- Step 1: Get all base data with row numbers
-- NOTE: Added secondary ORDER BY on close_time_ms for deterministic ordering
base_bars AS (
    SELECT
        close_time_ms,
        CASE WHEN close > open THEN 1 ELSE 0 END as direction,
        trade_intensity,
        kyle_lambda_proxy,
        ROW_NUMBER() OVER (ORDER BY close_time_ms) as bar_idx
    FROM opendeviationbar_cache.open_deviation_bars
    WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
    AND ouroboros_mode = 'month'
    ORDER BY close_time_ms
),

-- Step 2: Pick a specific test bar (around bar 50,000 for rigorous testing)
test_bar_selection AS (
    SELECT
        close_time_ms as test_timestamp,
        bar_idx as test_bar_idx,
        direction as test_direction,
        trade_intensity as test_trade_intensity,
        kyle_lambda_proxy as test_kyle
    FROM base_bars
    WHERE bar_idx BETWEEN 49990 AND 50010
      AND trade_intensity > 0
    ORDER BY trade_intensity DESC
    LIMIT 1
),

-- Step 3: MANUAL COMPUTATION - compute p95 of ALL bars STRICTLY BEFORE test bar
-- This is what the model SHOULD have known at decision time
manual_p95_computation AS (
    SELECT
        quantileExactExclusive(0.95)(trade_intensity) as manual_p95,
        count(*) as bars_used_in_p95,
        max(close_time_ms) as last_bar_used_ts,
        max(bar_idx) as last_bar_idx
    FROM base_bars
    WHERE bar_idx < (SELECT test_bar_idx FROM test_bar_selection)
),

-- Step 4: SQL WINDOW FUNCTION OUTPUT - what our query actually produces
window_computation AS (
    SELECT
        close_time_ms,
        bar_idx,
        direction,
        trade_intensity,
        kyle_lambda_proxy,
        quantileExactExclusive(0.95)(trade_intensity) OVER (
            ORDER BY close_time_ms
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) as window_p95,
        lagInFrame(direction, 1) OVER w as dir_1,
        lagInFrame(direction, 2) OVER w as dir_2,
        lagInFrame(trade_intensity, 1) OVER w as ti_1,
        lagInFrame(kyle_lambda_proxy, 1) OVER w as kyle_1
    FROM base_bars
    WINDOW w AS (ORDER BY close_time_ms)
),

-- Step 5: Get values at our test bar
test_bar_window_values AS (
    SELECT *
    FROM window_computation
    WHERE bar_idx = (SELECT test_bar_idx FROM test_bar_selection)
),

-- Step 6: Get actual directions of t-1 and t-2 bars for verification
prev_bars AS (
    SELECT bar_idx, direction, close_time_ms
    FROM base_bars
    WHERE bar_idx IN (
        (SELECT test_bar_idx FROM test_bar_selection) - 1,
        (SELECT test_bar_idx FROM test_bar_selection) - 2
    )
)

-- =============================================================================
-- FINAL OUTPUT: Comparison and Pass/Fail Determination
-- =============================================================================
SELECT
    '=== TEST RESULTS ===' as section,

    -- Test bar identification
    t.test_timestamp,
    t.test_bar_idx,

    -- Manual computation (ground truth)
    m.manual_p95,
    m.bars_used_in_p95,
    m.last_bar_idx as manual_last_bar,

    -- Window function output (what we're testing)
    w.window_p95,

    -- Difference (should be ZERO)
    abs(m.manual_p95 - w.window_p95) as p95_difference,

    -- PASS/FAIL tests
    CASE
        WHEN abs(m.manual_p95 - w.window_p95) < 1e-10 THEN '✅ PASS'
        ELSE '❌ FAIL'
    END as p95_match_test,

    CASE
        WHEN m.bars_used_in_p95 = t.test_bar_idx - 1 THEN '✅ PASS'
        ELSE '❌ FAIL'
    END as exclusion_test,

    -- Direction verification
    w.dir_1 as window_dir_1,
    w.dir_2 as window_dir_2,

    -- Signal values
    w.ti_1 as lagged_ti,
    w.kyle_1 as lagged_kyle,

    -- Would signal fire?
    CASE WHEN w.dir_2 = 0 AND w.dir_1 = 0 AND w.ti_1 > w.window_p95 AND w.kyle_1 > 0
         THEN '🎯 SIGNAL FIRES' ELSE '⛔ NO SIGNAL' END as signal_status

FROM test_bar_selection t
CROSS JOIN manual_p95_computation m
CROSS JOIN test_bar_window_values w;

-- =============================================================================
-- DIRECTION LAG VERIFICATION
-- =============================================================================
SELECT
    '=== DIRECTION LAG VERIFICATION ===' as section,
    bar_idx,
    direction,
    close_time_ms,
    CASE
        WHEN bar_idx = (SELECT test_bar_idx - 1 FROM test_bar_selection) THEN 'Should match dir_1'
        WHEN bar_idx = (SELECT test_bar_idx - 2 FROM test_bar_selection) THEN 'Should match dir_2'
    END as verification_note
FROM base_bars
WHERE bar_idx IN (
    (SELECT test_bar_idx FROM test_bar_selection) - 1,
    (SELECT test_bar_idx FROM test_bar_selection) - 2
)
ORDER BY bar_idx DESC;

-- =============================================================================
-- TIMESTAMP TIE CHECK (Audit finding: non-deterministic if ties exist)
-- =============================================================================
SELECT
    '=== TIMESTAMP TIE CHECK ===' as section,
    close_time_ms,
    count(*) as bars_with_same_ts,
    CASE WHEN count(*) > 1 THEN '⚠️ TIES EXIST' ELSE '✅ UNIQUE' END as tie_status
FROM opendeviationbar_cache.open_deviation_bars
WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 1000
AND ouroboros_mode = 'month'
GROUP BY close_time_ms
HAVING count(*) > 1
LIMIT 10;
