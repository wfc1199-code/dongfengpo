"""
实时引擎 - 每3秒循环

职责:
- 每3秒执行扫描循环
- 协调: 异动检测 → 策略评估 → 风控检查 → 信号推送
- 管理引擎生命周期(启动/停止)

V20设计:
    loop Every 3 Seconds
        获取快照 → 匹配信号 → 风控检查 → 推送信号
"""

import asyncio
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

from .anomaly_scanner import AnomalyScanner, AnomalyCandidate, get_scanner, ScannerConfig
from .scorer import get_scorer, StockMetrics
from .adapters import IgnitionAdapter
from .risk.manager import RiskManager
from .reviewer import get_ai_reviewer
from .market_monitor import MarketMonitor

logger = logging.getLogger(__name__)


class EngineState(Enum):
    """引擎状态"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class EngineConfig:
    """引擎配置"""
    scan_interval: int = 3              # 扫描间隔(秒)
    max_signals_per_cycle: int = 10     # 每轮最多推送信号数
    enable_risk_check: bool = True      # 启用风控检查
    enable_strategy_eval: bool = True   # 启用策略评估
    auto_clear_daily: bool = True       # 每日自动清理


@dataclass
class Signal:
    """推送信号"""
    code: str
    name: str
    price: float
    change_pct: float
    anomaly_score: float        # 异动分数
    unified_score: float        # 统一评分
    ignition_score: float       # 点火评分
    strength_level: str         # 强势等级
    risk_level: str             # 风险等级
    risk_passed: bool           # 风控通过
    risk_reasons: List[str]     # 风控原因
    signal_type: str            # 信号类型
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "code": self.code,
            "name": self.name,
            "price": self.price,
            "changePct": self.change_pct,
            "anomalyScore": self.anomaly_score,
            "unifiedScore": self.unified_score,
            "ignitionScore": self.ignition_score,
            "strengthLevel": self.strength_level,
            "riskLevel": self.risk_level,
            "riskPassed": self.risk_passed,
            "riskReasons": self.risk_reasons,
            "signalType": self.signal_type,
            "createdAt": self.created_at.isoformat(),
        }


@dataclass
class EngineStats:
    """引擎统计"""
    total_scans: int = 0
    total_anomalies: int = 0
    total_signals: int = 0
    total_passed: int = 0
    total_blocked: int = 0
    last_scan_time: Optional[datetime] = None
    started_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "totalScans": self.total_scans,
            "totalAnomalies": self.total_anomalies,
            "totalSignals": self.total_signals,
            "totalPassed": self.total_passed,
            "totalBlocked": self.total_blocked,
            "lastScanTime": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
        }


class RealtimeEngine:
    """
    实时引擎
    
    核心循环:
        每3秒:
        1. 调用异动扫描器
        2. 对异动股票进行策略评估
        3. 风控检查
        4. AI复核 (Optional)
        5. 推送信号
    """
    
    def __init__(
        self,
        config: Optional[EngineConfig] = None,
        scanner: Optional[AnomalyScanner] = None,
        risk_manager: Optional[RiskManager] = None,
        broadcast_callback: Optional[Callable] = None,
    ):
        self.config = config or EngineConfig()
        self.scanner = scanner or get_scanner()
        self.risk_manager = risk_manager or RiskManager()
        self.broadcast_callback = broadcast_callback
        
        self._state = EngineState.STOPPED
        self._task: Optional[asyncio.Task] = None
        self._last_trade_date: Optional[date] = None
        self._pushed_codes: set = set()  # 今日已推送(避免重复)
        
        self.stats = EngineStats()
        self.ignition_adapter = IgnitionAdapter()
        self.scorer = get_scorer()
        
        # 新增: AI复核与市场监控
        self.ai_reviewer = get_ai_reviewer()
        self.market_monitor = MarketMonitor()
    
    @property
    def state(self) -> EngineState:
        return self._state
    
    async def start(self):
        """启动引擎"""
        if self._state == EngineState.RUNNING:
            logger.warning("引擎已在运行中")
            return
        
        self._state = EngineState.RUNNING
        self.stats.started_at = datetime.now()
        
        logger.info("🚀 实时引擎启动")
        
        # 初始更新一次市场状态
        await self.market_monitor.update()
        
        self._task = asyncio.create_task(self._run_loop())
    
    async def stop(self):
        """停止引擎"""
        if self._state != EngineState.RUNNING:
            return
        
        self._state = EngineState.STOPPED
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        logger.info("🛑 实时引擎停止")
    
    async def _run_loop(self):
        """主循环"""
        while self._state == EngineState.RUNNING:
            try:
                # 检查是否新交易日
                self._check_new_day()
                
                # 执行一轮扫描
                await self._run_cycle()
                
                # 等待下一轮
                await asyncio.sleep(self.config.scan_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"引擎循环错误: {e}")
                await asyncio.sleep(self.config.scan_interval)
    
    async def _run_cycle(self):
        """执行一轮扫描周期"""
        cycle_start = datetime.now()
        
        # 0. 更新市场状态 (异步, 每分钟)
        await self.market_monitor.update()
        
        # 1. 异动扫描
        candidates = await self.scanner.scan()
        self.stats.total_scans += 1
        self.stats.total_anomalies += len(candidates)
        self.stats.last_scan_time = cycle_start
        
        if not candidates:
            return
        
        # 2. 过滤已推送
        new_candidates = [c for c in candidates if c.code not in self._pushed_codes]
        
        if not new_candidates:
            logger.debug("本轮无新异动")
            return
        
        # 3. 策略评估 + 风控 + 推送
        signals_this_cycle = 0
        
        for candidate in new_candidates[:self.config.max_signals_per_cycle]:
            try:
                signal = await self._process_candidate(candidate)
                
                if signal:
                    self.stats.total_signals += 1
                    
                    if signal.risk_passed:
                        self.stats.total_passed += 1
                        await self._push_signal(signal)
                        self._pushed_codes.add(candidate.code)
                        signals_this_cycle += 1
                    else:
                        self.stats.total_blocked += 1
                        logger.info(f"风控拦截 {candidate.code}: {signal.risk_reasons}")
                        
            except Exception as e:
                logger.warning(f"处理候选 {candidate.code} 失败: {e}")
        
        if signals_this_cycle > 0:
            logger.info(f"本轮推送 {signals_this_cycle} 个信号")
    
    async def _process_candidate(self, candidate: AnomalyCandidate) -> Optional[Signal]:
        """处理单个候选股票"""
        
        # 1. 统一评分
        try:
            metrics = StockMetrics(
                code=candidate.code,
                name=candidate.name,
                price=candidate.price,
                change_pct=candidate.change_pct,
                turnover_rate=candidate.turnover_rate,
                amount=candidate.amount,
                volume_ratio=candidate.volume_ratio,
            )
            score_result = self.scorer.score(metrics)
            unified_score = score_result.total_score
            strength_level = score_result.strength_level.value
            risk_level = score_result.risk_level.value
        except Exception as e:
            logger.warning(f"评分失败 {candidate.code}: {e}")
            unified_score = candidate.anomaly_score
            strength_level = "中"
            risk_level = "中等"
        
        # 2. 点火策略评估 (如果启用)
        ignition_score = 0.0
        if self.config.enable_strategy_eval:
            try:
                stock_data = {
                    "code": candidate.code,
                    "name": candidate.name,
                    "price": candidate.price,
                    "changePercent": candidate.change_pct,
                    "turnoverRate": candidate.turnover_rate,
                    "amount": candidate.amount,
                    "volumeRatio": candidate.volume_ratio,
                }
                # 简化评估
                ignition_score = min(100, unified_score * 0.6 + candidate.anomaly_score * 0.4)
            except Exception as e:
                logger.debug(f"点火评估跳过 {candidate.code}: {e}")
        
        # 3. 风控检查
        risk_passed = True
        risk_reasons = []
        
        if self.config.enable_risk_check:
            try:
                check_result = self.risk_manager.check_buy_signal({
                    "code": candidate.code,
                    "name": candidate.name,
                    "price": candidate.price,
                    "change_pct": candidate.change_pct,
                })
                risk_passed = check_result.get("passed", True)
                risk_reasons = check_result.get("reasons", [])
            except Exception as e:
                logger.warning(f"风控检查失败 {candidate.code}: {e}")
        
        # 4. AI 复核 (新增: 仅对风控通过且分数较高的信号进行)
        ai_recommendation = ""
        ai_confidence = 0.0
        
        if risk_passed and unified_score >= 60 and self.ai_reviewer.enable_ai:
            try:
                # 构造临时信号对象供AI审核
                from .pipeline import SignalResult, SignalStatus
                temp_signal = SignalResult(
                    code=candidate.code,
                    name=candidate.name,
                    unified_score=unified_score,
                    strategy_score=ignition_score,
                    status=SignalStatus.PASSED,
                    raw_data=stock_data if 'stock_data' in locals() else {}
                )
                
                # 获取市场背景
                market_context = self.market_monitor.get_context()
                
                # 调用AI审核 (单个)
                # 注意: 这里简化为直接调用内部方法或单独封装，避免批量处理的复杂性
                # 实际生产中应放入队列批量处理
                review_results = await self.ai_reviewer.review_signals([temp_signal], market_context)
                
                if review_results:
                    res = review_results[0]
                    ai_confidence = res.ai_confidence
                    ai_recommendation = res.ai_recommendation
                    
                    # 如果AI强烈反对，则标记风控未通过
                    if "avoid" in res.final_action.lower() or "回避" in res.final_action:
                         risk_passed = False
                         risk_reasons.append(f"AI建议回避: {ai_recommendation}")
                         logger.info(f"AI拦截 {candidate.code}: {ai_recommendation}")
                         
            except Exception as e:
                logger.error(f"AI复核失败 {candidate.code}: {e}")

        return Signal(
            code=candidate.code,
            name=candidate.name,
            price=candidate.price,
            change_pct=candidate.change_pct,
            anomaly_score=candidate.anomaly_score,
            unified_score=unified_score,
            ignition_score=ignition_score,
            strength_level=strength_level,
            risk_level=risk_level,
            risk_passed=risk_passed,
            risk_reasons=risk_reasons,
            signal_type="anomaly",
            # 可以扩展Signal类添加ai_confidence字段，但在当前定义中暂时省略或放入risk_reasons
        )
    
    async def _push_signal(self, signal: Signal):
        """推送信号"""
        if not self.broadcast_callback:
            logger.debug(f"信号 {signal.code} (无推送回调)")
            return
        
        try:
            signal_data = signal.to_dict()
            
            if asyncio.iscoroutinefunction(self.broadcast_callback):
                await self.broadcast_callback(signal_data)
            else:
                self.broadcast_callback(signal_data)
            
            logger.info(f"📡 推送信号: {signal.code} {signal.name} 异动{signal.anomaly_score:.0f}分 统一{signal.unified_score:.0f}分")
            
        except Exception as e:
            logger.warning(f"推送信号失败 {signal.code}: {e}")
    
    def _check_new_day(self):
        """检查是否新交易日"""
        today = date.today()
        
        if self._last_trade_date != today:
            if self.config.auto_clear_daily:
                self._pushed_codes.clear()
                self.scanner.clear_detected()
                logger.info(f"新交易日 {today}, 已清空记录")
            
            self._last_trade_date = today
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "state": self._state.value,
            "stats": self.stats.to_dict(),
            "pushed_count": len(self._pushed_codes),
        }


# 全局单例
_engine: Optional[RealtimeEngine] = None


def get_engine(
    config: Optional[EngineConfig] = None,
    broadcast_callback: Optional[Callable] = None
) -> RealtimeEngine:
    """获取引擎单例"""
    global _engine
    if _engine is None:
        _engine = RealtimeEngine(config=config, broadcast_callback=broadcast_callback)
    return _engine


async def start_engine(broadcast_callback: Optional[Callable] = None):
    """启动引擎"""
    engine = get_engine(broadcast_callback=broadcast_callback)
    await engine.start()
    return engine


async def stop_engine():
    """停止引擎"""
    global _engine
    if _engine:
        await _engine.stop()
