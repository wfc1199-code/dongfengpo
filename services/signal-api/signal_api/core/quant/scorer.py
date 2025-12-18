"""
统一评分系统 (Unified Scoring System)

实现5维加权评分算法，统一用于：
- 盯盘雷达 (Realtime Radar)
- 明日潜力 (Tomorrow Potential)
- AI量化策略 (Quant Strategies)

评分维度：
1. 涨幅异动 (40%) - 价格变动强度
2. 换手活跃 (25%) - 交易活跃度
3. 成交规模 (20%) - 资金参与度
4. 形态强势 (10%) - K线形态
5. 量价配合 (5%)  - 量价协同
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from functools import lru_cache
import logging
import os

logger = logging.getLogger(__name__)


class StrengthLevel(Enum):
    """强势等级分类"""
    EXTREME_STRONG = "极强"    # 100+分
    STRONG_BREAK = "强势突破"  # 80-99分
    ACCELERATING = "加速上涨"  # 60-79分
    STEADY_RISE = "稳步上升"   # 40-59分
    MILD_START = "温和启动"    # 20-39分
    WEAK = "弱势"              # <20分


class RiskLevel(Enum):
    """风险等级"""
    HIGH = "高风险"      # 涨幅>7%
    MEDIUM_HIGH = "中高" # 涨幅4-7%
    MEDIUM = "中等"      # 涨幅2-4%
    LOW = "低风险"       # 涨幅<2%


@dataclass
class ScorerConfig:
    """P1改进：可配置的评分参数"""
    # 权重配置
    weight_change: float = 0.40      # 涨幅异动权重
    weight_turnover: float = 0.25    # 换手活跃权重
    weight_volume: float = 0.20      # 成交规模权重
    weight_shape: float = 0.10       # 形态强势权重
    weight_combo: float = 0.05       # 量价配合权重
    
    # 阈值配置
    high_change_pct: float = 7.0     # 高涨幅阈值
    medium_change_pct: float = 4.0   # 中涨幅阈值
    high_turnover: float = 10.0      # 高换手阈值
    medium_turnover: float = 5.0     # 中换手阈值
    high_amount_yi: float = 10.0     # 大额成交阈值（亿）
    medium_amount_yi: float = 5.0    # 中额成交阈值（亿）
    
    # 强势等级阈值
    extreme_strong_score: float = 100.0
    strong_break_score: float = 80.0
    accelerating_score: float = 60.0
    steady_rise_score: float = 40.0
    mild_start_score: float = 20.0
    
    # 缓存配置
    cache_size: int = 1000           # LRU缓存大小
    
    @classmethod
    def from_env(cls) -> 'ScorerConfig':
        """从环境变量加载配置"""
        return cls(
            weight_change=float(os.getenv('SCORER_WEIGHT_CHANGE', '0.40')),
            weight_turnover=float(os.getenv('SCORER_WEIGHT_TURNOVER', '0.25')),
            high_change_pct=float(os.getenv('SCORER_HIGH_CHANGE_PCT', '7.0')),
            cache_size=int(os.getenv('SCORER_CACHE_SIZE', '1000')),
        )


@dataclass
class StockMetrics:
    """股票评分所需指标"""
    code: str
    name: str
    price: float
    change_pct: float      # 涨跌幅 %
    turnover_rate: float   # 换手率 %
    amount: float          # 成交额 (元)
    volume_ratio: float    # 量比
    high: Optional[float] = None  # 最高价
    low: Optional[float] = None   # 最低价
    open: Optional[float] = None  # 开盘价
    prev_close: Optional[float] = None  # 昨收
    
    def cache_key(self) -> str:
        """生成缓存键（用于LRU缓存）"""
        return f"{self.code}:{self.change_pct:.2f}:{self.turnover_rate:.2f}:{self.amount:.0f}"


@dataclass
class ScoringResult:
    """评分结果"""
    code: str
    name: str
    total_score: float
    
    # 分项得分
    change_score: float      # 涨幅异动得分
    turnover_score: float    # 换手活跃得分
    volume_score: float      # 成交规模得分
    shape_score: float       # 形态强势得分
    combo_score: float       # 量价配合得分
    
    # 等级
    strength_level: StrengthLevel
    risk_level: RiskLevel
    
    # 原始指标
    metrics: StockMetrics
    
    # 信号原因
    reasons: List[str]


class UnifiedScorer:
    """
    统一5维评分器
    
    P1改进：
    - 支持可配置的权重和阈值
    - 添加 LRU 缓存提升性能
    
    Usage:
        scorer = UnifiedScorer()
        result = scorer.score(StockMetrics(...))
    """
    
    def __init__(self, config: Optional[ScorerConfig] = None):
        """初始化评分器"""
        self.config = config or ScorerConfig()
        
        # 设置权重
        self.WEIGHTS = {
            'change': self.config.weight_change,
            'turnover': self.config.weight_turnover,
            'volume': self.config.weight_volume,
            'shape': self.config.weight_shape,
            'combo': self.config.weight_combo,
        }
        
        # 初始化缓存
        self._cache: Dict[str, ScoringResult] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        logger.info(f"UnifiedScorer initialized with cache_size={self.config.cache_size}")
    
    def score(self, metrics: StockMetrics) -> ScoringResult:
        """
        计算综合评分
        
        P1改进：添加缓存支持
        
        Args:
            metrics: 股票指标数据
            
        Returns:
            ScoringResult: 评分结果
        """
        # P1改进：检查缓存
        cache_key = metrics.cache_key()
        if cache_key in self._cache:
            self._cache_hits += 1
            return self._cache[cache_key]
        
        self._cache_misses += 1
        
        # 1. 涨幅异动评分 (满分100)
        change_score = self._score_change(metrics.change_pct)
        
        # 2. 换手活跃评分 (满分60)
        turnover_score = self._score_turnover(metrics.turnover_rate)
        
        # 3. 成交规模评分 (满分50)
        volume_score = self._score_volume(metrics.amount)
        
        # 4. 形态强势评分 (满分30)
        shape_score = self._score_shape(metrics)
        
        # 5. 量价配合评分 (满分25)
        combo_score = self._score_combo(metrics)
        
        # 计算加权总分
        total_score = (
            change_score * self.WEIGHTS['change'] +
            turnover_score * self.WEIGHTS['turnover'] +
            volume_score * self.WEIGHTS['volume'] +
            shape_score * self.WEIGHTS['shape'] +
            combo_score * self.WEIGHTS['combo']
        )
        
        # 确定强势等级
        strength_level = self._get_strength_level(total_score)
        
        # 确定风险等级
        risk_level = self._get_risk_level(metrics.change_pct)
        
        # 生成信号原因
        reasons = self._generate_reasons(metrics, change_score, turnover_score, volume_score)
        
        result = ScoringResult(
            code=metrics.code,
            name=metrics.name,
            total_score=round(total_score, 1),
            change_score=round(change_score, 1),
            turnover_score=round(turnover_score, 1),
            volume_score=round(volume_score, 1),
            shape_score=round(shape_score, 1),
            combo_score=round(combo_score, 1),
            strength_level=strength_level,
            risk_level=risk_level,
            metrics=metrics,
            reasons=reasons,
        )
        
        # P1改进：存入缓存（LRU淘汰策略）
        if len(self._cache) >= self.config.cache_size:
            # 简单LRU：删除最早的缓存项
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[cache_key] = result
        
        return result
    
    def _score_change(self, change_pct: float) -> float:
        """
        涨幅异动评分
        
        >7%: 100分 (涨停级别)
        >4%: 70分 (强势)
        >2%: 40分 (活跃)
        >0.8%: 20分 (温和)
        其他: 0-20分
        """
        if change_pct >= 7:
            return 100
        elif change_pct >= 4:
            return 70 + (change_pct - 4) * 10  # 70-100
        elif change_pct >= 2:
            return 40 + (change_pct - 2) * 15  # 40-70
        elif change_pct >= 0.8:
            return 20 + (change_pct - 0.8) * 16.7  # 20-40
        elif change_pct > 0:
            return change_pct * 25  # 0-20
        else:
            return 0
    
    def _score_turnover(self, turnover_rate: float) -> float:
        """
        换手活跃评分
        
        >10%: 60分 (极度活跃)
        >5%: 40分 (活跃)
        >2%: 25分 (一般)
        其他: 0-25分
        """
        if turnover_rate >= 10:
            return 60
        elif turnover_rate >= 5:
            return 40 + (turnover_rate - 5) * 4  # 40-60
        elif turnover_rate >= 2:
            return 25 + (turnover_rate - 2) * 5  # 25-40
        else:
            return min(turnover_rate * 12.5, 25)  # 0-25
    
    def _score_volume(self, amount: float) -> float:
        """
        成交规模评分 (amount单位：元)
        
        >10亿: 50分
        >5亿: 30分
        >1亿: 15分
        其他: 0-15分
        """
        amount_yi = amount / 1e8  # 转换为亿
        
        if amount_yi >= 10:
            return 50
        elif amount_yi >= 5:
            return 30 + (amount_yi - 5) * 4  # 30-50
        elif amount_yi >= 1:
            return 15 + (amount_yi - 1) * 3.75  # 15-30
        else:
            return amount_yi * 15  # 0-15
    
    def _score_shape(self, metrics: StockMetrics) -> float:
        """
        形态强势评分
        
        收盘位置 = (收盘-最低) / (最高-最低)
        >90%: 30分 (强势收高)
        >80%: 20分 (较强)
        >70%: 15分 (一般)
        其他: 0-15分
        """
        if metrics.high is None or metrics.low is None:
            # 无高低价数据，根据涨幅估算
            if metrics.change_pct >= 5:
                return 25
            elif metrics.change_pct >= 2:
                return 15
            else:
                return 5
        
        if metrics.high == metrics.low:
            return 30 if metrics.change_pct > 0 else 0
        
        close_position = (metrics.price - metrics.low) / (metrics.high - metrics.low)
        
        if close_position >= 0.9:
            return 30
        elif close_position >= 0.8:
            return 20 + (close_position - 0.8) * 100  # 20-30
        elif close_position >= 0.7:
            return 15 + (close_position - 0.7) * 50   # 15-20
        else:
            return close_position * 21.4  # 0-15
    
    def _score_combo(self, metrics: StockMetrics) -> float:
        """
        量价配合评分
        
        涨幅>3% 且 换手>3%: 25分
        涨幅>2% 且 换手>2%: 15分
        量比>3: 10分
        其他: 0-10分
        """
        score = 0
        
        if metrics.change_pct > 3 and metrics.turnover_rate > 3:
            score = 25
        elif metrics.change_pct > 2 and metrics.turnover_rate > 2:
            score = 15
        elif metrics.volume_ratio > 3:
            score = 10
        elif metrics.volume_ratio > 1.5:
            score = 5
        
        return score
    
    def _get_strength_level(self, total_score: float) -> StrengthLevel:
        """根据总分确定强势等级"""
        if total_score >= 100:
            return StrengthLevel.EXTREME_STRONG
        elif total_score >= 80:
            return StrengthLevel.STRONG_BREAK
        elif total_score >= 60:
            return StrengthLevel.ACCELERATING
        elif total_score >= 40:
            return StrengthLevel.STEADY_RISE
        elif total_score >= 20:
            return StrengthLevel.MILD_START
        else:
            return StrengthLevel.WEAK
    
    def _get_risk_level(self, change_pct: float) -> RiskLevel:
        """根据涨幅确定风险等级"""
        if change_pct >= 7:
            return RiskLevel.HIGH
        elif change_pct >= 4:
            return RiskLevel.MEDIUM_HIGH
        elif change_pct >= 2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_reasons(
        self,
        metrics: StockMetrics,
        change_score: float,
        turnover_score: float,
        volume_score: float
    ) -> List[str]:
        """生成信号原因列表"""
        reasons = []
        
        # 涨幅原因
        if metrics.change_pct >= 7:
            reasons.append(f"涨幅{metrics.change_pct:.2f}%达涨停级别")
        elif metrics.change_pct >= 4:
            reasons.append(f"涨幅{metrics.change_pct:.2f}%强势")
        elif metrics.change_pct >= 2:
            reasons.append(f"涨幅{metrics.change_pct:.2f}%活跃")
        
        # 换手原因
        if metrics.turnover_rate >= 10:
            reasons.append(f"换手{metrics.turnover_rate:.1f}%极活跃")
        elif metrics.turnover_rate >= 5:
            reasons.append(f"换手{metrics.turnover_rate:.1f}%活跃")
        
        # 成交额原因
        amount_yi = metrics.amount / 1e8
        if amount_yi >= 10:
            reasons.append(f"成交{amount_yi:.1f}亿大资金")
        elif amount_yi >= 5:
            reasons.append(f"成交{amount_yi:.1f}亿较活跃")
        
        # 量比原因
        if metrics.volume_ratio >= 3:
            reasons.append(f"量比{metrics.volume_ratio:.1f}放量")
        
        return reasons if reasons else ["综合评分"]
    
    def score_batch(self, metrics_list: List[StockMetrics]) -> List[ScoringResult]:
        """
        批量评分
        
        Args:
            metrics_list: 股票指标列表
            
        Returns:
            按总分降序排列的评分结果列表
        """
        results = [self.score(m) for m in metrics_list]
        results.sort(key=lambda x: x.total_score, reverse=True)
        return results
    
    def to_dict(self, result: ScoringResult) -> Dict[str, Any]:
        """将评分结果转换为字典（用于API响应）"""
        return {
            "code": result.code,
            "name": result.name,
            "total_score": result.total_score,
            "scores": {
                "change": result.change_score,
                "turnover": result.turnover_score,
                "volume": result.volume_score,
                "shape": result.shape_score,
                "combo": result.combo_score,
            },
            "strength_level": result.strength_level.value,
            "risk_level": result.risk_level.value,
            "reasons": result.reasons,
            "metrics": {
                "change_pct": result.metrics.change_pct,
                "turnover_rate": result.metrics.turnover_rate,
                "amount": result.metrics.amount,
                "volume_ratio": result.metrics.volume_ratio,
            }
        }


# 全局评分器实例
_scorer: Optional[UnifiedScorer] = None


def get_scorer() -> UnifiedScorer:
    """获取全局评分器实例"""
    global _scorer
    if _scorer is None:
        _scorer = UnifiedScorer()
    return _scorer
