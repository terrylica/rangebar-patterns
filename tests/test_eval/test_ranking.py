"""Test per-metric percentile ranking with cutoffs and intersection.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/17
"""

import importlib
import os
from unittest.mock import patch

from rangebar_patterns.eval.ranking import (
    DEFAULT_METRICS,
    MetricSpec,
    apply_cutoff,
    intersection,
    load_metric_data,
    overlap_count,
    percentile_ranks,
    resolve_cutoffs,
    tightening_analysis,
)


def test_percentile_ranks_basic():
    """3 values -> correct percentile assignment."""
    values = {"a": 10.0, "b": 20.0, "c": 30.0}
    result = percentile_ranks(values, higher_is_better=True)
    assert result["a"] < result["b"] < result["c"]
    assert result["c"] == 100.0


def test_percentile_ranks_none_gets_zero():
    """None values get percentile 0."""
    values = {"a": 10.0, "b": None, "c": 30.0}
    result = percentile_ranks(values, higher_is_better=True)
    assert result["b"] == 0.0
    assert result["a"] > 0
    assert result["c"] > 0


def test_percentile_ranks_lower_is_better():
    """Lower-is-better metrics: lowest raw value gets highest percentile."""
    values = {"a": 0.1, "b": 0.5, "c": 0.9}
    result = percentile_ranks(values, higher_is_better=False)
    assert result["a"] > result["b"] > result["c"]
    assert result["a"] == 100.0


def test_percentile_ranks_ties():
    """Tied values get average rank."""
    values = {"a": 10.0, "b": 10.0, "c": 20.0}
    result = percentile_ranks(values, higher_is_better=True)
    assert result["a"] == result["b"]
    assert result["c"] > result["a"]


def test_apply_cutoff_50():
    """Top 50% of 4 configs -> 3 survive (threshold = pct >= 50)."""
    pct_ranks = {"a": 25.0, "b": 50.0, "c": 75.0, "d": 100.0}
    result = apply_cutoff(pct_ranks, cutoff=50)
    assert len(result) == 3
    assert "b" in result  # exactly at threshold
    assert "c" in result
    assert "d" in result
    assert "a" not in result


def test_apply_cutoff_100():
    """cutoff=100 -> all survive."""
    pct_ranks = {"a": 10.0, "b": 50.0, "c": 90.0}
    result = apply_cutoff(pct_ranks, cutoff=100)
    assert result == {"a", "b", "c"}


def test_apply_cutoff_0():
    """cutoff=0 -> none survive."""
    pct_ranks = {"a": 10.0, "b": 50.0, "c": 90.0}
    result = apply_cutoff(pct_ranks, cutoff=0)
    assert result == set()


def test_intersection_two_metrics():
    """Intersection of two metric pass-sets."""
    per_metric_pass = {
        "tamrs": {"a", "b", "c"},
        "omega": {"b", "c", "d"},
    }
    result = intersection(per_metric_pass)
    assert result == {"b", "c"}


def test_intersection_empty():
    """Disjoint pass-sets -> empty intersection."""
    per_metric_pass = {
        "tamrs": {"a", "b"},
        "omega": {"c", "d"},
    }
    result = intersection(per_metric_pass)
    assert result == set()


def test_overlap_count():
    """Config in 4/5 metric pass-sets -> count=4."""
    per_metric_pass = {
        "m1": {"a", "b"},
        "m2": {"a", "c"},
        "m3": {"a", "b", "c"},
        "m4": {"d"},
        "m5": {"a", "d"},
    }
    result = overlap_count(per_metric_pass, ["a", "b", "c", "d"])
    assert result["a"] == 4
    assert result["b"] == 2
    assert result["c"] == 2
    assert result["d"] == 2


def test_tightening_analysis():
    """Intersection shrinks as cutoff tightens."""
    pct_ranks_m1 = {"a": 90.0, "b": 70.0, "c": 50.0, "d": 30.0}
    pct_ranks_m2 = {"a": 80.0, "b": 60.0, "c": 40.0, "d": 20.0}
    all_pct_ranks = {"m1": pct_ranks_m1, "m2": pct_ranks_m2}
    result = tightening_analysis(all_pct_ranks, cutoff_levels=[100, 50, 20])
    assert result[0]["n_intersection"] == 4
    assert result[1]["n_intersection"] < 4
    assert result[2]["n_intersection"] <= result[1]["n_intersection"]


def test_resolve_cutoffs_default():
    """No env override -> all 100 (wide open)."""
    cutoffs = resolve_cutoffs()
    for spec in DEFAULT_METRICS:
        assert cutoffs[spec.name] == 100


def test_resolve_cutoffs_override():
    """RBP_RANK_CUT_TAMRS=10 -> tamrs cutoff is 10."""
    with patch.dict(os.environ, {"RBP_RANK_CUT_TAMRS": "10"}):
        from rangebar_patterns import config

        importlib.reload(config)
        try:
            cutoffs = resolve_cutoffs()
            assert cutoffs["tamrs"] == 10
        finally:
            importlib.reload(config)


def test_load_metric_data_missing_file(tmp_path):
    """Missing JSONL -> empty dict (graceful)."""
    specs = (
        MetricSpec("fake", "Fake", True, 100, "nonexistent.jsonl", "value"),
    )
    result = load_metric_data(tmp_path, specs)
    assert result["fake"] == {}
