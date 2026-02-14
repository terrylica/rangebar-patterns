"""Test multi-tier screening logic.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/16
"""

from rangebar_patterns.eval.screening import TIERS, individual_gate_pass, passes_tier


def test_tiers_defined():
    assert "tier1_exploratory" in TIERS
    assert "tier2_balanced" in TIERS
    assert "tier3_strict" in TIERS


def test_passes_tier_exploratory():
    cfg = {
        "kelly": 0.01,
        "omega": 1.1,
        "dsr": 0.3,
        "headroom": 0.5,
        "n_trades": 100,
        "tamrs": 0.10,
        "rachev": 1.5,
        "ou_ratio": 0.7,
    }
    result = passes_tier(cfg, TIERS["tier1_exploratory"])
    assert result is True


def test_passes_tier_strict_fails_weak():
    cfg = {
        "kelly": 0.001,
        "omega": 1.1,
        "dsr": 0.3,
        "headroom": 0.5,
        "n_trades": 100,
        "tamrs": 0.10,
        "rachev": 1.5,
        "ou_ratio": 0.7,
    }
    result = passes_tier(cfg, TIERS["tier3_strict"])
    assert result is False  # Kelly too low for strict (min 0.05)


def test_individual_gate_pass_returns_dict():
    cfg = {
        "kelly": 0.01,
        "omega": 1.1,
        "dsr": 0.3,
        "headroom": 0.5,
        "n_trades": 100,
        "tamrs": 0.10,
        "rachev": 1.5,
        "ou_ratio": 0.7,
    }
    result = individual_gate_pass(cfg, TIERS["tier1_exploratory"])
    assert isinstance(result, dict)
    assert result["kelly"] is True
    assert result["omega"] is True
    assert result["tamrs"] is True
    assert result["rachev"] is True
    assert result["ou_ratio"] is True


def test_individual_gate_fails_on_none():
    cfg = {
        "kelly": None,
        "omega": None,
        "dsr": None,
        "headroom": 0.0,
        "n_trades": 0,
        "tamrs": None,
        "rachev": None,
        "ou_ratio": None,
    }
    result = individual_gate_pass(cfg, TIERS["tier1_exploratory"])
    assert result["kelly"] is False
    assert result["omega"] is False
    assert result["tamrs"] is False
    assert result["rachev"] is False
