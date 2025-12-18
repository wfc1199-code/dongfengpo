"""
信号管道 (Signal Pipeline)

完整的信号处理流程：
1. 数据输入 → 数据质量检查
2. 统一评分 → 评分过滤
3. 策略适配 → 策略评估
4. 风控检查 → 风控过滤
5. 信号输出 → 推送/存储

用于盯盘雷达和明日潜力的统一处理。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum
import logging

from .scorer import get_scorer, StockMetrics, ScoringResult
from .adapters import (
    get_ignition_adapter, get_ambush_adapter,
    RadarSignal, TomorrowCandidate
)
from .risk.manager import RiskManager, RiskConfig, RiskCheckResult

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """信号类型"""
    RADAR = "radar"          # 盯盘雷达
    TOMORROW = "tomorrow"    # 明日潜力
    IGNITION = "ignition"    # 点火策略
    AMBUSH = "ambush"        # 潜伏策略


class SignalStatus(Enum):
    """信号状态"""
    PENDING = "pending"      # 待处理
    PASSED = "passed"        # 通过
    FILTERED = "filtered"    # 被过滤
    REJECTED = "rejected"    # 被拒绝（风控）


@dataclass
class SignalResult:
    """信号处理结果"""
    code: str
    name: str
    signal_type: SignalType
    status: SignalStatus
    
    # 评分
    unified_score: float
    strategy_score: float
    
    # 状态信息
    level: str
    risk: str
    action: str
    
    # 过滤/拒绝原因
    filter_reason: Optional[str] = None
    risk_message: Optional[str] = None
    
    # 时间戳
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # 原始数据
    raw_data: Optional[Dict] = None


@dataclass
class PipelineConfig:
    """管道配置"""
    min_unified_score: float = 40.0    # 最低统一分数
    min_strategy_score: float = 50.0   # 最低策略分数
    enable_risk_check: bool = True     # 是否启用风控
    max_signals: int = 20              # 最大信号数量


class SignalPipeline:
    """
    信号处理管道
    
    Usage:
        pipeline = SignalPipeline()
        results = pipeline.process_radar_batch(stocks)
        
    WebSocket推送:
        async def broadcast(signal):
            await send_to_all_clients(signal)
        
        pipeline = SignalPipeline(broadcast_callback=broadcast)
    """
    
    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        risk_manager: Optional[RiskManager] = None,
        broadcast_callback: Optional[Callable] = None
    ):
        """
        初始化管道
        
        Args:
            config: 管道配置
            risk_manager: 风险管理器
            broadcast_callback: WebSocket广播回调 (async function)
        """
        self.config = config or PipelineConfig()
        self.risk_manager = risk_manager or RiskManager()
        self.ignition_adapter = get_ignition_adapter()
        self.ambush_adapter = get_ambush_adapter()
        self.scorer = get_scorer()
        self.broadcast_callback = broadcast_callback
        
        # 统计
        self.stats = {
            'total_processed': 0,
            'passed': 0,
            'filtered': 0,
            'rejected': 0,
            'broadcasted': 0,
        }
        
        logger.info("SignalPipeline initialized" + 
                    (" with broadcast callback" if broadcast_callback else ""))
    
    def process_radar_batch(
        self,
        stocks: List[Dict[str, Any]]
    ) -> List[SignalResult]:
        """
        批量处理盯盘雷达股票
        
        Args:
            stocks: 雷达股票列表
            
        Returns:
            处理后的信号列表
        """
        results = []
        
        for stock in stocks:
            try:
                result = self._process_radar_single(stock)
                results.append(result)
                self.stats['total_processed'] += 1
                
                if result.status == SignalStatus.PASSED:
                    self.stats['passed'] += 1
                    # 广播通过的信号
                    self._broadcast_signal(result)
                elif result.status == SignalStatus.FILTERED:
                    self.stats['filtered'] += 1
                elif result.status == SignalStatus.REJECTED:
                    self.stats['rejected'] += 1
                    
            except Exception as e:
                logger.error(f"处理雷达信号失败 {stock.get('code', '?')}: {e}")
        
        # 按分数排序，取前N个
        results.sort(key=lambda x: x.unified_score, reverse=True)
        return results[:self.config.max_signals]
    
    def _process_radar_single(self, stock: Dict) -> SignalResult:
        """处理单只雷达股票"""
        code = stock.get('code', '')
        name = stock.get('name', '')
        
        # 1. 使用适配器处理
        signal = self.ignition_adapter.process_radar_stock(stock)
        
        # 2. 评分过滤
        if signal.unified_score < self.config.min_unified_score:
            return SignalResult(
                code=code,
                name=name,
                signal_type=SignalType.RADAR,
                status=SignalStatus.FILTERED,
                unified_score=signal.unified_score,
                strategy_score=signal.ignition_score,
                level=signal.strength_level,
                risk=signal.risk_level,
                action="跳过",
                filter_reason=f"评分{signal.unified_score:.1f}<{self.config.min_unified_score}",
            )
        
        # 3. 策略分数过滤
        if signal.ignition_score < self.config.min_strategy_score:
            return SignalResult(
                code=code,
                name=name,
                signal_type=SignalType.RADAR,
                status=SignalStatus.FILTERED,
                unified_score=signal.unified_score,
                strategy_score=signal.ignition_score,
                level=signal.strength_level,
                risk=signal.risk_level,
                action="跳过",
                filter_reason=f"点火分{signal.ignition_score:.1f}<{self.config.min_strategy_score}",
            )
        
        # 4. 风控检查
        if self.config.enable_risk_check:
            risk_result = self._check_risk_for_signal(signal)
            if not risk_result.is_allowed:
                return SignalResult(
                    code=code,
                    name=name,
                    signal_type=SignalType.RADAR,
                    status=SignalStatus.REJECTED,
                    unified_score=signal.unified_score,
                    strategy_score=signal.ignition_score,
                    level=signal.strength_level,
                    risk=signal.risk_level,
                    action="拒绝",
                    risk_message=risk_result.message,
                )
        
        # 5. 通过
        return SignalResult(
            code=code,
            name=name,
            signal_type=SignalType.RADAR,
            status=SignalStatus.PASSED,
            unified_score=signal.unified_score,
            strategy_score=signal.ignition_score,
            level=signal.strength_level,
            risk=signal.risk_level,
            action=signal.action,
            raw_data=stock,
        )
    
    def process_tomorrow_batch(
        self,
        candidates: List[Dict[str, Any]]
    ) -> List[SignalResult]:
        """
        批量处理明日潜力候选
        
        Args:
            candidates: 候选列表
            
        Returns:
            处理后的信号列表
        """
        results = []
        
        for candidate in candidates:
            try:
                result = self._process_tomorrow_single(candidate)
                results.append(result)
                self.stats['total_processed'] += 1
                
                if result.status == SignalStatus.PASSED:
                    self.stats['passed'] += 1
                elif result.status == SignalStatus.FILTERED:
                    self.stats['filtered'] += 1
                    
            except Exception as e:
                logger.error(f"处理候选失败 {candidate.get('code', '?')}: {e}")
        
        # 按策略分数排序
        results.sort(key=lambda x: x.strategy_score, reverse=True)
        return results[:self.config.max_signals]
    
    def _process_tomorrow_single(self, candidate: Dict) -> SignalResult:
        """处理单只明日候选"""
        code = candidate.get('code', '')
        name = candidate.get('name', '')
        
        # 1. 使用适配器处理
        result = self.ambush_adapter.process_candidate(candidate)
        
        # 2. 评分过滤
        if result.unified_score < self.config.min_unified_score:
            return SignalResult(
                code=code,
                name=name,
                signal_type=SignalType.TOMORROW,
                status=SignalStatus.FILTERED,
                unified_score=result.unified_score,
                strategy_score=result.ambush_score,
                level=result.strength_level,
                risk="",
                action="跳过",
                filter_reason=f"评分{result.unified_score:.1f}<{self.config.min_unified_score}",
            )
        
        # 3. 通过
        return SignalResult(
            code=code,
            name=name,
            signal_type=SignalType.TOMORROW,
            status=SignalStatus.PASSED,
            unified_score=result.unified_score,
            strategy_score=result.ambush_score,
            level=result.strength_level,
            risk="",
            action="候选",
            raw_data=candidate,
        )
    
    def _check_risk_for_signal(self, signal: RadarSignal) -> RiskCheckResult:
        """对信号进行风控检查"""
        # 假设信号价值为10万（可配置）
        proposed_value = 100000
        
        return self.risk_manager.check_buy_signal(
            symbol=signal.code,
            proposed_value=proposed_value,
            sector=""  # 暂无板块信息
        )
    
    def _broadcast_signal(self, signal: SignalResult):
        """
        广播信号到 WebSocket 客户端
        
        Args:
            signal: 通过的信号结果
        """
        if not self.broadcast_callback:
            return
        
        try:
            import asyncio
            
            signal_data = {
                "code": signal.code,
                "name": signal.name,
                "type": signal.signal_type.value,
                "unified_score": signal.unified_score,
                "strategy_score": signal.strategy_score,
                "level": signal.level,
                "risk": signal.risk,
                "action": signal.action,
                "timestamp": signal.timestamp,
            }
            
            # 异步调用广播回调
            if asyncio.iscoroutinefunction(self.broadcast_callback):
                # 如果在事件循环中
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.broadcast_callback(signal_data))
                except RuntimeError:
                    # 不在事件循环中，创建新任务
                    asyncio.run(self.broadcast_callback(signal_data))
            else:
                self.broadcast_callback(signal_data)
            
            self.stats['broadcasted'] += 1
            logger.debug(f"Broadcasted signal: {signal.code}")
            
        except Exception as e:
            logger.warning(f"Failed to broadcast signal {signal.code}: {e}")
    
    def get_stats(self) -> Dict[str, int]:
        """获取处理统计"""
        return self.stats.copy()
    
    def reset_stats(self):
        """重置统计"""
        self.stats = {
            'total_processed': 0,
            'passed': 0,
            'filtered': 0,
            'rejected': 0,
            'broadcasted': 0,
        }


# 全局管道实例
_pipeline: Optional[SignalPipeline] = None


def get_signal_pipeline() -> SignalPipeline:
    """获取信号管道实例"""
    global _pipeline
    if _pipeline is None:
        _pipeline = SignalPipeline()
    return _pipeline


def process_radar_signals(stocks: List[Dict]) -> List[SignalResult]:
    """便捷方法：处理雷达信号"""
    return get_signal_pipeline().process_radar_batch(stocks)


def process_tomorrow_signals(candidates: List[Dict]) -> List[SignalResult]:
    """便捷方法：处理明日候选"""
    return get_signal_pipeline().process_tomorrow_batch(candidates)
