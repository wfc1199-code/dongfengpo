"""
AI 审核模块 (AI Reviewer)

集成 DeepSeek AI 对信号进行复核：
1. 对 Top 候选进行 AI 分析
2. 增强信号置信度
3. 记录审核日志
4. 统计历史胜率

用于盯盘雷达和明日潜力的智能复核。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from pathlib import Path
import json
import logging

from .ai.deepseek_client import DeepSeekClient, AIAnalysisResult
from .pipeline import SignalResult, SignalStatus, SignalType

logger = logging.getLogger(__name__)

# 审核日志存储路径
AUDIT_LOG_DIR = Path(__file__).parent / "audit_logs"


@dataclass
class ReviewResult:
    """AI 审核结果"""
    signal: SignalResult
    ai_analysis: Optional[AIAnalysisResult] = None
    ai_confidence: float = 0.0
    ai_recommendation: str = ""
    final_action: str = ""
    review_time: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.signal.code,
            "name": self.signal.name,
            "unified_score": self.signal.unified_score,
            "strategy_score": self.signal.strategy_score,
            "ai_confidence": self.ai_confidence,
            "ai_recommendation": self.ai_recommendation,
            "final_action": self.final_action,
            "review_time": self.review_time,
        }


@dataclass
class DailyStats:
    """每日统计"""
    date: str
    total_signals: int = 0
    passed_signals: int = 0
    ai_reviewed: int = 0
    ai_approved: int = 0
    
    # 次日验证结果（需要次日更新）
    actual_winners: int = 0   # 实际盈利数
    actual_losers: int = 0    # 实际亏损数
    win_rate: float = 0.0     # 胜率
    
    def to_dict(self) -> Dict:
        return {
            "date": self.date,
            "total_signals": self.total_signals,
            "passed_signals": self.passed_signals,
            "ai_reviewed": self.ai_reviewed,
            "ai_approved": self.ai_approved,
            "actual_winners": self.actual_winners,
            "actual_losers": self.actual_losers,
            "win_rate": self.win_rate,
        }


class AIReviewer:
    """
    AI 信号审核器
    
    Usage:
        reviewer = AIReviewer()
        reviewed_signals = await reviewer.review_signals(signals, top_n=5)
    """
    
    def __init__(
        self,
        enable_ai: bool = True,
        top_n: int = 5,
        min_score_for_review: float = 60.0
    ):
        """
        初始化审核器
        
        Args:
            enable_ai: 是否启用 AI 审核（需要 DEEPSEEK_API_KEY）
            top_n: 只对 Top N 信号进行 AI 审核
            min_score_for_review: 最低审核分数
        """
        self.enable_ai = enable_ai
        self.top_n = top_n
        self.min_score_for_review = min_score_for_review
        
        # 初始化 DeepSeek 客户端（如果启用）
        self._ai_client: Optional[DeepSeekClient] = None
        if enable_ai:
            try:
                self._ai_client = DeepSeekClient()
                logger.info("AIReviewer initialized with DeepSeek")
            except Exception as e:
                logger.warning(f"DeepSeek 初始化失败，降级为无AI模式: {e}")
                self.enable_ai = False
        
        # 确保日志目录存在
        AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    async def review_signals(
        self,
        signals: List[SignalResult],
        market_context: Optional[str] = None
    ) -> List[ReviewResult]:
        """
        对信号列表进行 AI 审核
        
        Args:
            signals: 信号列表（应已按分数排序）
            market_context: 市场背景信息
            
        Returns:
            审核结果列表
        """
        results = []
        
        # 筛选需要审核的信号
        candidates = [
            s for s in signals
            if s.status == SignalStatus.PASSED
            and s.unified_score >= self.min_score_for_review
        ][:self.top_n]
        
        for signal in signals:
            if signal in candidates and self.enable_ai and self._ai_client:
                # 进行 AI 审核
                review_result = await self._ai_review_single(signal, market_context)
            else:
                # 不需要 AI 审核，直接通过
                review_result = ReviewResult(
                    signal=signal,
                    ai_confidence=0.0,
                    ai_recommendation="未审核",
                    final_action=signal.action,
                )
            
            results.append(review_result)
        
        # 记录审核日志
        self._log_audit(results)
        
        return results
    
    async def _ai_review_single(
        self,
        signal: SignalResult,
        market_context: Optional[str],
        max_retries: int = 3
    ) -> ReviewResult:
        """
        对单个信号进行 AI 审核
        
        P2改进：添加指数退避重试机制
        """
        import asyncio
        
        # 构建因子字典
        factors = {
            "unified_score": signal.unified_score,
            "strategy_score": signal.strategy_score,
            "level": signal.level,
            "risk": signal.risk,
        }
        
        if signal.raw_data:
            factors.update({
                "change_pct": signal.raw_data.get("changePercent", 0),
                "turnover_rate": signal.raw_data.get("turnoverRate", 0),
                "volume_ratio": signal.raw_data.get("volumeRatio", 1),
            })
        
        last_error = None
        for attempt in range(max_retries):
            try:
                # 调用 AI 分析
                ai_result = await self._ai_client.analyze_stock(
                    symbol=signal.code,
                    factors=factors,
                    market_context=market_context
                )
                
                # 根据 AI 结果确定最终操作
                final_action = self._determine_final_action(signal, ai_result)
                
                return ReviewResult(
                    signal=signal,
                    ai_analysis=ai_result,
                    ai_confidence=ai_result.confidence,
                    ai_recommendation=ai_result.recommendation,
                    final_action=final_action,
                )
                
            except Exception as e:
                last_error = e
                wait_time = (2 ** attempt) * 0.5  # 0.5s, 1s, 2s
                logger.warning(f"AI 审核重试 {signal.code} (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
        
        # 所有重试失败
        logger.error(f"AI 审核最终失败 {signal.code} after {max_retries} retries: {last_error}")
        return ReviewResult(
            signal=signal,
            ai_confidence=0.0,
            ai_recommendation=f"审核失败(重试{max_retries}次): {last_error}",
            final_action=signal.action,
        )
    
    def _determine_final_action(
        self,
        signal: SignalResult,
        ai_result: AIAnalysisResult
    ) -> str:
        """根据 AI 结果确定最终操作"""
        # AI 推荐 + 高置信度 → 采纳
        if ai_result.recommendation.lower() in ["buy", "买入"] and ai_result.confidence >= 0.7:
            return "AI推荐买入"
        elif ai_result.recommendation.lower() in ["avoid", "回避"] and ai_result.confidence >= 0.6:
            return "AI建议回避"
        else:
            # 保持原判断
            return signal.action
    
    def _log_audit(self, results: List[ReviewResult]):
        """记录审核日志"""
        try:
            today = date.today().isoformat()
            log_file = AUDIT_LOG_DIR / f"audit_{today}.jsonl"
            
            with open(log_file, "a", encoding="utf-8") as f:
                for result in results:
                    log_entry = result.to_dict()
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                    
        except Exception as e:
            logger.error(f"写入审核日志失败: {e}")
    
    def review_signals_sync(
        self,
        signals: List[SignalResult]
    ) -> List[ReviewResult]:
        """
        同步版本的审核（不使用 AI）
        
        用于不需要 AI 审核的场景
        """
        results = []
        for signal in signals:
            results.append(ReviewResult(
                signal=signal,
                ai_confidence=0.0,
                ai_recommendation="未启用AI",
                final_action=signal.action,
            ))
        return results


class StatsTracker:
    """
    历史统计追踪器 (SQLite版本)
    
    P0修复：使用 SQLite 替代 JSON 文件存储
    记录信号胜率、AI 准确率等指标
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """初始化统计器"""
        import sqlite3
        self.db_path = db_path or (AUDIT_LOG_DIR / "stats.db")
        AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        import sqlite3
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    total_signals INTEGER DEFAULT 0,
                    passed_signals INTEGER DEFAULT 0,
                    ai_reviewed INTEGER DEFAULT 0,
                    ai_approved INTEGER DEFAULT 0,
                    actual_winners INTEGER DEFAULT 0,
                    actual_losers INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            conn.close()
            logger.info(f"StatsTracker SQLite initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"初始化数据库失败: {e}")
    
    def _get_conn(self):
        """获取数据库连接"""
        import sqlite3
        return sqlite3.connect(str(self.db_path))
    
    def record_signals(
        self,
        signal_type: SignalType,
        total: int,
        passed: int,
        ai_reviewed: int = 0,
        ai_approved: int = 0
    ):
        """记录今日信号统计"""
        today = date.today().isoformat()
        
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # 使用 UPSERT 语法
            cursor.execute('''
                INSERT INTO daily_stats (date, total_signals, passed_signals, ai_reviewed, ai_approved)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    total_signals = total_signals + excluded.total_signals,
                    passed_signals = passed_signals + excluded.passed_signals,
                    ai_reviewed = ai_reviewed + excluded.ai_reviewed,
                    ai_approved = ai_approved + excluded.ai_approved,
                    updated_at = CURRENT_TIMESTAMP
            ''', (today, total, passed, ai_reviewed, ai_approved))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"记录信号统计失败: {e}")
    
    def update_results(
        self,
        date_str: str,
        winners: int,
        losers: int
    ):
        """更新某日的实际结果（用于次日验证）"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            total = winners + losers
            win_rate = winners / total if total > 0 else 0.0
            
            cursor.execute('''
                UPDATE daily_stats
                SET actual_winners = ?, actual_losers = ?, win_rate = ?, updated_at = CURRENT_TIMESTAMP
                WHERE date = ?
            ''', (winners, losers, win_rate, date_str))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"更新结果失败: {e}")
    
    def get_recent_stats(self, days: int = 7) -> List[DailyStats]:
        """获取最近 N 天的统计"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT date, total_signals, passed_signals, ai_reviewed, ai_approved,
                       actual_winners, actual_losers, win_rate
                FROM daily_stats
                ORDER BY date DESC
                LIMIT ?
            ''', (days,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [DailyStats(
                date=row[0],
                total_signals=row[1],
                passed_signals=row[2],
                ai_reviewed=row[3],
                ai_approved=row[4],
                actual_winners=row[5],
                actual_losers=row[6],
                win_rate=row[7]
            ) for row in rows]
        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            return []
    
    def get_summary(self) -> Dict[str, Any]:
        """获取总体统计摘要"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_days,
                    COALESCE(SUM(total_signals), 0) as total_signals,
                    COALESCE(SUM(actual_winners), 0) as total_winners,
                    COALESCE(SUM(actual_losers), 0) as total_losers,
                    COALESCE(SUM(ai_reviewed), 0) as ai_reviewed
                FROM daily_stats
            ''')
            
            row = cursor.fetchone()
            conn.close()
            
            if not row or row[0] == 0:
                return {
                    "total_days": 0,
                    "total_signals": 0,
                    "overall_win_rate": 0.0,
                }
            
            total_winners = row[2]
            total_losers = row[3]
            overall_win_rate = 0.0
            if total_winners + total_losers > 0:
                overall_win_rate = total_winners / (total_winners + total_losers)
            
            return {
                "total_days": row[0],
                "total_signals": row[1],
                "total_winners": total_winners,
                "total_losers": total_losers,
                "overall_win_rate": round(overall_win_rate * 100, 2),
                "ai_reviewed": row[4],
            }
        except Exception as e:
            logger.error(f"获取统计摘要失败: {e}")
            return {"total_days": 0, "total_signals": 0, "overall_win_rate": 0.0}


# 全局实例
_reviewer: Optional[AIReviewer] = None
_stats_tracker: Optional[StatsTracker] = None


def get_ai_reviewer(enable_ai: bool = True) -> AIReviewer:
    """获取 AI 审核器实例"""
    global _reviewer
    if _reviewer is None:
        _reviewer = AIReviewer(enable_ai=enable_ai)
    return _reviewer


def get_stats_tracker() -> StatsTracker:
    """获取统计追踪器实例"""
    global _stats_tracker
    if _stats_tracker is None:
        _stats_tracker = StatsTracker()
    return _stats_tracker
