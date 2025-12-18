"""
Backtest Engine API测试
"""

import pytest
from fastapi.testclient import TestClient
from backtest_engine.main import app

client = TestClient(app)


class TestHealthCheck:
    """测试健康检查端点"""

    def test_root(self):
        """测试根路径"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["service"] == "Backtest Engine"
        assert response.json()["status"] == "running"

    def test_health_check(self):
        """测试健康检查"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestBacktestAPI:
    """测试回测API"""

    def test_run_backtest(self):
        """测试运行回测"""
        request_data = {
            "strategy_name": "ignition",
            "parameters": {"rise_threshold": 3.0, "volume_ratio": 2.0},
            "start_date": "2023-01-01",
            "end_date": "2024-12-31",
            "initial_cash": 100000.0,
        }
        response = client.post("/api/backtest/run", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"
        assert data["task_id"].startswith("bt_")

    def test_get_task_status(self):
        """测试获取任务状态"""
        task_id = "bt_test_123"
        response = client.get(f"/api/backtest/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert "status" in data

    def test_get_results(self):
        """测试获取回测结果"""
        task_id = "bt_test_123"
        response = client.get(f"/api/backtest/results/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert "metrics" in data


class TestOptimizeAPI:
    """测试参数优化API"""

    def test_run_optimization(self):
        """测试运行参数优化"""
        request_data = {
            "strategy_name": "ignition",
            "param_space": {
                "rise_threshold": {"min": 2.0, "max": 5.0},
                "volume_ratio": {"min": 1.5, "max": 3.0},
            },
            "algorithm": "genetic",
            "data_range": {"start": "2023-01-01", "end": "2024-12-31"},
            "objective": "sharpe",
        }
        response = client.post("/api/optimize/run", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["task_id"].startswith("opt_")

    def test_get_optimization_status(self):
        """测试获取优化状态"""
        task_id = "opt_test_123"
        response = client.get(f"/api/optimize/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id

    def test_get_optimization_results(self):
        """测试获取优化结果"""
        task_id = "opt_test_123"
        response = client.get(f"/api/optimize/results/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert "best_params" in data
        assert "best_score" in data
