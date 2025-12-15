"""
涨停板预测策略
基于多维度特征的涨停潜力分析
"""

import logging
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, time
import numpy as np

logger = logging.getLogger(__name__)


class LimitUpPredictionStrategy:
    """涨停板预测策略"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化策略

        Args:
            config: 策略配置字典
        """
        params = config.get('parameters', {})

        # 涨幅参数
        self.min_change_percent = params.get('min_change_percent', 2.0)
        self.strong_change_ratio = params.get('strong_change_ratio', 0.4)
        self.near_limit_ratio = params.get('near_limit_ratio', 0.8)

        # 成交量参数
        self.volume_surge_ratio = params.get('volume_surge_ratio', 1.5)
        self.strong_volume_ratio = params.get('strong_volume_ratio', 2.0)
        self.huge_volume_ratio = params.get('huge_volume_ratio', 3.0)

        # 动量参数
        self.momentum_threshold = params.get('momentum_threshold', 0.5)
        self.acceleration_threshold = params.get('acceleration_threshold', 0.2)

        # 涨停板限制
        self.main_board_limit = params.get('main_board_limit', 9.8)
        self.growth_board_limit = params.get('growth_board_limit', 19.8)

        # 置信度参数
        self.min_signal_count = params.get('min_signal_count', 2)
        self.min_probability = params.get('min_probability', 0.5)

        # 时间分层配置
        self.time_windows = params.get('time_windows', [])

        # 风险控制
        risk_controls = config.get('risk_controls', {})
        self.min_confidence = risk_controls.get('min_confidence', 0.50)
        self.blacklist_sectors = risk_controls.get('blacklist_sectors', [])
        self.max_distance_to_limit = risk_controls.get('max_distance_to_limit', 8.0)

        logger.info(f"LimitUpPredictionStrategy initialized with min_change={self.min_change_percent}%")

    def analyze_sync(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        分析特征快照,生成涨停预测信号

        Args:
            snapshot: 特征快照字典

        Returns:
            信号列表
        """
        symbol = snapshot.get('symbol', '')

        # 风险控制检查
        if not self._pass_risk_control(snapshot):
            return []

        # 获取涨停板限制
        limit = self._get_limit_threshold(symbol)

        # 计算各维度评分
        scores = []
        signals = []

        # 1. 涨幅强度评分
        change_score, change_signal = self._evaluate_change_strength(snapshot, limit)
        if change_signal:
            signals.append(change_signal)
            scores.append(change_score)

        # 2. 成交量异动评分
        volume_score, volume_signal = self._evaluate_volume_surge(snapshot)
        if volume_signal:
            signals.append(volume_signal)
            scores.append(volume_score)

        # 3. 动量评分
        momentum_score, momentum_signal = self._evaluate_momentum(snapshot)
        if momentum_signal:
            signals.append(momentum_signal)
            scores.append(momentum_score)

        # 4. 时间因素评分
        time_score, time_signal, time_window = self._evaluate_time_factor()
        if time_signal:
            signals.append(time_signal)
            scores.append(time_score)

        # 判断是否生成信号
        if not scores or len(signals) < self.min_signal_count:
            return []

        # 计算综合概率
        probability = self._calculate_probability(scores, signals, snapshot, limit)

        if probability < self.min_probability:
            return []

        # 计算置信度
        confidence = min(probability * 1.1, 1.0)  # 略微提升置信度但不超过1.0

        # 计算强度评分
        strength_score = np.mean(scores) * 100

        # 距离涨停板距离
        current_change = snapshot.get('price_change_rate', 0) * 100
        distance_to_limit = limit - current_change

        # 生成信号
        result = {
            'strategy': 'limit_up_prediction',
            'symbol': symbol,
            'signal_type': 'limit_up_potential',
            'confidence': confidence,
            'strength_score': strength_score,
            'reasons': signals,
            'triggered_at': datetime.now().isoformat(),
            'window': snapshot.get('window', '5s'),
            'metadata': {
                'probability': probability,
                'current_change_percent': current_change,
                'limit_percent': limit,
                'distance_to_limit': distance_to_limit,
                'time_window': time_window,
                'signal_count': len(signals)
            }
        }

        logger.info(f"Generated limit-up prediction signal for {symbol}: prob={probability:.2f}, conf={confidence:.2f}")

        return [result]

    def _pass_risk_control(self, snapshot: Dict[str, Any]) -> bool:
        """风险控制检查"""
        symbol = snapshot.get('symbol', '')

        # 检查黑名单板块
        for blacklist in self.blacklist_sectors:
            if blacklist in symbol.upper():
                return False

        # 检查涨幅是否超过最小要求
        change_rate = snapshot.get('price_change_rate', 0) * 100
        if change_rate < self.min_change_percent:
            return False

        return True

    def _get_limit_threshold(self, symbol: str) -> float:
        """获取涨停板限制"""
        # 创业板(30/300开头)、科创板(68开头) 为20%
        if symbol.startswith('30') or symbol.startswith('300') or symbol.startswith('68'):
            return self.growth_board_limit
        return self.main_board_limit

    def _evaluate_change_strength(self, snapshot: Dict[str, Any], limit: float) -> Tuple[float, Optional[str]]:
        """评估涨幅强度"""
        change_rate = snapshot.get('price_change_rate', 0) * 100

        if change_rate < self.min_change_percent:
            return 0, None

        # 计算涨幅相对于涨停板的比例
        change_ratio = change_rate / limit

        if change_ratio >= self.near_limit_ratio:
            return 0.95, f"即将涨停({change_rate:.1f}%)"
        elif change_ratio >= 0.6:
            return 0.80, f"强势拉升({change_rate:.1f}%)"
        elif change_ratio >= self.strong_change_ratio:
            return 0.60, f"稳步上涨({change_rate:.1f}%)"
        elif change_ratio >= 0.25:
            return 0.40, f"开始拉升({change_rate:.1f}%)"
        else:
            return 0.20, None

    def _evaluate_volume_surge(self, snapshot: Dict[str, Any]) -> Tuple[float, Optional[str]]:
        """评估成交量异动"""
        volume_ratio = snapshot.get('volume_ratio', 0)

        if volume_ratio >= self.huge_volume_ratio:
            return 0.90, f"巨量突破(量比{volume_ratio:.1f})"
        elif volume_ratio >= self.strong_volume_ratio:
            return 0.70, f"明显放量(量比{volume_ratio:.1f})"
        elif volume_ratio >= self.volume_surge_ratio:
            return 0.50, f"温和放量(量比{volume_ratio:.1f})"

        return 0, None

    def _evaluate_momentum(self, snapshot: Dict[str, Any]) -> Tuple[float, Optional[str]]:
        """评估动量"""
        # 使用change_speed作为动量代理
        change_speed = snapshot.get('change_speed', 0) * 100

        if change_speed > self.momentum_threshold * 2:
            return 0.85, f"加速拉升(涨速{change_speed:.2f}%/min)"
        elif change_speed > self.momentum_threshold:
            return 0.65, f"快速拉升(涨速{change_speed:.2f}%/min)"
        elif change_speed > 0:
            return 0.45, f"逐步加速(涨速{change_speed:.2f}%/min)"

        return 0, None

    def _evaluate_time_factor(self) -> Tuple[float, Optional[str], str]:
        """评估时间因素"""
        now = datetime.now()
        current_time = now.time()

        # 遍历时间窗口配置
        for window in self.time_windows:
            start_time = time.fromisoformat(window['start'])
            end_time = time.fromisoformat(window['end'])

            if start_time <= current_time <= end_time:
                weight = window['weight']
                name = window['name']
                return weight, f"时段优势({name})", name

        # 默认返回
        return 0.3, None, "other"

    def _calculate_probability(self, scores: List[float], signals: List[str],
                               snapshot: Dict[str, Any], limit: float) -> float:
        """计算涨停概率"""
        if not scores:
            return 0.0

        # 基础概率 = 平均分数
        avg_score = np.mean(scores)
        max_score = max(scores)

        # 加权计算
        base_prob = (avg_score * 0.6 + max_score * 0.4)

        # 信号数量加成
        signal_bonus = min(len(signals) * 0.05, 0.15)

        # 距离涨停板距离调整
        change_rate = snapshot.get('price_change_rate', 0) * 100
        distance = limit - change_rate
        if distance < 2.0:  # 距离涨停板小于2%
            distance_bonus = 0.15
        elif distance < 4.0:
            distance_bonus = 0.10
        elif distance < 6.0:
            distance_bonus = 0.05
        else:
            distance_bonus = 0.0

        # 综合概率
        probability = base_prob + signal_bonus + distance_bonus

        return min(probability, 1.0)
