"""Opportunity state machine logic."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

from .models import Opportunity, OpportunityState, StrategySignal


class OpportunityManager:
    """Maintain opportunities for symbols."""

    def __init__(self, expiration: timedelta) -> None:
        self.expiration = expiration
        self.opportunities: Dict[str, Opportunity] = {}

    def ingest(self, signal: StrategySignal) -> Opportunity:
        opportunity = self.opportunities.get(signal.symbol)
        now = datetime.utcnow()

        if opportunity is None:
            opportunity = Opportunity(
                id=f"{signal.symbol}-{int(now.timestamp())}",
                symbol=signal.symbol,
                created_at=now,
                updated_at=now,
                signals=[signal],
                confidence=signal.confidence,
                strength_score=signal.strength_score,
                notes=[f"策略 {signal.strategy} 触发"]
            )
            opportunity.state = OpportunityState.NEW
            self.opportunities[signal.symbol] = opportunity
            return opportunity

        opportunity.signals.append(signal)
        opportunity.updated_at = now
        opportunity.confidence = max(opportunity.confidence, signal.confidence)
        opportunity.strength_score = max(opportunity.strength_score, signal.strength_score)
        opportunity.notes.append(f"策略 {signal.strategy} 追加")

        if opportunity.state == OpportunityState.NEW:
            opportunity.state = OpportunityState.ACTIVE
        if len(opportunity.signals) > 1:
            opportunity.state = OpportunityState.TRACKING

        return opportunity

    def cleanup(self) -> List[Opportunity]:
        now = datetime.utcnow()
        closed: List[Opportunity] = []
        for symbol, opportunity in list(self.opportunities.items()):
            if now - opportunity.updated_at > self.expiration:
                opportunity.state = OpportunityState.CLOSED
                opportunity.notes.append("自动关闭：超时无信号")
                closed.append(opportunity)
                self.opportunities.pop(symbol, None)
        return closed
