"""Verify champion pattern constants are consistent.

ADR: docs/adr/2026-02-06-repository-creation.md
"""

from rangebar_patterns.champion import CHAMPION, CROSS_ASSET, TEMPORAL_HIT_RATES


def test_champion_name():
    assert CHAMPION["name"] == "combo_2down_ti_p95_kyle_gt_0_long"


def test_champion_hit_rate_true_nla():
    assert 0.60 <= CHAMPION["hit_rate_true_nla"] <= 0.65


def test_champion_dsr():
    assert CHAMPION["dsr"] == 1.000


def test_champion_z_score():
    assert CHAMPION["z_score_true_nla"] > 1.96  # Statistically significant


def test_biased_higher_than_true_nla():
    assert CHAMPION["hit_rate_biased"] > CHAMPION["hit_rate_true_nla"]


def test_temporal_2024_2025_not_significant():
    assert not TEMPORAL_HIT_RATES[2024]["significant"]
    assert not TEMPORAL_HIT_RATES[2025]["significant"]


def test_temporal_early_years_significant():
    for year in [2020, 2021, 2022, 2023]:
        assert TEMPORAL_HIT_RATES[year]["significant"], f"{year} should be significant"


def test_cross_asset_eth_inverted():
    assert CROSS_ASSET["ETHUSDT"]["direction"] == "inverted"


def test_cross_asset_sol_long():
    assert CROSS_ASSET["SOLUSDT"]["direction"] == "long"
