"""
市场数据模型 - 股票行情、K线等数据结构定义
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class MarketData:
    """实时市场数据"""
    
    code: str  # 股票代码
    name: str  # 股票名称
    current_price: float  # 当前价格
    open: float  # 开盘价
    high: float  # 最高价
    low: float  # 最低价
    volume: float  # 成交量
    amount: float  # 成交额
    turnover: float  # 换手率
    timestamp: datetime  # 时间戳
    
    # 可选字段
    close: Optional[float] = None  # 收盘价（仅收盘后有）
    change_percent: Optional[float] = None  # 涨跌幅
    amplitude: Optional[float] = None  # 振幅


@dataclass
class BarData:
    """K线数据"""
    
    code: str  # 股票代码
    datetime: datetime  # 时间
    open: float  # 开盘价
    high: float  # 最高价
    low: float  # 最低价
    close: float  # 收盘价
    volume: float  # 成交量
    amount: Optional[float] = None  # 成交额
    
    # 技术指标（可选）
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'code': self.code,
            'datetime': self.datetime,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'amount': self.amount,
        }
