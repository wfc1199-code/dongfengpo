"""Tests for opportunity manager state machine."""

from __future__ import annotations

from datetime import datetime, timedelta

from opportunity_aggregator.models import StrategySignal
from opportunity_aggregator.state import OpportunityManager


def make_signal(symbol: str, confidence: float, strength: float) -> StrategySignal:
    now = datetime.utcnow()
    return StrategySignal(
        strategy="test",
        symbol=symbol,
        signal_type="rapid_rise",
        confidence=confidence,
        strength_score=strength,
        reasons=["test"],
        triggered_at=now,
        window="5s",
        metadata={}
    )


def test_manager_creates_new_opportunity():
    manager = OpportunityManager(expiration=timedelta(seconds=60))
    signal = make_signal("sh600000", confidence=0.8, strength=70)

    opportunity = manager.ingest(signal)

    assert opportunity.symbol == "sh600000"
    assert opportunity.state == "NEW"
    assert opportunity.confidence == 0.8


def test_manager_updates_existing_opportunity():
    manager = OpportunityManager(expiration=timedelta(seconds=60))
    first = make_signal("sh600000", confidence=0.6, strength=50)
    second = make_signal("sh600000", confidence=0.9, strength=80)

    manager.ingest(first)
    opportunity = manager.ingest(second)

    assert opportunity.state == "TRACKING"
    assert opportunity.confidence == 0.9
    assert len(opportunity.signals) == 2
