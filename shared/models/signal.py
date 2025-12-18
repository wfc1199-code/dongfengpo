"""
信号模型 - 交易信号数据结构定义
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class SignalType(Enum):
    """信号类型"""
    BUY = "BUY"  # 买入
    SELL = "SELL"  # 卖出
    HOLD = "HOLD"  # 持有
    WATCH = "WATCH"  # 观察


@dataclass
class Signal:
    """交易信号"""
    
    code: str  # 股票代码
    name: str  # 股票名称
    signal_type: SignalType  # 信号类型
    confidence: float  # 置信度 0-100
    reason: str  # 信号原因
    strategy: str  # 策略名称
    timestamp: datetime  # 信号生成时间
    
    # 可选字段
    price: Optional[float] = None  # 价格
    detail: Optional[Dict[str, Any]] = None  # 详细信息
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'code': self.code,
            'name': self.name,
            'signal_type': self.signal_type.value,
            'confidence': self.confidence,
            'reason': self.reason,
            'strategy': self.strategy,
            'timestamp': self.timestamp.isoformat(),
            'price': self.price,
            'detail': self.detail,
        }
