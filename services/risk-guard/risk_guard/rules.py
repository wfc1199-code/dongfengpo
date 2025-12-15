"""Risk evaluation rules."""

from __future__ import annotations

from datetime import datetime
from typing import List

from .models import Opportunity, RiskAlert, RiskSeverity


def evaluate_risks(opportunity: Opportunity, volatility_threshold: float, drawdown_threshold: float) -> List[RiskAlert]:
    alerts: List[RiskAlert] = []
    now = datetime.utcnow()

    if opportunity.confidence < 0.4:
        alerts.append(
            RiskAlert(
                symbol=opportunity.symbol,
                risk_type="low_confidence",
                severity=RiskSeverity.MEDIUM,
                message="策略置信度较低，建议谨慎参与",
                triggered_at=now,
                opportunity_id=opportunity.id,
                metadata={"confidence": opportunity.confidence},
            )
        )

    if opportunity.strength_score < 40:
        alerts.append(
            RiskAlert(
                symbol=opportunity.symbol,
                risk_type="weak_momentum",
                severity=RiskSeverity.MEDIUM,
                message="信号强度不足，缺乏持续动能",
                triggered_at=now,
                opportunity_id=opportunity.id,
                metadata={"strength": opportunity.strength_score},
            )
        )

    for signal in opportunity.signals:
        metadata = getattr(signal, "metadata", {})
        change = metadata.get("change_percent") if isinstance(metadata, dict) else None
        if change and change < 0:
            alerts.append(
                RiskAlert(
                    symbol=opportunity.symbol,
                    risk_type="negative_reversal",
                    severity=RiskSeverity.HIGH,
                    message="近期出现反向波动，警惕回落",
                    triggered_at=now,
                    opportunity_id=opportunity.id,
                    metadata={"change_percent": change},
                )
            )

    return alerts
