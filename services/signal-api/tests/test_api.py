"""API smoke tests using dependency overrides."""

from __future__ import annotations

from datetime import datetime
from typing import List

import pytest
from fastapi.testclient import TestClient

from signal_api.app import create_app
from signal_api.dependencies import get_repository
from signal_api.models import Opportunity, StrategySignal


class DummyRepository:
    def __init__(self) -> None:
        self.calls = 0

    async def list_opportunities(self, limit=None, state=None):  # noqa: ANN001
        self.calls += 1
        now = datetime.utcnow()
        return [
            Opportunity(
                id="op-1",
                symbol="sh600000",
                state="ACTIVE",
                created_at=now,
                updated_at=now,
                confidence=0.8,
                strength_score=75,
                notes=["test"],
                signals=[
                    StrategySignal(
                        strategy="rapid",
                        symbol="sh600000",
                        signal_type="rapid_rise",
                        confidence=0.8,
                        strength_score=75,
                        reasons=["test"],
                        triggered_at=now,
                        window="5s",
                        metadata={},
                    )
                ],
            )
        ]

    async def get_opportunity(self, symbol: str) -> Opportunity | None:  # type: ignore[override]
        opportunities = await self.list_opportunities()
        for opportunity in opportunities:
            if opportunity.symbol == symbol:
                return opportunity
        return None


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    repo = DummyRepository()
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: repo
    return TestClient(app)


def test_list_opportunities(client: TestClient) -> None:
    response = client.get("/opportunities")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["symbol"] == "sh600000"


def test_get_opportunity(client: TestClient) -> None:
    response = client.get("/opportunities/sh600000")
    assert response.status_code == 200
    assert response.json()["id"] == "op-1"


def test_get_opportunity_not_found(client: TestClient) -> None:
    response = client.get("/opportunities/sz000001")
    assert response.status_code == 404
