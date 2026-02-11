"""Test introspect.py — parse_config_id roundtrip + rendering.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/13
"""

import pytest


def test_parse_config_id_roundtrip():
    """Every config from generate_configs() must roundtrip through parse_config_id."""
    from rangebar_patterns.eval.extraction import generate_configs
    from rangebar_patterns.introspect import parse_config_id

    configs = generate_configs()
    assert len(configs) == 1008

    for config in configs:
        parsed = parse_config_id(config["config_id"])
        assert parsed["config_id"] == config["config_id"]
        assert parsed["feature_col_1"] == config["feature_col_1"]
        assert parsed["feature_col_2"] == config["feature_col_2"]
        assert parsed["quantile_pct_1"] == config["quantile_pct_1"]
        assert parsed["quantile_pct_2"] == config["quantile_pct_2"]
        assert parsed["direction_1"] == config["direction_1"]
        assert parsed["direction_2"] == config["direction_2"]


def test_parse_config_id_known_values():
    """Multi-word features parse correctly."""
    from rangebar_patterns.introspect import parse_config_id

    # volume_per_trade (3-word feature)
    result = parse_config_id("volume_per_trade_gt_p75__duration_us_lt_p25")
    assert result["feature_col_1"] == "volume_per_trade"
    assert result["feature_col_2"] == "duration_us"
    assert result["quantile_pct_1"] == "0.75"
    assert result["direction_1"] == ">"
    assert result["quantile_pct_2"] == "0.25"
    assert result["direction_2"] == "<"

    # vwap_close_deviation (3-word feature)
    result = parse_config_id("vwap_close_deviation_lt_p10__aggregation_density_gt_p90")
    assert result["feature_col_1"] == "vwap_close_deviation"
    assert result["feature_col_2"] == "aggregation_density"
    assert result["quantile_pct_1"] == "0.10"
    assert result["direction_1"] == "<"
    assert result["quantile_pct_2"] == "0.90"
    assert result["direction_2"] == ">"


def test_parse_config_id_simple_features():
    """Single-word features parse correctly."""
    from rangebar_patterns.introspect import parse_config_id

    result = parse_config_id("ofi_gt_p50__price_impact_lt_p50")
    assert result["feature_col_1"] == "ofi"
    assert result["feature_col_2"] == "price_impact"
    assert result["quantile_pct_1"] == "0.50"
    assert result["direction_1"] == ">"
    assert result["quantile_pct_2"] == "0.50"
    assert result["direction_2"] == "<"


def test_parse_config_id_invalid_no_separator():
    """Missing __ separator raises ValueError."""
    from rangebar_patterns.introspect import parse_config_id

    with pytest.raises(ValueError, match="exactly one '__'"):
        parse_config_id("ofi_gt_p50_price_impact_lt_p50")


def test_parse_config_id_invalid_unknown_feature():
    """Unknown feature raises ValueError."""
    from rangebar_patterns.introspect import parse_config_id

    with pytest.raises(ValueError, match="Cannot parse config half"):
        parse_config_id("unknown_feature_gt_p50__ofi_lt_p50")


def test_parse_config_id_invalid_unknown_qualifier():
    """Unknown qualifier raises ValueError."""
    from rangebar_patterns.introspect import parse_config_id

    with pytest.raises(ValueError, match="Cannot parse config half"):
        parse_config_id("ofi_gt_p99__price_impact_lt_p50")


# ---------------------------------------------------------------------------
# SQL construction tests (Gate G2)
# ---------------------------------------------------------------------------


def test_build_inspect_sql_trade_list():
    """trade_list SQL contains expected clauses and no unresolved placeholders."""
    from rangebar_patterns.introspect import build_inspect_sql, parse_config_id

    config = parse_config_id("ofi_gt_p50__price_impact_lt_p50")
    sql = build_inspect_sql(config, "trade_list")

    assert "row_number() OVER" in sql
    assert "trade_outcomes" in sql
    assert "exit_type != 'INCOMPLETE'" in sql
    assert "ORDER BY timestamp_ms" in sql
    # No unresolved format placeholders
    assert "{" not in sql
    assert "}" not in sql


def test_build_inspect_sql_trade_detail():
    """trade_detail SQL contains ARRAY JOIN and barrier columns."""
    from rangebar_patterns.introspect import build_inspect_sql, parse_config_id

    config = parse_config_id(
        "price_impact_lt_p10__volume_per_trade_gt_p75"
    )
    sql = build_inspect_sql(config, "trade_detail", signal_ts=1700000000000)

    assert "ARRAY JOIN" in sql
    assert "barrier_scan" in sql
    assert "exit_bar" in sql
    assert "tp_distance" in sql
    assert "sl_distance" in sql
    assert "running_pnl" in sql
    assert "1700000000000" in sql
    # No unresolved format placeholders
    assert "{" not in sql
    assert "}" not in sql


def test_build_inspect_sql_trade_detail_requires_signal_ts():
    """trade_detail without signal_ts raises ValueError."""
    from rangebar_patterns.introspect import build_inspect_sql, parse_config_id

    config = parse_config_id("ofi_gt_p50__price_impact_lt_p50")
    with pytest.raises(ValueError, match="signal_ts required"):
        build_inspect_sql(config, "trade_detail")


def test_build_inspect_sql_unknown_mode():
    """Unknown mode raises ValueError."""
    from rangebar_patterns.introspect import build_inspect_sql, parse_config_id

    config = parse_config_id("ofi_gt_p50__price_impact_lt_p50")
    with pytest.raises(ValueError, match="Unknown mode"):
        build_inspect_sql(config, "bogus")


# ---------------------------------------------------------------------------
# Renderer smoke tests (T4)
# ---------------------------------------------------------------------------


def _make_synthetic_detail():
    """Create a synthetic trade detail dict for renderer testing."""
    return {
        "config": {
            "config_id": "ofi_gt_p50__price_impact_lt_p50",
            "feature_col_1": "ofi",
            "feature_col_2": "price_impact",
            "quantile_pct_1": "0.50",
            "quantile_pct_2": "0.50",
            "direction_1": ">",
            "direction_2": "<",
        },
        "trade_meta": {"trade_n": 42, "timestamp_ms": 1700000000000},
        "signal_ts": 1700000000000,
        "entry_price": 152.340,
        "exit_price": 152.720,
        "exit_type": "TP",
        "tp_price": 152.720,
        "sl_price": 151.960,
        "tp_mult": 0.5,
        "sl_mult": 0.25,
        "max_bars": 50,
        "feature1_name": "ofi",
        "feature1_value": 0.15,
        "feature1_threshold": 0.10,
        "feature2_name": "price_impact",
        "feature2_value": 0.005,
        "feature2_threshold": 0.001,
        "bars": [
            {
                "bar_idx": 1,
                "open": 152.340,
                "high": 152.450,
                "low": 152.310,
                "close": 152.420,
                "tp_distance": 0.170,
                "sl_distance": -0.270,
                "running_pnl": 0.00053,
            },
            {
                "bar_idx": 2,
                "open": 152.420,
                "high": 152.720,
                "low": 152.400,
                "close": 152.720,
                "tp_distance": 0.0,
                "sl_distance": -0.440,
                "running_pnl": 0.00249,
            },
        ],
    }


def test_render_summary_contains_key_fields():
    """Summary includes trade number, config, entry/exit, P&L."""
    from rangebar_patterns.introspect import render_summary

    detail = _make_synthetic_detail()
    output = render_summary(detail, total_trades=1503)

    assert "Trade #42 / 1503" in output
    assert "ofi_gt_p50__price_impact_lt_p50" in output
    assert "152.340" in output
    assert "152.720" in output
    assert "TP" in output
    assert "2 / 50 max" in output


def test_render_feature_diagnostic_pass_fail():
    """Feature diagnostic shows YES/NO for quantile pass/fail."""
    from rangebar_patterns.introspect import render_feature_diagnostic

    detail = _make_synthetic_detail()
    output = render_feature_diagnostic(detail)

    assert "Feature Diagnostic:" in output
    assert "ofi" in output
    assert "price_impact" in output
    assert "YES" in output
    assert "NO" in output


def test_render_barrier_progression_header():
    """Barrier progression has correct column headers."""
    from rangebar_patterns.introspect import render_barrier_progression

    detail = _make_synthetic_detail()
    output = render_barrier_progression(detail)

    assert "Barrier Progression:" in output
    assert "Bar" in output
    assert "Open" in output
    assert "->TP" in output
    assert "->SL" in output
    assert "P&L" in output


def test_export_json_valid():
    """JSON export produces valid JSON."""
    import json

    from rangebar_patterns.introspect import export_json

    detail = _make_synthetic_detail()
    output = export_json(detail)
    parsed = json.loads(output)

    assert parsed["config"]["config_id"] == "ofi_gt_p50__price_impact_lt_p50"
    assert parsed["exit_type"] == "TP"
    assert len(parsed["bars"]) == 2
