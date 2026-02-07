-- ============================================================================
-- Gen 300: Results table for feature filter brute-force sweep
-- GitHub Issue: TBD
--
-- PURPOSE: Store metrics from Gen300 sweep — 8 features × 6 quantile/direction
-- configs = 48 single-feature configurations, plus multi-feature combos (Phase 2).
-- ============================================================================

CREATE TABLE IF NOT EXISTS rangebar_cache.gen300_results (
    symbol String,
    threshold_decimal_bps UInt32,
    generation UInt32,
    config_id String,
    feature_name String,
    feature_column String,
    quantile_level Float64,
    filter_direction String,
    -- Barrier parameters (fixed for Phase 1)
    tp_mult Float64,
    sl_mult Float64,
    max_bars UInt32,
    tp_pct Float64,
    sl_pct Float64,
    -- Signal counts
    base_signals UInt32,
    filtered_signals UInt32,
    filter_ratio Float64,
    -- Barrier outcomes
    tp_count UInt32,
    sl_count UInt32,
    time_count UInt32,
    incomplete_count UInt32,
    -- Metrics
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
ORDER BY (symbol, threshold_decimal_bps, generation, config_id);
