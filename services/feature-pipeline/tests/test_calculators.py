"""Tests for feature calculator rolling windows."""

from __future__ import annotations

from datetime import datetime, timedelta

from feature_pipeline.calculators import FeatureCalculator
from feature_pipeline.models import CleanTick


def _tick(symbol: str, price: float, volume: int, offset_seconds: int) -> CleanTick:
    now = datetime.utcnow() + timedelta(seconds=offset_seconds)
    return CleanTick(
        source="test",
        symbol=symbol,
        price=price,
        volume=volume,
        turnover=price * volume,
        timestamp=now,
        ingested_at=now,
        cleaned_at=now,
        raw={},
    )


def test_calculator_produces_snapshots():
    calculator = FeatureCalculator({"5s": timedelta(seconds=5)})

    snapshots = calculator.update(_tick("sh600000", 10.0, 100, 0))
    assert snapshots[0].price == 10.0
    assert snapshots[0].volume_sum == 100

    snapshots = calculator.update(_tick("sh600000", 11.0, 200, 2))
    assert len(snapshots) == 1
    assert snapshots[0].price == 11.0
    assert snapshots[0].volume_sum == 300
    assert snapshots[0].sample_size == 2


def test_calculator_trims_old_ticks():
    calculator = FeatureCalculator({"5s": timedelta(seconds=5)})

    calculator.update(_tick("sh600000", 10.0, 100, -10))
    snapshots = calculator.update(_tick("sh600000", 11.0, 200, 0))

    assert snapshots[0].sample_size == 1
    assert snapshots[0].volume_sum == 200
