"""Test config.py typed env reader.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""


def test_defaults():
    from rangebar_patterns.config import (
        ALPHA,
        DSR_THRESHOLD,
        MAX_BARS,
        N_TRIALS,
        SL_MULT,
        SYMBOL,
        THRESHOLD_DBPS,
        THRESHOLD_PCT,
        TP_MULT,
    )

    assert SYMBOL == "SOLUSDT"
    assert THRESHOLD_DBPS == 500
    assert THRESHOLD_PCT == 0.05
    assert TP_MULT == 0.5
    assert SL_MULT == 0.25
    assert MAX_BARS == 50
    assert N_TRIALS == 1008
    assert ALPHA == 0.05
    assert DSR_THRESHOLD == 0.95


def test_threshold_pct_derived():
    from rangebar_patterns.config import THRESHOLD_DBPS, THRESHOLD_PCT

    assert THRESHOLD_PCT == THRESHOLD_DBPS / 10000.0


def test_env_override(monkeypatch):
    monkeypatch.setenv("RBP_SYMBOL", "ETHUSDT")
    monkeypatch.setenv("RBP_THRESHOLD_DBPS", "250")

    # Reimport to pick up env changes
    import importlib

    import rangebar_patterns.config as cfg

    importlib.reload(cfg)

    assert cfg.SYMBOL == "ETHUSDT"
    assert cfg.THRESHOLD_DBPS == 250
    assert cfg.THRESHOLD_PCT == 0.025

    # Restore defaults
    monkeypatch.delenv("RBP_SYMBOL")
    monkeypatch.delenv("RBP_THRESHOLD_DBPS")
    importlib.reload(cfg)
