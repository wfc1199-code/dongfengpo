"""
异动检测策略
从Legacy backend/core/anomaly_detection.py迁移
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class AnomalyDetectionStrategy:
    """
    异动检测策略

    检测类型:
    1. 涨速异动 - 短时间快速上涨
    2. 放量异动 - 成交量突然放大
    3. 大单异动 - 大额买单频繁
    4. 资金流入 - 主动买入资金流入
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化策略"""
        self.config = config
        self.params = config.get('parameters', {})

        # 涨速参数
        self.speed_threshold = self.params.get('speed_threshold', 0.02)
        self.speed_confidence_base = self.params.get('speed_confidence_base', 0.75)

        # 放量参数
        self.volume_threshold = self.params.get('volume_threshold', 2.0)
        self.volume_confidence_base = self.params.get('volume_confidence_base', 0.70)

        # 大单参数
        self.big_order_threshold = self.params.get('big_order_threshold', 3000000)

        # 资金流入参数
        self.capital_inflow_threshold = self.params.get('capital_inflow_threshold', 5000000)

        # 多信号加成
        self.multi_signal_bonus = self.params.get('multi_signal_bonus', 0.1)

        # 风控参数
        risk_controls = config.get('risk_controls', {})
        self.min_confidence = risk_controls.get('min_confidence', 0.60)
        self.blacklist_sectors = risk_controls.get('blacklist_sectors', [])

        logger.info(f"AnomalyDetectionStrategy initialized with speed_threshold={self.speed_threshold}")

    def analyze_sync(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        分析特征快照,生成异动信号

        Args:
            snapshot: 特征快照字典,包含:
                - symbol: 股票代码
                - price: 当前价格
                - price_change_rate: 涨跌幅
                - volume: 成交量
                - volume_ratio: 量比
                - avg_price: 均价
                - change_speed: 涨速

        Returns:
            信号列表,每个信号包含:
                - strategy: 策略名称
                - symbol: 股票代码
                - signal_type: 信号类型
                - confidence: 置信度
                - strength_score: 强度评分
                - reasons: 触发原因列表
                - metadata: 元数据
        """
        signals = []
        symbol = snapshot.get('symbol')

        # 风控检查
        if not self._pass_risk_control(snapshot):
            return signals

        # 1. 涨速异动检测
        speed_signal = self._detect_speed_anomaly(snapshot)
        if speed_signal:
            signals.append(speed_signal)

        # 2. 放量异动检测
        volume_signal = self._detect_volume_anomaly(snapshot)
        if volume_signal:
            signals.append(volume_signal)

        # 3. 大单异动检测
        big_order_signal = self._detect_big_order(snapshot)
        if big_order_signal:
            signals.append(big_order_signal)

        # 4. 资金流入检测
        capital_signal = self._detect_capital_inflow(snapshot)
        if capital_signal:
            signals.append(capital_signal)

        # 多信号加成
        if len(signals) > 1:
            for signal in signals:
                signal['confidence'] = min(
                    signal['confidence'] + self.multi_signal_bonus * (len(signals) - 1),
                    1.0
                )

        # 过滤低置信度信号
        signals = [s for s in signals if s['confidence'] >= self.min_confidence]

        if signals:
            logger.info(f"Generated {len(signals)} signals for {symbol}")

        return signals

    def _pass_risk_control(self, snapshot: Dict[str, Any]) -> bool:
        """风险控制检查"""
        symbol = snapshot.get('symbol', '')

        # 检查黑名单
        for blacklist_word in self.blacklist_sectors:
            if blacklist_word in symbol.upper():
                logger.debug(f"Blacklisted: {symbol}")
                return False

        return True

    def _detect_speed_anomaly(self, snapshot: Dict[str, Any]) -> Dict[str, Any] | None:
        """
        涨速异动检测
        检测短时间内价格快速上涨
        """
        price_change_rate = snapshot.get('price_change_rate', 0)
        change_speed = snapshot.get('change_speed', 0)  # 每分钟涨幅

        # 使用涨速或涨幅判断
        speed_metric = change_speed if change_speed > 0 else price_change_rate

        if speed_metric >= self.speed_threshold:
            # 计算置信度: 超过阈值越多,置信度越高
            confidence = min(
                self.speed_confidence_base + (speed_metric - self.speed_threshold) * 5,
                1.0
            )

            # 强度评分: 0-100
            strength_score = min(speed_metric / self.speed_threshold * 50, 100)

            return {
                'strategy': 'anomaly_detection',
                'symbol': snapshot['symbol'],
                'signal_type': 'speed_up',
                'confidence': confidence,
                'strength_score': strength_score,
                'reasons': [f"涨速异动: {speed_metric:.2%}"],
                'triggered_at': datetime.utcnow().isoformat(),
                'window': snapshot.get('window', '5s'),
                'metadata': {
                    'price': snapshot.get('price'),
                    'price_change_rate': price_change_rate,
                    'change_speed': change_speed
                }
            }

        return None

    def _detect_volume_anomaly(self, snapshot: Dict[str, Any]) -> Dict[str, Any] | None:
        """
        放量异动检测
        检测成交量突然放大
        """
        volume_ratio = snapshot.get('volume_ratio', 0)

        if volume_ratio >= self.volume_threshold:
            confidence = min(
                self.volume_confidence_base + (volume_ratio - self.volume_threshold) * 0.1,
                1.0
            )

            strength_score = min(volume_ratio / self.volume_threshold * 40, 100)

            return {
                'strategy': 'anomaly_detection',
                'symbol': snapshot['symbol'],
                'signal_type': 'volume_surge',
                'confidence': confidence,
                'strength_score': strength_score,
                'reasons': [f"放量异动: 量比{volume_ratio:.1f}倍"],
                'triggered_at': datetime.utcnow().isoformat(),
                'window': snapshot.get('window', '5s'),
                'metadata': {
                    'volume': snapshot.get('volume'),
                    'volume_ratio': volume_ratio
                }
            }

        return None

    def _detect_big_order(self, snapshot: Dict[str, Any]) -> Dict[str, Any] | None:
        """
        大单异动检测
        检测大额买单出现
        """
        # 通过成交额简单判断
        volume = snapshot.get('volume', 0)
        price = snapshot.get('price', 0)
        turnover = volume * price if price > 0 else 0

        if turnover >= self.big_order_threshold:
            confidence = min(0.65 + (turnover / self.big_order_threshold - 1) * 0.1, 1.0)
            strength_score = min(turnover / self.big_order_threshold * 30, 100)

            return {
                'strategy': 'anomaly_detection',
                'symbol': snapshot['symbol'],
                'signal_type': 'big_order',
                'confidence': confidence,
                'strength_score': strength_score,
                'reasons': [f"大单异动: {turnover/10000:.0f}万元"],
                'triggered_at': datetime.utcnow().isoformat(),
                'window': snapshot.get('window', '5s'),
                'metadata': {
                    'turnover': turnover,
                    'volume': volume,
                    'price': price
                }
            }

        return None

    def _detect_capital_inflow(self, snapshot: Dict[str, Any]) -> Dict[str, Any] | None:
        """
        资金流入检测
        检测主动买入资金流入
        """
        # 简化实现: 通过量比和涨幅综合判断
        volume_ratio = snapshot.get('volume_ratio', 0)
        price_change_rate = snapshot.get('price_change_rate', 0)

        # 放量且上涨
        if volume_ratio > 1.5 and price_change_rate > 0.01:
            estimated_inflow = snapshot.get('volume', 0) * snapshot.get('price', 0) * 0.6

            if estimated_inflow >= self.capital_inflow_threshold:
                confidence = min(0.68 + price_change_rate * 10, 0.95)
                strength_score = min((estimated_inflow / self.capital_inflow_threshold) * 35, 100)

                return {
                    'strategy': 'anomaly_detection',
                    'symbol': snapshot['symbol'],
                    'signal_type': 'capital_inflow',
                    'confidence': confidence,
                    'strength_score': strength_score,
                    'reasons': [f"资金流入: {estimated_inflow/10000:.0f}万元"],
                    'triggered_at': datetime.utcnow().isoformat(),
                    'window': snapshot.get('window', '5s'),
                    'metadata': {
                        'estimated_inflow': estimated_inflow,
                        'volume_ratio': volume_ratio,
                        'price_change_rate': price_change_rate
                    }
                }

        return None


# 策略工厂函数
def create_strategy(config: Dict[str, Any]) -> AnomalyDetectionStrategy:
    """创建策略实例"""
    return AnomalyDetectionStrategy(config)
