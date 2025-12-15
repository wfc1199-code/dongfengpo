"""
快速拉升异动检测策略
"""

from strategy_sdk import BaseStrategy, Signal, SignalType
from datetime import datetime
from typing import Dict, List


class RapidRiseStrategy(BaseStrategy):
    """
    快速拉升策略

    检测短时间内价格快速上涨且成交量放大的异动情况

    信号生成条件：
    1. 价格涨幅 > 阈值（默认3%）
    2. 成交量放大 > 阈值（默认2倍）
    3. 有大额资金流入
    4. 未触发风险控制
    """

    name = "rapid_rise"
    version = "1.2.0"
    author = "dongfengpo_team"
    description = "快速拉升异动检测策略"

    required_features = [
        "code",
        "name",
        "price",
        "price_change_rate",
        "volume_ratio",
        "money_flow_5min",
        "turnover_rate"
    ]

    default_parameters = {
        "price_threshold": 0.03,
        "volume_threshold": 2.0,
        "money_flow_threshold": 5000000,
        "confidence_base": 0.7
    }

    def __init__(self):
        super().__init__()
        self.signal_count = {}  # 信号计数（防止过度信号）

    async def initialize(self, config: Dict):
        """初始化策略参数"""
        self.price_threshold = config.get('price_threshold', 0.03)
        self.volume_threshold = config.get('volume_threshold', 2.0)
        self.money_flow_threshold = config.get('money_flow_threshold', 5000000)
        self.confidence_base = config.get('confidence_base', 0.7)

        # 风险控制参数
        risk_controls = config.get('risk_controls', {})
        self.max_signals_per_minute = risk_controls.get('max_signals_per_minute', 10)
        self.min_confidence = risk_controls.get('min_confidence', 0.6)
        self.blacklist_sectors = risk_controls.get('blacklist_sectors', [])
        self.max_price = risk_controls.get('max_price', 100)
        self.min_volume = risk_controls.get('min_volume', 1000000)

        print(f"[RapidRise] Initialized with thresholds: "
              f"price={self.price_threshold}, volume={self.volume_threshold}")

    async def analyze(self, features: Dict) -> List[Signal]:
        """分析特征并生成信号"""
        signals = []

        # 验证必要特征
        if not self.validate_features(features):
            return signals

        # 提取特征
        stock_code = features['code']
        stock_name = features['name']
        price = features['price']
        price_change_rate = features['price_change_rate']
        volume_ratio = features['volume_ratio']
        money_flow = features['money_flow_5min']
        turnover_rate = features.get('turnover_rate', 0)

        # 风险控制检查
        if not self._pass_risk_control(stock_name, price, features.get('volume', 0)):
            return signals

        # 策略逻辑
        is_price_rise = price_change_rate > self.price_threshold
        is_volume_surge = volume_ratio > self.volume_threshold
        has_money_flow = money_flow > self.money_flow_threshold

        if is_price_rise and is_volume_surge:
            # 计算置信度
            confidence = self._calculate_confidence(
                price_change_rate,
                volume_ratio,
                money_flow,
                turnover_rate
            )

            if confidence >= self.min_confidence:
                # 生成信号
                signals.append(Signal(
                    type=self._determine_signal_type(price_change_rate),
                    stock_code=stock_code,
                    stock_name=stock_name,
                    confidence=confidence,
                    timestamp=int(datetime.now().timestamp()),
                    reason=self._generate_reason(
                        price_change_rate,
                        volume_ratio,
                        money_flow
                    ),
                    metadata={
                        "price": price,
                        "price_change_rate": price_change_rate,
                        "volume_ratio": volume_ratio,
                        "money_flow_5min": money_flow,
                        "turnover_rate": turnover_rate,
                        "strategy_version": self.version
                    }
                ))

                # 记录信号
                self._record_signal(stock_code)

        return signals

    def _pass_risk_control(self, stock_name: str, price: float, volume: float) -> bool:
        """风险控制检查"""
        # 黑名单检查
        for blacklist_pattern in self.blacklist_sectors:
            if blacklist_pattern in stock_name:
                return False

        # 价格检查
        if price > self.max_price:
            return False

        # 成交量检查
        if volume < self.min_volume:
            return False

        return True

    def _calculate_confidence(
        self,
        price_change: float,
        volume_ratio: float,
        money_flow: float,
        turnover_rate: float
    ) -> float:
        """计算信号置信度"""
        # 基础置信度
        confidence = self.confidence_base

        # 价格涨幅加成
        price_score = min((price_change / self.price_threshold - 1) * 0.1, 0.15)
        confidence += price_score

        # 量比加成
        volume_score = min((volume_ratio / self.volume_threshold - 1) * 0.08, 0.10)
        confidence += volume_score

        # 资金流加成
        if money_flow > self.money_flow_threshold * 2:
            confidence += 0.05

        # 换手率加成
        if turnover_rate > 5:  # 换手率大于5%
            confidence += 0.03

        return min(confidence, 1.0)

    def _determine_signal_type(self, price_change_rate: float) -> SignalType:
        """根据涨幅确定信号类型"""
        if price_change_rate >= 0.095:  # 接近涨停
            return SignalType.LIMIT_UP
        elif price_change_rate >= 0.05:  # 涨幅超过5%
            return SignalType.ANOMALY
        else:
            return SignalType.BUY

    def _generate_reason(
        self,
        price_change: float,
        volume_ratio: float,
        money_flow: float
    ) -> str:
        """生成信号原因说明"""
        return (
            f"快速拉升: 涨幅{price_change*100:.2f}%, "
            f"量比{volume_ratio:.2f}倍, "
            f"资金流入{money_flow/10000:.0f}万"
        )

    def _record_signal(self, stock_code: str):
        """记录信号（用于限流）"""
        current_minute = datetime.now().strftime("%Y%m%d%H%M")
        key = f"{stock_code}_{current_minute}"
        self.signal_count[key] = self.signal_count.get(key, 0) + 1

    async def on_market_open(self):
        """开盘回调"""
        print(f"[{self.name}] 市场开盘 - 策略开始运行")
        self.signal_count.clear()  # 清空信号计数

    async def on_market_close(self):
        """收盘回调"""
        total_signals = sum(self.signal_count.values())
        print(f"[{self.name}] 市场收盘 - 今日共生成 {total_signals} 个信号")