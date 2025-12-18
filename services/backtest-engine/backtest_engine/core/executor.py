"""
回测执行器 - 事件驱动的回测引擎

支持：
- 日K线回测
- 分钟K线回测（后续扩展）
- 订单撮合模拟
- 滑点和手续费
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from enum import Enum


class OrderSide(Enum):
    """订单方向"""

    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """订单状态"""

    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"


@dataclass
class Order:
    """订单"""

    code: str
    side: OrderSide
    quantity: int
    price: float
    timestamp: datetime
    status: OrderStatus = OrderStatus.PENDING
    filled_price: Optional[float] = None
    filled_quantity: int = 0
    commission: float = 0.0


@dataclass
class Position:
    """持仓"""

    code: str
    quantity: int
    avg_price: float
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        """市值"""
        return self.quantity * self.current_price

    @property
    def cost(self) -> float:
        """成本"""
        return self.quantity * self.avg_price

    @property
    def profit(self) -> float:
        """浮动盈亏"""
        return self.market_value - self.cost

    @property
    def profit_pct(self) -> float:
        """盈亏比例"""
        return (self.profit / self.cost) if self.cost > 0 else 0.0


@dataclass
class Account:
    """账户"""

    initial_cash: float
    cash: float = 0.0
    positions: Dict[str, Position] = field(default_factory=dict)
    commission_rate: float = 0.0003  # 0.03%
    slippage: float = 0.001  # 0.1%

    def __post_init__(self):
        if self.cash == 0.0:
            self.cash = self.initial_cash

    @property
    def total_value(self) -> float:
        """总资产"""
        return self.cash + sum(pos.market_value for pos in self.positions.values())

    @property
    def position_value(self) -> float:
        """持仓市值"""
        return sum(pos.market_value for pos in self.positions.values())


class BacktestEngine:
    """
    回测执行器

    事件驱动的回测引擎，逐Bar处理数据并执行策略。
    """

    def __init__(
        self,
        strategy,
        initial_cash: float = 100000.0,
        commission: float = 0.0003,
        slippage: float = 0.001,
    ):
        """
        初始化回测引擎

        Args:
            strategy: 策略实例
            initial_cash: 初始资金
            commission: 手续费率
            slippage: 滑点率
        """
        self.strategy = strategy
        self.account = Account(
            initial_cash=initial_cash, commission_rate=commission, slippage=slippage
        )

        # 回测状态
        self.current_date: Optional[datetime] = None
        self.trades: List[Dict] = []
        self.equity_curve: List[Dict] = []

    def run(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        运行回测

        Args:
            data: K线数据，DataFrame格式
                  必须包含: datetime, open, high, low, close, volume

        Returns:
            回测结果字典
        """
        # 确保数据按时间排序
        data = data.sort_values("datetime").reset_index(drop=True)

        # 逐Bar处理
        for idx, bar in data.iterrows():
            self._process_bar(bar)

        # 返回结果
        return self._generate_result()

    def _process_bar(self, bar: pd.Series):
        """
        处理单根K线

        Args:
            bar: K线数据
        """
        self.current_date = bar["datetime"]

        # 更新持仓价格
        code = bar.get("code", "UNKNOWN")
        if code in self.account.positions:
            self.account.positions[code].current_price = bar["close"]

        # 调用策略生成信号
        signal = self.strategy.on_bar(context=self, bar=bar.to_dict())

        # 处理信号
        if signal:
            self._execute_signal(signal, bar)

        # 记录净值
        self._record_equity()

    def _execute_signal(self, signal, bar: pd.Series):
        """
        执行信号

        Args:
            signal: 策略信号
            bar: K线数据
        """
        code = bar.get("code", "UNKNOWN")
        price = bar["close"]

        if signal.action == "BUY":
            self._buy(code, price, bar["datetime"])
        elif signal.action == "SELL":
            self._sell(code, price, bar["datetime"])

    def _buy(self, code: str, price: float, timestamp: datetime):
        """
        买入

        Args:
            code: 股票代码
            price: 价格
            timestamp: 时间戳
        """
        # 简单策略：用50%现金买入
        available_cash = self.account.cash * 0.5
        if available_cash < price * 100:  # 至少1手
            return

        # 考虑滑点
        actual_price = price * (1 + self.account.slippage)

        # 计算可买数量（100股为1手）
        quantity = int(available_cash / (actual_price * 100)) * 100
        if quantity == 0:
            return

        # 计算手续费
        cost = quantity * actual_price
        commission = cost * self.account.commission_rate

        # 检查资金
        total_cost = cost + commission
        if total_cost > self.account.cash:
            return

        # 扣除资金
        self.account.cash -= total_cost

        # 更新持仓
        if code in self.account.positions:
            pos = self.account.positions[code]
            total_quantity = pos.quantity + quantity
            pos.avg_price = (pos.cost + cost) / total_quantity
            pos.quantity = total_quantity
        else:
            self.account.positions[code] = Position(
                code=code, quantity=quantity, avg_price=actual_price, current_price=price
            )

        # 记录交易
        self.trades.append(
            {
                "datetime": timestamp,
                "code": code,
                "side": "BUY",
                "price": actual_price,
                "quantity": quantity,
                "commission": commission,
                "cash_after": self.account.cash,
            }
        )

    def _sell(self, code: str, price: float, timestamp: datetime):
        """
        卖出

        Args:
            code: 股票代码
            price: 价格
            timestamp: 时间戳
        """
        if code not in self.account.positions:
            return

        pos = self.account.positions[code]
        if pos.quantity == 0:
            return

        # 考虑滑点
        actual_price = price * (1 - self.account.slippage)

        # 全部卖出
        quantity = pos.quantity
        revenue = quantity * actual_price
        commission = revenue * self.account.commission_rate

        # 增加资金
        self.account.cash += revenue - commission

        # 记录交易
        profit = (actual_price - pos.avg_price) * quantity - commission
        self.trades.append(
            {
                "datetime": timestamp,
                "code": code,
                "side": "SELL",
                "price": actual_price,
                "quantity": quantity,
                "commission": commission,
                "profit": profit,
                "cash_after": self.account.cash,
            }
        )

        # 清空持仓
        del self.account.positions[code]

    def _record_equity(self):
        """记录净值"""
        self.equity_curve.append(
            {
                "datetime": self.current_date,
                "cash": self.account.cash,
                "position_value": self.account.position_value,
                "total_value": self.account.total_value,
            }
        )

    def _generate_result(self) -> Dict[str, Any]:
        """
        生成回测结果

        Returns:
            回测结果字典
        """
        if not self.equity_curve:
            return {"error": "No data"}

        equity_df = pd.DataFrame(self.equity_curve)

        # 计算收益率
        initial_value = self.account.initial_cash
        final_value = self.account.total_value
        total_return = (final_value - initial_value) / initial_value

        # 计算年化收益率（简化版）
        days = len(equity_df)
        annual_return = total_return * (252 / days) if days > 0 else 0

        return {
            "initial_cash": self.account.initial_cash,
            "final_value": self.account.total_value,
            "total_return": total_return,
            "annual_return": annual_return,
            "total_trades": len(self.trades),
            "equity_curve": equity_df.to_dict("records"),
            "trades": self.trades,
        }
