"""Tests for strategy loader."""

from __future__ import annotations

from strategy_engine.config import StrategyConfig
from strategy_engine.loader import load_strategies


def test_load_strategies_creates_instances():
    configs = [
        StrategyConfig(
            name="rapid-rise",
            module="strategy_engine.strategies.rapid_rise",
            class_name="RapidRiseStrategy",
            parameters={"min_change": 1.5, "min_volume": 1000},
        )
    ]

    strategies = load_strategies(configs)

    assert "rapid-rise" in strategies
    strategy = strategies["rapid-rise"]
    assert strategy.name == "rapid-rise"
