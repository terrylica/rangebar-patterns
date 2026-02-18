"""Test config.py typed env reader.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""


def test_defaults():
    from rangebar_patterns.config import (
        ALPHA,
        BAR_RANGE,
        DSR_THRESHOLD,
        MAX_BARS,
        N_TRIALS,
        SL_MULT,
        SYMBOL,
        THRESHOLD_DBPS,
        TP_MULT,
    )

    assert SYMBOL == "SOLUSDT"
    assert THRESHOLD_DBPS == 500
    assert BAR_RANGE == 0.005
    assert TP_MULT == 5.0
    assert SL_MULT == 2.5
    assert MAX_BARS == 50
    assert N_TRIALS == 1008
    assert ALPHA == 0.05
    assert DSR_THRESHOLD == 0.95


def test_bar_range_derived():
    from rangebar_patterns.config import BAR_RANGE, THRESHOLD_DBPS

    assert BAR_RANGE == THRESHOLD_DBPS / 100_000.0


def test_env_override(monkeypatch):
    monkeypatch.setenv("RBP_SYMBOL", "ETHUSDT")
    monkeypatch.setenv("RBP_THRESHOLD_DBPS", "250")

    # Reimport to pick up env changes
    import importlib

    import rangebar_patterns.config as cfg

    importlib.reload(cfg)

    assert cfg.SYMBOL == "ETHUSDT"
    assert cfg.THRESHOLD_DBPS == 250
    assert cfg.BAR_RANGE == 0.0025

    # Restore defaults
    monkeypatch.delenv("RBP_SYMBOL")
    monkeypatch.delenv("RBP_THRESHOLD_DBPS")
    importlib.reload(cfg)
