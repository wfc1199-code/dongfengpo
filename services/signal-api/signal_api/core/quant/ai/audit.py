"""
AI Quant Platform - AI Audit Logger
Logging and auditing for AI-driven decisions.

Features:
- Records all AI inputs and outputs
- SQLite storage for traceability
- Query interface for analysis
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AuditRecord:
    """Single audit log entry."""
    id: Optional[int]
    timestamp: datetime
    symbol: str
    action: str  # 'analyze', 'recommend', 'execute'
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    confidence: float
    recommendation: str
    executed: bool = False
    execution_result: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "action": self.action,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "confidence": self.confidence,
            "recommendation": self.recommendation,
            "executed": self.executed,
            "execution_result": self.execution_result
        }


class AIAudit:
    """
    Audit logger for AI-driven trading decisions.
    
    Provides full traceability of:
    - What data was sent to AI
    - What AI recommended
    - Whether the recommendation was executed
    - What the outcome was
    
    Usage:
        audit = AIAudit("./quant_data/ai_audit.db")
        audit.log_analysis(symbol, input_factors, ai_result)
        audit.log_execution(record_id, success, details)
    """
    
    def __init__(self, db_path: str = "./quant_data/ai_audit.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_db()
        logger.info(f"AIAudit initialized at {self.db_path}")
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    input_data TEXT,
                    output_data TEXT,
                    confidence REAL,
                    recommendation TEXT,
                    executed INTEGER DEFAULT 0,
                    execution_result TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_audit_symbol 
                ON ai_audit(symbol)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_audit_timestamp 
                ON ai_audit(timestamp)
            """)
            conn.commit()
    
    def log_analysis(
        self,
        symbol: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        confidence: float,
        recommendation: str
    ) -> int:
        """
        Log an AI analysis.
        
        Args:
            symbol: Stock symbol
            input_data: Input factors sent to AI
            output_data: AI response
            confidence: Confidence score
            recommendation: AI recommendation
        
        Returns:
            Record ID for later reference
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO ai_audit 
                (timestamp, symbol, action, input_data, output_data, confidence, recommendation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                symbol,
                "analyze",
                json.dumps(input_data, ensure_ascii=False, default=str),
                json.dumps(output_data, ensure_ascii=False, default=str),
                confidence,
                recommendation
            ))
            conn.commit()
            
            record_id = cursor.lastrowid
            logger.debug(f"AI audit logged: {symbol} - {recommendation} (ID: {record_id})")
            
            return record_id
    
    def log_execution(
        self,
        record_id: int,
        executed: bool,
        result: Optional[str] = None
    ):
        """
        Update audit record with execution result.
        
        Args:
            record_id: Original audit record ID
            executed: Whether the signal was executed
            result: Execution result details
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE ai_audit 
                SET executed = ?, execution_result = ?
                WHERE id = ?
            """, (
                1 if executed else 0,
                result,
                record_id
            ))
            conn.commit()
            
            logger.debug(f"AI audit execution logged: ID {record_id} - {executed}")
    
    def get_recent(self, limit: int = 50) -> List[AuditRecord]:
        """Get recent audit records."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM ai_audit 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            records = []
            for row in cursor.fetchall():
                records.append(self._row_to_record(row))
            
            return records
    
    def get_by_symbol(self, symbol: str, limit: int = 20) -> List[AuditRecord]:
        """Get audit records for a specific symbol."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM ai_audit 
                WHERE symbol = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (symbol, limit))
            
            records = []
            for row in cursor.fetchall():
                records.append(self._row_to_record(row))
            
            return records
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get summary statistics of AI decisions."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Total counts
            total = conn.execute("SELECT COUNT(*) as cnt FROM ai_audit").fetchone()["cnt"]
            
            # By recommendation
            by_rec = conn.execute("""
                SELECT recommendation, COUNT(*) as cnt 
                FROM ai_audit 
                GROUP BY recommendation
            """).fetchall()
            
            # Execution rate
            executed = conn.execute("""
                SELECT COUNT(*) as cnt 
                FROM ai_audit 
                WHERE executed = 1
            """).fetchone()["cnt"]
            
            # Average confidence
            avg_conf = conn.execute("""
                SELECT AVG(confidence) as avg 
                FROM ai_audit
            """).fetchone()["avg"]
            
            return {
                "total_analyses": total,
                "by_recommendation": {r["recommendation"]: r["cnt"] for r in by_rec},
                "executed_count": executed,
                "execution_rate": executed / total if total > 0 else 0,
                "average_confidence": avg_conf or 0
            }
    
    def _row_to_record(self, row: sqlite3.Row) -> AuditRecord:
        """Convert database row to AuditRecord."""
        return AuditRecord(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            symbol=row["symbol"],
            action=row["action"],
            input_data=json.loads(row["input_data"]) if row["input_data"] else {},
            output_data=json.loads(row["output_data"]) if row["output_data"] else {},
            confidence=row["confidence"] or 0,
            recommendation=row["recommendation"] or "",
            executed=bool(row["executed"]),
            execution_result=row["execution_result"]
        )
    
    def cleanup_old(self, days: int = 90):
        """Delete records older than specified days."""
        from datetime import timedelta
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM ai_audit 
                WHERE timestamp < ?
            """, (cutoff,))
            conn.commit()
            
            logger.info(f"Cleaned up {cursor.rowcount} old AI audit records")
