"""Backtest API tests."""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from backtest_service.app import create_app
from backtest_service.models import BacktestRequest, StrategyParameters


def test_backtest_endpoint():
    app = create_app()
    client = TestClient(app)

    payload = {
        "symbol": "sh600000",
        "start_date": "2024-01-01",
        "end_date": "2024-02-01",
        "strategy": {"name": "rapid-rise", "config": {"threshold": 2.0}},
        "initial_capital": 100000,
    }

    response = client.post("/backtests", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["metrics"]["trades"] >= 0
