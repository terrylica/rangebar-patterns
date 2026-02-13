-- Gen600 Oracle: Per-trade output for exh_l__opposite_wick_pct_lt_p50__intra_garman_klass_vol_gt_p50
-- Inverted barrier (TP=0.25x, SL=0.50x, max_bars=100)
-- Symbol/threshold substituted by caller via sed
--
-- Pattern: Single DOWN bar + intra_max_drawdown > p75_rolling (exhaustion long)
-- Feature1: opposite_wick_pct < rolling p50 (within signal set)
-- Feature2: intra_garman_klass_vol > rolling p50 (within signal set)
WITH
base_bars AS (
    SELECT
        timestamp_ms,
        open, high, low, close,
        intra_max_drawdown,
        intra_garman_klass_vol,
        -- Computed: direction-aware opposite wick percentage
        CASE
            WHEN close <= open THEN (high - open) / nullIf(high - low, 0)   -- DOWN: upper wick
            ELSE (open - low) / nullIf(high - low, 0)                        -- UP: lower wick
        END AS opposite_wick_pct,
        -- Forward arrays (AP-14: window-based, NOT self-join)
        arraySlice(groupArray(high) OVER (
            ORDER BY timestamp_ms ROWS BETWEEN CURRENT ROW AND 101 FOLLOWING
        ), 2, 101) AS fwd_highs,
        arraySlice(groupArray(low) OVER (
            ORDER BY timestamp_ms ROWS BETWEEN CURRENT ROW AND 101 FOLLOWING
        ), 2, 101) AS fwd_lows,
        arraySlice(groupArray(open) OVER (
            ORDER BY timestamp_ms ROWS BETWEEN CURRENT ROW AND 101 FOLLOWING
        ), 2, 101) AS fwd_opens,
        arraySlice(groupArray(close) OVER (
            ORDER BY timestamp_ms ROWS BETWEEN CURRENT ROW AND 101 FOLLOWING
        ), 2, 101) AS fwd_closes,
        CASE WHEN close > open THEN 1 ELSE 0 END AS direction,
        row_number() OVER (ORDER BY timestamp_ms) AS rn
    FROM rangebar_cache.range_bars
    WHERE symbol = '__SYMBOL__'
      AND threshold_decimal_bps = __THRESHOLD__
      AND timestamp_ms <= 1738713600000
    ORDER BY timestamp_ms
),
running_stats AS (
    SELECT
        *,
        quantileExactExclusive(0.75)(intra_max_drawdown) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
        ) AS mdd_p75_rolling
    FROM base_bars
),
signal_detection AS (
    SELECT
        timestamp_ms,
        open, high, low, close,
        direction,
        rn,
        -- AP-15: current row IS the last pattern bar
        direction AS dir_0,
        intra_max_drawdown AS intra_mdd_0,
        lagInFrame(mdd_p75_rolling, 0) OVER w AS mdd_p75_prior,
        opposite_wick_pct AS feature1_val,
        intra_garman_klass_vol AS feature2_val,
        leadInFrame(open, 1) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS entry_price,
        fwd_highs, fwd_lows, fwd_opens, fwd_closes
    FROM running_stats
    WINDOW w AS (ORDER BY timestamp_ms)
),
champion_signals AS (
    SELECT *
    FROM signal_detection
    WHERE dir_0 = 0
      AND intra_mdd_0 IS NOT NULL
      AND intra_mdd_0 > mdd_p75_prior
      AND rn > 1000
      AND mdd_p75_prior IS NOT NULL
      AND entry_price IS NOT NULL
      AND entry_price > 0
      AND feature1_val IS NOT NULL
      AND feature2_val IS NOT NULL
),
feature1_with_quantile AS (
    SELECT
        *,
        quantileExactExclusive(0.50)(feature1_val) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
        ) AS feature1_q
    FROM champion_signals
),
feature2_with_quantile AS (
    SELECT
        *,
        quantileExactExclusive(0.50)(feature2_val) OVER (
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
      AND feature1_val < feature1_q
      AND feature2_val > feature2_q
),
barrier_params AS (
    SELECT
        s.timestamp_ms,
        s.entry_price,
        s.entry_price * (1.0 + 0.25 * (__THRESHOLD__ / 10000.0)) AS tp_price,
        s.entry_price * (1.0 - 0.50 * (__THRESHOLD__ / 10000.0)) AS sl_price,
        toUInt32(100) AS max_bars,
        s.fwd_highs, s.fwd_lows, s.fwd_opens, s.fwd_closes
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
        END AS exit_price
    FROM barrier_scan
)
SELECT
    timestamp_ms,
    entry_price,
    exit_type,
    exit_price,
    exit_bar
FROM trade_outcomes
WHERE exit_type != 'INCOMPLETE'
ORDER BY timestamp_ms
FORMAT TabSeparatedWithNames;
