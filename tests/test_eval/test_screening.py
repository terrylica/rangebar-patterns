"""Test multi-tier screening logic.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/16
GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/17
"""

from rangebar_patterns.eval.screening import TIERS, individual_gate_pass, passes_tier


def test_tiers_defined():
    assert "tier1_exploratory" in TIERS
    assert "tier2_balanced" in TIERS
    assert "tier3_strict" in TIERS


def test_kelly_removed_from_tiers():
    """Kelly was removed as a gate (Issue #17)."""
    for tier_name, thresholds in TIERS.items():
        assert "kelly_min" not in thresholds, f"kelly_min still in {tier_name}"


def test_regularity_gates_in_tiers():
    """Signal regularity gates added (Issue #17)."""
    for tier_name, thresholds in TIERS.items():
        assert "regularity_cv_max" in thresholds, f"regularity_cv_max missing from {tier_name}"
        assert "coverage_min" in thresholds, f"coverage_min missing from {tier_name}"


def test_passes_tier_exploratory():
    cfg = {
        "omega": 1.1,
        "dsr": 0.3,
        "headroom": 0.5,
        "n_trades": 100,
        "tamrs": 0.10,
        "rachev": 1.5,
        "ou_ratio": 0.7,
        "regularity_cv": 0.3,
        "temporal_coverage": 0.8,
    }
    result = passes_tier(cfg, TIERS["tier1_exploratory"])
    assert result is True


def test_passes_tier_strict_fails_low_omega():
    cfg = {
        "omega": 1.01,
        "dsr": 0.3,
        "headroom": 0.5,
        "n_trades": 100,
        "tamrs": 0.20,
        "rachev": 1.5,
        "ou_ratio": 0.7,
        "regularity_cv": 0.3,
        "temporal_coverage": 0.8,
    }
    result = passes_tier(cfg, TIERS["tier3_strict"])
    assert result is False  # Omega too low for strict (min 1.05)


def test_passes_tier_strict_fails_high_regularity_cv():
    cfg = {
        "omega": 1.2,
        "dsr": 0.3,
        "headroom": 0.5,
        "n_trades": 100,
        "tamrs": 0.20,
        "rachev": 1.5,
        "ou_ratio": 0.7,
        "regularity_cv": 0.8,
        "temporal_coverage": 0.8,
    }
    result = passes_tier(cfg, TIERS["tier3_strict"])
    assert result is False  # regularity_cv 0.8 > 0.50 max for strict


def test_passes_tier_strict_fails_low_coverage():
    cfg = {
        "omega": 1.2,
        "dsr": 0.3,
        "headroom": 0.5,
        "n_trades": 100,
        "tamrs": 0.20,
        "rachev": 1.5,
        "ou_ratio": 0.7,
        "regularity_cv": 0.3,
        "temporal_coverage": 0.5,
    }
    result = passes_tier(cfg, TIERS["tier3_strict"])
    assert result is False  # coverage 0.5 < 0.70 min for strict


def test_individual_gate_pass_returns_dict():
    cfg = {
        "omega": 1.1,
        "dsr": 0.3,
        "headroom": 0.5,
        "n_trades": 100,
        "tamrs": 0.10,
        "rachev": 1.5,
        "ou_ratio": 0.7,
        "regularity_cv": 0.3,
        "temporal_coverage": 0.8,
    }
    result = individual_gate_pass(cfg, TIERS["tier1_exploratory"])
    assert isinstance(result, dict)
    assert "kelly" not in result  # Kelly removed
    assert result["omega"] is True
    assert result["tamrs"] is True
    assert result["rachev"] is True
    assert result["ou_ratio"] is True
    assert result["regularity_cv"] is True
    assert result["temporal_coverage"] is True


def test_individual_gate_fails_on_none():
    cfg = {
        "omega": None,
        "dsr": None,
        "headroom": 0.0,
        "n_trades": 0,
        "tamrs": None,
        "rachev": None,
        "ou_ratio": None,
        "regularity_cv": None,
        "temporal_coverage": None,
    }
    result = individual_gate_pass(cfg, TIERS["tier1_exploratory"])
    assert result["omega"] is False
    assert result["tamrs"] is False
    assert result["rachev"] is False
