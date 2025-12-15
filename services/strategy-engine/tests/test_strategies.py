"""Tests for built-in strategies."""

from __future__ import annotations

from datetime import datetime

from strategy_engine.models import FeatureSnapshot
from strategy_engine.strategies.rapid_rise import RapidRiseStrategy


def make_snapshot(change_percent: float, volume: int) -> FeatureSnapshot:
    now = datetime.utcnow()
    return FeatureSnapshot(
        symbol="sh600000",
        window="5s",
        timestamp=now,
        price=10.0,
        change_percent=change_percent,
        volume_sum=volume,
        avg_price=9.8,
        max_price=10.1,
        min_price=9.5,
        turnover_sum=volume * 10.0,
        sample_size=5,
    )


def test_strategy_triggers_on_threshold():
    strategy = RapidRiseStrategy(name="rapid", min_change=2.0, min_volume=1000)
    snapshot = make_snapshot(change_percent=2.5, volume=2000)

    signal = strategy.evaluate(snapshot)

    assert signal is not None
    assert signal.signal_type == "rapid_rise"


def test_strategy_ignore_low_volume():
    strategy = RapidRiseStrategy(name="rapid", min_change=2.0, min_volume=5000)
    snapshot = make_snapshot(change_percent=3.0, volume=1000)

    assert strategy.evaluate(snapshot) is None
