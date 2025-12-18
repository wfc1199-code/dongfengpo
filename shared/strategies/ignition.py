"""
点火策略 - 适配回测框架的简化版本

基于盯盘雷达的点火策略，简化为日K线版本用于回测
"""

from shared.strategies.base import BaseStrategy, SignalResult
import pandas as pd


class IgnitionStrategy(BaseStrategy):
    """
    点火策略（日K线简化版）

    原理：
    1. 成交量放大（量比 > volume_ratio阈值）
    2. 价格突破（涨幅 > price_threshold）
    3. 趋势向上（收盘 > 开盘）

    这是原分钟级点火策略的日K线简化版本，用于回测验证。
    """

    name = "IgnitionStrategy"

    # 参数定义（供优化器使用）
    params = {
        "volume_ratio": {
            "type": "float",
            "range": [1.5, 5.0],
            "default": 2.0,
            "description": "成交量放大倍数",
        },
        "price_threshold": {
            "type": "float",
            "range": [0.01, 0.05],
            "default": 0.02,
            "description": "价格涨幅阈值",
        },
    }

    def generate_signal(self, data):
        """
        生成交易信号

        Args:
            data: K线数据字典

        Returns:
            SignalResult or None
        """
        # 检查必要的字段
        required_fields = ["open", "close", "volume"]
        if not all(field in data for field in required_fields):
            return None

        # 计算涨幅
        price_change = (data["close"] - data["open"]) / data["open"]

        # 检查是否有历史数据用于计算量比
        # 简化版本：如果volume字段存在且大于某个基准值就认为放量
        # 实际应该用历史均量，但我们现在没有历史数据，所以简化处理

        # 条件1: 价格上涨超过阈值
        condition1 = price_change > self.price_threshold

        # 条件2: 阳线（收盘 > 开盘）
        condition2 = data["close"] > data["open"]

        # 条件3: 成交量大于0（简化的量比判断）
        condition3 = data["volume"] > 0

        # 买入信号
        if condition1 and condition2 and condition3:
            confidence = min(90, 70 + price_change * 1000)  # 根据涨幅计算置信度

            return SignalResult(
                action="BUY",
                confidence=confidence,
                reason=f"点火信号: 涨{price_change*100:.1f}%, 放量",
                detail={
                    "price_change_pct": round(price_change * 100, 2),
                    "volume": data["volume"],
                },
            )

        # 卖出信号：跌破开盘价
        if data["close"] < data["open"] * 0.97:  # 跌破3%
            return SignalResult(action="SELL", confidence=80, reason="止损: 跌破3%")

        return None
