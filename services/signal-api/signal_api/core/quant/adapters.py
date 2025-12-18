"""
策略适配器 (Strategy Adapters)

连接现有功能模块与 AI 量化策略：
1. IgnitionAdapter - 盯盘雷达 → 点火策略
2. AmbushAdapter - 明日潜力 → 潜伏策略

适配器负责：
- 数据格式转换
- 信号增强
- 风控检查前置
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .scorer import get_scorer, StockMetrics, ScoringResult, StrengthLevel, RiskLevel
from .strategies.ignition import IgnitionStrategy, IgnitionConfig
from .strategies.ambush import AmbushStrategy, AmbushConfig
from .risk.manager import RiskManager

logger = logging.getLogger(__name__)


@dataclass
class RadarSignal:
    """盯盘雷达信号（增强版）"""
    code: str
    name: str
    price: float
    change_pct: float
    
    # 统一评分
    unified_score: float
    strength_level: str
    risk_level: str
    
    # 点火策略增强
    ignition_score: float
    ignition_triggered: bool
    ignition_reason: str
    
    # 时间信息
    detected_time: str
    seal_time: Optional[str] = None
    
    # 风控状态
    risk_passed: bool = True
    risk_warnings: List[str] = None
    
    # 操作建议
    action: str = "观察"  # 买入/观察/回避
    
    def __post_init__(self):
        if self.risk_warnings is None:
            self.risk_warnings = []


@dataclass
class TomorrowCandidate:
    """明日潜力候选（增强版）"""
    code: str
    name: str
    price: float
    
    # 统一评分
    unified_score: float
    strength_level: str
    
    # 潜伏策略增强
    ambush_score: float
    ambush_triggered: bool
    ambush_factors: Dict[str, float]
    
    # 晋级概率
    probability: float
    
    # 日期信息
    first_board_date: str
    first_board_time: str
    
    # 风险评估
    risks: List[str] = None
    
    def __post_init__(self):
        if self.risks is None:
            self.risks = []


class IgnitionAdapter:
    """
    点火策略适配器
    
    将盯盘雷达数据 → 点火策略评估 → 生成增强信号
    """
    
    def __init__(self, risk_manager: Optional[RiskManager] = None):
        """初始化适配器"""
        self.scorer = get_scorer()
        self.ignition = IgnitionStrategy()
        self.risk_manager = risk_manager
        logger.info("IgnitionAdapter initialized")
    
    def process_radar_stock(
        self,
        stock_data: Dict[str, Any],
        market_data: Optional[Dict] = None
    ) -> RadarSignal:
        """
        处理单只雷达股票，生成增强信号
        
        Args:
            stock_data: 盯盘雷达原始数据
            market_data: 可选的行情数据（分钟线）
            
        Returns:
            RadarSignal: 增强后的雷达信号
        """
        code = stock_data.get('code', '')
        name = stock_data.get('name', '')
        price = float(stock_data.get('price', 0))
        change_pct = float(stock_data.get('changePercent', 0))
        turnover_rate = float(stock_data.get('turnoverRate', 0))
        amount = float(stock_data.get('amount', 0))
        volume_ratio = float(stock_data.get('volumeRatio', 1.0))
        seal_time = stock_data.get('sealTime', None)
        
        # 1. 统一评分
        metrics = StockMetrics(
            code=code,
            name=name,
            price=price,
            change_pct=change_pct,
            turnover_rate=turnover_rate,
            amount=amount,
            volume_ratio=volume_ratio,
        )
        score_result = self.scorer.score(metrics)
        
        # 2. 点火策略评估
        ignition_score, ignition_triggered, ignition_reason = self._evaluate_ignition(
            stock_data, score_result
        )
        
        # 3. 风控检查
        risk_passed, risk_warnings = self._check_risk(stock_data, score_result)
        
        # 4. 确定操作建议
        action = self._determine_action(
            score_result, ignition_triggered, risk_passed
        )
        
        return RadarSignal(
            code=code,
            name=name,
            price=price,
            change_pct=change_pct,
            unified_score=score_result.total_score,
            strength_level=score_result.strength_level.value,
            risk_level=score_result.risk_level.value,
            ignition_score=ignition_score,
            ignition_triggered=ignition_triggered,
            ignition_reason=ignition_reason,
            detected_time=datetime.now().strftime("%H:%M:%S"),
            seal_time=seal_time,
            risk_passed=risk_passed,
            risk_warnings=risk_warnings,
            action=action,
        )
    
    def _evaluate_ignition(
        self,
        stock_data: Dict,
        score_result: ScoringResult
    ) -> tuple:
        """
        评估点火策略条件
        
        P0修复：集成真实分钟线数据
        - 优先使用 DataManager 获取分钟线
        - 调用真正的 IgnitionStrategy.generate_signal()
        - 无数据时回退到简化评估
        """
        code = stock_data.get('code', '')
        ignition_score = 0.0
        reasons = []
        triggered = False
        
        # 尝试获取真实分钟线数据
        try:
            import os
            from .data.manager import DataManager, DataManagerConfig
            
            # 从环境变量读取 TUSHARE_TOKEN
            token = os.environ.get('TUSHARE_TOKEN')
            dm = DataManager(DataManagerConfig(tushare_token=token))
            minute_df = dm.get_minute(code, days=1, freq='1min')
            
            if minute_df is not None and len(minute_df) >= 20:
                # 使用真实分钟线数据进行点火评估
                self.ignition.calculate_factors(minute_df)
                
                # 获取最新一根K线的信号
                latest_index = len(minute_df) - 1
                signal = self.ignition.generate_signal(latest_index)
                
                if signal is not None:
                    # 真实点火信号触发
                    ignition_score = signal.confidence * 100
                    triggered = True
                    reasons.append(signal.reason)
                    
                    # 添加因子详情
                    factors = signal.factors or {}
                    if factors.get('minute_volume_ratio', 0) >= 3:
                        reasons.append(f"量比{factors.get('minute_volume_ratio', 0):.1f}x")
                    
                    logger.info(f"Ignition真实评估 {code}: score={ignition_score:.1f}, triggered={triggered}")
                    return ignition_score, triggered, "; ".join(reasons)
                else:
                    # 有数据但未触发信号
                    logger.debug(f"Ignition未触发 {code}: 数据正常但条件不满足")
            else:
                logger.debug(f"Ignition回退简化评估 {code}: 分钟线数据不足")
                
        except Exception as e:
            logger.warning(f"Ignition真实评估失败 {code}: {e}, 使用简化评估")
        
        # === 回退：简化的点火评估（无分钟线数据时） ===
        volume_ratio = float(stock_data.get('volumeRatio', 1.0))
        change_pct = float(stock_data.get('changePercent', 0))
        turnover_rate = float(stock_data.get('turnoverRate', 0))
        
        # 条件1: 量比 > 3 (资金涌入)
        if volume_ratio >= 3:
            ignition_score += 30
            reasons.append(f"量比{volume_ratio:.1f}x放量")
        elif volume_ratio >= 2:
            ignition_score += 15
        
        # 条件2: 涨幅 > 4% (突破)
        if change_pct >= 7:
            ignition_score += 40
            reasons.append(f"涨幅{change_pct:.1f}%强势突破")
        elif change_pct >= 4:
            ignition_score += 25
            reasons.append(f"涨幅{change_pct:.1f}%突破")
        
        # 条件3: 高换手 (活跃)
        if turnover_rate >= 10:
            ignition_score += 20
        elif turnover_rate >= 5:
            ignition_score += 10
        
        # 条件4: 综合评分高
        if score_result.total_score >= 70:
            ignition_score += 10
        
        triggered = ignition_score >= 60
        reason = "; ".join(reasons) if reasons else "条件不足"
        
        return ignition_score, triggered, reason
    
    def _check_risk(
        self,
        stock_data: Dict,
        score_result: ScoringResult
    ) -> tuple:
        """风控检查 - P0修复：实际调用 RiskManager.check_buy_signal()"""
        warnings = []
        passed = True
        
        # 风险1: 涨幅过高
        if score_result.risk_level == RiskLevel.HIGH:
            warnings.append("高位风险：涨幅>7%")
        
        # 风险2: 换手过高
        turnover = float(stock_data.get('turnoverRate', 0))
        if turnover >= 20:
            warnings.append(f"换手率{turnover:.1f}%过高")
        
        # 风险3: 尾盘拉升
        seal_time = stock_data.get('sealTime', '')
        if seal_time and seal_time >= '14:30':
            warnings.append("尾盘拉升，谨慎追高")
        
        # P0修复：实际调用 RiskManager 进行风控检查
        if self.risk_manager:
            try:
                # 假设信号价值为10万进行风控检查
                proposed_value = 100000
                code = stock_data.get('code', '')
                sector = stock_data.get('theme', '')
                
                risk_result = self.risk_manager.check_buy_signal(
                    symbol=code,
                    proposed_value=proposed_value,
                    sector=sector
                )
                
                if not risk_result.is_allowed:
                    passed = False
                    warnings.append(f"风控拒绝: {risk_result.message}")
                    logger.warning(f"风控拒绝 {code}: {risk_result.action.value}")
            except Exception as e:
                logger.error(f"风控检查失败 {stock_data.get('code', '?')}: {e}")
                # 风控检查失败时，保守处理：通过但添加警告
                warnings.append("风控检查异常，请人工确认")
        
        return passed, warnings
    
    def _determine_action(
        self,
        score_result: ScoringResult,
        ignition_triggered: bool,
        risk_passed: bool
    ) -> str:
        """确定操作建议"""
        if not risk_passed:
            return "回避"
        
        if ignition_triggered and score_result.total_score >= 70:
            return "买入"
        elif ignition_triggered or score_result.total_score >= 60:
            return "观察"
        else:
            return "观察"
    
    def process_batch(
        self,
        stocks: List[Dict[str, Any]]
    ) -> List[RadarSignal]:
        """批量处理雷达股票"""
        signals = []
        for stock in stocks:
            try:
                signal = self.process_radar_stock(stock)
                signals.append(signal)
            except Exception as e:
                logger.warning(f"处理股票失败 {stock.get('code', '?')}: {e}")
        
        # 按点火分数排序
        signals.sort(key=lambda x: x.ignition_score, reverse=True)
        return signals


class AmbushAdapter:
    """
    潜伏策略适配器
    
    将明日潜力数据 → 潜伏策略评估 → 生成增强候选
    """
    
    def __init__(self):
        """初始化适配器"""
        self.scorer = get_scorer()
        self.ambush = AmbushStrategy()
        logger.info("AmbushAdapter initialized")
    
    def process_candidate(
        self,
        candidate_data: Dict[str, Any],
        historical_data: Optional[Dict] = None
    ) -> TomorrowCandidate:
        """
        处理单只二板候选，生成增强结果
        
        Args:
            candidate_data: 明日潜力原始数据
            historical_data: 可选的历史K线数据
            
        Returns:
            TomorrowCandidate: 增强后的候选
        """
        code = candidate_data.get('code', '')
        name = candidate_data.get('name', '')
        price = float(candidate_data.get('currentPrice', 0))
        change_pct = float(candidate_data.get('changePercent', 0))
        turnover_rate = float(candidate_data.get('turnoverRate', 0))
        amount = float(candidate_data.get('sealAmount', 0)) * 1e8  # 转回元
        first_board_time = candidate_data.get('firstBoardTime', '')
        probability = candidate_data.get('probability', 0)
        
        # 1. 统一评分
        metrics = StockMetrics(
            code=code,
            name=name,
            price=price,
            change_pct=change_pct,
            turnover_rate=turnover_rate,
            amount=amount,
            volume_ratio=1.0,
        )
        score_result = self.scorer.score(metrics)
        
        # 2. 潜伏策略评估
        ambush_result = self._evaluate_ambush(
            candidate_data, score_result
        )
        
        # 强制使用因子：数据不足时跳过此股票
        if ambush_result[0] is None:
            logger.info(f"跳过 {code}: 历史数据不足，无法进行因子分析")
            return None
        
        ambush_score, ambush_triggered, ambush_factors = ambush_result
        
        # 3. 增强晋级概率
        enhanced_probability = self._enhance_probability(
            probability, ambush_score, score_result
        )
        
        # 4. 风险评估
        risks = self._assess_risks(candidate_data, score_result)
        
        return TomorrowCandidate(
            code=code,
            name=name,
            price=price,
            unified_score=score_result.total_score,
            strength_level=score_result.strength_level.value,
            ambush_score=ambush_score,
            ambush_triggered=ambush_triggered,
            ambush_factors=ambush_factors,
            probability=enhanced_probability,
            first_board_date=datetime.now().strftime("%Y-%m-%d"),
            first_board_time=first_board_time,
            risks=risks,
        )
    
    def _evaluate_ambush(
        self,
        candidate_data: Dict,
        score_result: ScoringResult
    ) -> tuple:
        """
        评估潜伏策略条件
        
        P0修复：集成真实30天历史数据
        - 优先使用 DataManager 获取日线数据
        - 调用真正的 AmbushStrategy.generate_signal()
        - 无数据时回退到简化评估
        """
        code = candidate_data.get('code', '')
        ambush_score = 0.0
        factors = {}
        triggered = False
        
        # 尝试获取真实30天历史数据
        try:
            import os
            from .data.manager import DataManager, DataManagerConfig
            
            # 从环境变量读取 TUSHARE_TOKEN
            token = os.environ.get('TUSHARE_TOKEN')
            dm = DataManager(DataManagerConfig(tushare_token=token))
            daily_df = dm.get_daily(code, days=30)
            
            if daily_df is not None and len(daily_df) >= 20:
                # 使用真实日线数据进行潜伏评估
                self.ambush.calculate_factors(daily_df)
                
                # 获取最新一天的信号
                latest_index = len(daily_df) - 1
                signal = self.ambush.generate_signal(latest_index)
                
                if signal is not None:
                    # 真实潜伏信号触发
                    ambush_score = signal.confidence * 100
                    triggered = True
                    
                    # 提取因子
                    signal_factors = signal.factors or {}
                    factors = {
                        'volume_ratio': signal_factors.get('volume_ratio', 0),
                        'bb_width': signal_factors.get('bb_width', 0),
                        'washout_pct': signal_factors.get('washout_pct', 0),
                        'obv_divergence': signal_factors.get('obv_divergence', 0),
                    }
                    
                    logger.info(f"Ambush真实评估 {code}: score={ambush_score:.1f}, triggered={triggered}")
                    return ambush_score, triggered, factors
                else:
                    # 有数据但未触发信号
                    logger.debug(f"Ambush未触发 {code}: 数据正常但条件不满足")
                    # 数据充足但未触发信号 - 返回0分
                    return 0.0, False, {}
            else:
                # 数据不足 - 跳过此股票 (强制使用因子)
                logger.info(f"Ambush跳过 {code}: 日线数据不足 ({len(daily_df) if daily_df is not None else 0}/20), 需要更多历史数据")
                return None, False, {}
                
        except Exception as e:
            # 数据获取失败 - 跳过此股票 (强制使用因子)
            logger.warning(f"Ambush跳过 {code}: 数据获取失败 ({e})")
            return None, False, {}
        
        # 不再使用简化回退逻辑
        return None, False, {}
    
    def _enhance_probability(
        self,
        base_probability: float,
        ambush_score: float,
        score_result: ScoringResult
    ) -> float:
        """增强晋级概率"""
        # 基础概率 + Ambush加成 + 统一评分加成
        enhanced = base_probability
        
        if ambush_score >= 70:
            enhanced += 10
        elif ambush_score >= 50:
            enhanced += 5
        
        if score_result.strength_level in [StrengthLevel.EXTREME_STRONG, StrengthLevel.STRONG_BREAK]:
            enhanced += 5
        
        return min(95, enhanced)
    
    def _assess_risks(
        self,
        candidate_data: Dict,
        score_result: ScoringResult
    ) -> List[str]:
        """评估风险"""
        risks = []
        
        # 炸板风险
        burst_count = int(candidate_data.get('burstCount', 0))
        if burst_count >= 2:
            risks.append(f"炸板{burst_count}次，封板不稳")
        
        # 尾盘封板风险
        first_board_time = candidate_data.get('firstBoardTime', '')
        if first_board_time and first_board_time >= '14:00':
            risks.append("尾盘封板，次日溢价可能不足")
        
        # 高换手风险
        turnover = float(candidate_data.get('turnoverRate', 0))
        if turnover >= 20:
            risks.append(f"换手{turnover:.1f}%过高，筹码分散")
        
        return risks
    
    def process_batch(
        self,
        candidates: List[Dict[str, Any]]
    ) -> List[TomorrowCandidate]:
        """批量处理候选"""
        results = []
        for candidate in candidates:
            try:
                result = self.process_candidate(candidate)
                results.append(result)
            except Exception as e:
                logger.warning(f"处理候选失败 {candidate.get('code', '?')}: {e}")
        
        # 按增强概率排序
        results.sort(key=lambda x: x.probability, reverse=True)
        return results


# 全局适配器实例
_ignition_adapter: Optional[IgnitionAdapter] = None
_ambush_adapter: Optional[AmbushAdapter] = None


def get_ignition_adapter() -> IgnitionAdapter:
    """获取点火适配器实例"""
    global _ignition_adapter
    if _ignition_adapter is None:
        _ignition_adapter = IgnitionAdapter()
    return _ignition_adapter


def get_ambush_adapter() -> AmbushAdapter:
    """获取潜伏适配器实例"""
    global _ambush_adapter
    if _ambush_adapter is None:
        _ambush_adapter = AmbushAdapter()
    return _ambush_adapter
