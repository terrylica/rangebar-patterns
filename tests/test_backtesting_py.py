"""Smoke test: backtesting.py strategy loads and has correct structure.

ADR: docs/adr/2026-02-06-repository-creation.md
"""

import importlib


def test_champion_strategy_importable():
    mod = importlib.import_module("backtest.backtesting_py.champion_strategy")
    assert hasattr(mod, "ChampionMeanRevLong")


def test_data_loader_importable():
    mod = importlib.import_module("backtest.backtesting_py.data_loader")
    assert hasattr(mod, "load_range_bars")


def test_champion_strategy_has_init_and_next():
    from backtest.backtesting_py.champion_strategy import ChampionMeanRevLong

    assert hasattr(ChampionMeanRevLong, "init")
    assert hasattr(ChampionMeanRevLong, "next")
