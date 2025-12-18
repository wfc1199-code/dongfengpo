"""
回测执行器测试
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from backtest_engine.core.executor import BacktestEngine, Account, Position
from shared.strategies.base import BaseStrategy, SignalResult


class SimpleStrategy(BaseStrategy):
    """简单测试策略：价格上涨就买，下跌就卖"""

    name = "SimpleStrategy"
    params = {"threshold": {"type": "float", "range": [0.01, 0.1], "default": 0.03}}

    def generate_signal(self, data):
        """根据涨跌幅生成信号"""
        if "close" not in data or "open" not in data:
            return None

        change_pct = (data["close"] - data["open"]) / data["open"]

        if change_pct > self.threshold:
            return SignalResult(action="BUY", confidence=80, reason="Price rising")
        elif change_pct < -self.threshold:
            return SignalResult(action="SELL", confidence=80, reason="Price falling")

        return None


class TestBacktestEngine:
    """测试回测引擎"""

    def test_engine_initialization(self):
        """测试引擎初始化"""
        strategy = SimpleStrategy(threshold=0.03)
        engine = BacktestEngine(strategy, initial_cash=100000)

        assert engine.account.initial_cash == 100000
        assert engine.account.cash == 100000
        assert len(engine.account.positions) == 0

    def test_simple_backtest(self):
        """测试简单回测"""
        # 创建测试数据
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        data = pd.DataFrame(
            {
                "datetime": dates,
                "code": "000001",
                "open": [10.0, 10.5, 11.0, 10.8, 11.2, 11.5, 11.3, 11.8, 12.0, 11.5],
                "high": [10.2, 10.8, 11.2, 11.0, 11.5, 11.8, 11.6, 12.0, 12.2, 11.8],
                "low": [9.8, 10.3, 10.8, 10.6, 11.0, 11.3, 11.1, 11.6, 11.8, 11.3],
                "close": [
                    10.1,
                    10.7,
                    11.1,
                    10.9,
                    11.3,
                    11.6,
                    11.4,
                    11.9,
                    12.1,
                    11.6,
                ],
                "volume": [1000000] * 10,
            }
        )

        # 运行回测
        strategy = SimpleStrategy(threshold=0.03)
        engine = BacktestEngine(strategy, initial_cash=100000)
        result = engine.run(data)

        # 验证结果
        assert "total_return" in result
        assert "annual_return" in result
        assert "equity_curve" in result
        assert "trades" in result
        assert result["initial_cash"] == 100000
        assert result["final_value"] > 0

    def test_account_operations(self):
        """测试账户操作"""
        account = Account(initial_cash=100000, commission_rate=0.0003)

        assert account.total_value == 100000
        assert account.cash == 100000

        # 添加持仓
        account.positions["000001"] = Position(
            code="000001", quantity=1000, avg_price=10.0, current_price=11.0
        )

        assert account.position_value == 11000
        assert account.total_value == 100000 + 11000

    def test_position_profit(self):
        """测试持仓盈亏计算"""
        pos = Position(code="000001", quantity=1000, avg_price=10.0, current_price=11.0)

        assert pos.cost == 10000
        assert pos.market_value == 11000
        assert pos.profit == 1000
        assert pos.profit_pct == 0.1  # 10%


class TestIntegration:
    """集成测试"""

    def test_buy_and_sell_flow(self):
        """测试买卖流程"""
        # 创建上涨数据（触发买入）
        data = pd.DataFrame(
            {
                "datetime": pd.date_range("2024-01-01", periods=5, freq="D"),
                "code": "000001",
                "open": [10.0, 10.5, 11.0, 10.5, 10.0],
                "high": [10.5, 11.0, 11.5, 11.0, 10.5],
                "low": [9.5, 10.0, 10.5, 10.0, 9.5],
                "close": [10.4, 10.9, 11.3, 10.8, 10.2],  # 涨→涨→涨→跌→跌
                "volume": [1000000] * 5,
            }
        )

        strategy = SimpleStrategy(threshold=0.03)
        engine = BacktestEngine(strategy, initial_cash=100000, commission=0.0003)
        result = engine.run(data)

        # 应该有交易发生
        assert result["total_trades"] > 0
        assert len(result["equity_curve"]) == 5
