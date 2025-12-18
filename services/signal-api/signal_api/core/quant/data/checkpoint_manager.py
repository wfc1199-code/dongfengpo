"""
AI Quant Platform - Checkpoint Manager
检查点管理器

功能:
- 数据同步进度跟踪
- 断点续传支持
- 缺失数据检测
- 自动恢复机制

用法:
    manager = CheckpointManager()
    
    # 保存进度
    manager.save_progress('000001', date='2025-12-17', bars=240, status='completed')
    
    # 获取未完成列表
    incomplete = manager.get_incomplete_symbols()
    
    # 恢复同步
    for symbol in incomplete:
        sync_symbol(symbol)
        manager.update_progress(symbol, status='completed')
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
import sqlite3
import threading

logger = logging.getLogger(__name__)


class SyncStatus(Enum):
    """同步状态"""
    PENDING = "pending"       # 待同步
    IN_PROGRESS = "in_progress"  # 同步中
    COMPLETED = "completed"   # 已完成
    PARTIAL = "partial"       # 部分完成
    FAILED = "failed"         # 失败
    SKIPPED = "skipped"       # 跳过


@dataclass
class SyncCheckpoint:
    """同步检查点"""
    symbol: str
    trade_date: str
    status: SyncStatus
    minute_bars: int = 0
    daily_bars: int = 0
    completeness: float = 0.0
    error_message: Optional[str] = None
    retries: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['status'] = self.status.value
        return d
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SyncCheckpoint':
        data['status'] = SyncStatus(data['status'])
        return cls(**data)


class CheckpointManager:
    """
    检查点管理器
    
    使用 SQLite 存储同步进度，支持：
    - 按日期跟踪每只股票的同步状态
    - 检测缺失数据
    - 自动恢复未完成的同步
    - 统计分析
    """
    
    def __init__(self, db_path: str = "./quant_data/checkpoints.db"):
        """
        初始化检查点管理器
        
        Args:
            db_path: SQLite 数据库路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        
        self._init_database()
        logger.info(f"CheckpointManager initialized at {self.db_path}")
    
    def _init_database(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    minute_bars INTEGER DEFAULT 0,
                    daily_bars INTEGER DEFAULT 0,
                    completeness REAL DEFAULT 0.0,
                    error_message TEXT,
                    retries INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(symbol, trade_date)
                )
            """)
            
            # 索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_symbol ON sync_checkpoints(symbol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON sync_checkpoints(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON sync_checkpoints(trade_date)")
            
            conn.commit()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        return conn
    
    def save_progress(
        self,
        symbol: str,
        trade_date: str,
        status: SyncStatus,
        minute_bars: int = 0,
        daily_bars: int = 0,
        completeness: float = 0.0,
        error_message: Optional[str] = None
    ) -> bool:
        """
        保存同步进度
        
        Args:
            symbol: 股票代码
            trade_date: 交易日期 (YYYY-MM-DD)
            status: 同步状态
            minute_bars: 分钟线数量
            daily_bars: 日线数量
            completeness: 完整度 (0-100)
            error_message: 错误信息
        """
        with self._lock:
            try:
                now = datetime.now().isoformat()
                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT INTO sync_checkpoints 
                        (symbol, trade_date, status, minute_bars, daily_bars, 
                         completeness, error_message, retries, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                        ON CONFLICT(symbol, trade_date) DO UPDATE SET
                            status = excluded.status,
                            minute_bars = excluded.minute_bars,
                            daily_bars = excluded.daily_bars,
                            completeness = excluded.completeness,
                            error_message = excluded.error_message,
                            updated_at = excluded.updated_at
                    """, (symbol, trade_date, status.value, minute_bars, daily_bars,
                          completeness, error_message, now, now))
                    conn.commit()
                return True
            except Exception as e:
                logger.error(f"Failed to save checkpoint for {symbol}: {e}")
                return False
    
    def get_progress(self, symbol: str, trade_date: str) -> Optional[SyncCheckpoint]:
        """获取单个股票的同步进度"""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM sync_checkpoints 
                WHERE symbol = ? AND trade_date = ?
            """, (symbol, trade_date)).fetchone()
            
            if row:
                return SyncCheckpoint(
                    symbol=row['symbol'],
                    trade_date=row['trade_date'],
                    status=SyncStatus(row['status']),
                    minute_bars=row['minute_bars'],
                    daily_bars=row['daily_bars'],
                    completeness=row['completeness'],
                    error_message=row['error_message'],
                    retries=row['retries'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
        return None
    
    def get_incomplete_symbols(self, trade_date: Optional[str] = None) -> List[str]:
        """
        获取未完成同步的股票列表
        
        Args:
            trade_date: 交易日期，默认今天
        """
        if trade_date is None:
            trade_date = datetime.now().strftime("%Y-%m-%d")
        
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT DISTINCT symbol FROM sync_checkpoints
                WHERE trade_date = ? 
                AND status IN ('pending', 'in_progress', 'partial', 'failed')
            """, (trade_date,)).fetchall()
            
            return [row['symbol'] for row in rows]
    
    def get_missing_symbols(
        self,
        all_symbols: List[str],
        trade_date: Optional[str] = None
    ) -> List[str]:
        """
        获取缺失数据的股票（从未同步过）
        
        Args:
            all_symbols: 完整股票列表
            trade_date: 交易日期
        """
        if trade_date is None:
            trade_date = datetime.now().strftime("%Y-%m-%d")
        
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT symbol FROM sync_checkpoints
                WHERE trade_date = ?
            """, (trade_date,)).fetchall()
            
            synced = {row['symbol'] for row in rows}
            return [s for s in all_symbols if s not in synced]
    
    def increment_retry(self, symbol: str, trade_date: str) -> int:
        """增加重试次数并返回新值"""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE sync_checkpoints 
                    SET retries = retries + 1, updated_at = ?
                    WHERE symbol = ? AND trade_date = ?
                """, (datetime.now().isoformat(), symbol, trade_date))
                conn.commit()
                
                row = conn.execute("""
                    SELECT retries FROM sync_checkpoints
                    WHERE symbol = ? AND trade_date = ?
                """, (symbol, trade_date)).fetchone()
                
                return row['retries'] if row else 0
    
    def get_stats(self, trade_date: Optional[str] = None) -> Dict[str, Any]:
        """获取同步统计"""
        if trade_date is None:
            trade_date = datetime.now().strftime("%Y-%m-%d")
        
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM sync_checkpoints
                WHERE trade_date = ?
                GROUP BY status
            """, (trade_date,)).fetchall()
            
            stats = {
                'date': trade_date,
                'total': 0,
                'completed': 0,
                'partial': 0,
                'failed': 0,
                'pending': 0,
                'in_progress': 0,
            }
            
            for row in rows:
                status = row['status']
                count = row['count']
                stats['total'] += count
                if status in stats:
                    stats[status] = count
            
            # 计算完成率
            stats['completion_rate'] = (
                stats['completed'] / stats['total'] * 100 
                if stats['total'] > 0 else 0
            )
            
            return stats
    
    def cleanup_old_records(self, keep_days: int = 30):
        """清理旧记录"""
        cutoff = (datetime.now() - timedelta(days=keep_days)).strftime("%Y-%m-%d")
        
        with self._lock:
            with self._get_connection() as conn:
                result = conn.execute("""
                    DELETE FROM sync_checkpoints
                    WHERE trade_date < ?
                """, (cutoff,))
                conn.commit()
                
                logger.info(f"Cleaned up {result.rowcount} old checkpoint records")
                return result.rowcount


# 全局单例
_checkpoint_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    """获取检查点管理器单例"""
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager()
    return _checkpoint_manager
