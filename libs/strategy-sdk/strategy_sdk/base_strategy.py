"""
策略基类定义
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class SignalType(Enum):
    """信号类型"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    ANOMALY = "anomaly"
    WARNING = "warning"
    LIMIT_UP = "limit_up"


@dataclass
class Signal:
    """策略信号"""
    type: SignalType
    stock_code: str
    stock_name: str
    confidence: float  # 0-1置信度
    timestamp: int
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "type": self.type.value,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "reason": self.reason,
            "metadata": self.metadata
        }


class BaseStrategy(ABC):
    """
    策略基类

    所有策略都需要继承此类并实现必要的方法

    示例:
        ```python
        from strategy_sdk import BaseStrategy, Signal, SignalType

        class MyStrategy(BaseStrategy):
            name = "my_strategy"
            version = "1.0.0"
            author = "your_name"
            description = "策略描述"

            async def initialize(self, config: Dict):
                self.threshold = config.get('threshold', 0.03)

            async def analyze(self, features: Dict) -> List[Signal]:
                if features['price_change_rate'] > self.threshold:
                    return [Signal(
                        type=SignalType.ANOMALY,
                        stock_code=features['code'],
                        stock_name=features['name'],
                        confidence=0.85,
                        timestamp=int(datetime.now().timestamp()),
                        reason="价格快速上涨"
                    )]
                return []
        ```
    """

    # 策略元数据（子类必须定义）
    name: str = ""
    version: str = ""
    author: str = ""
    description: str = ""

    # 依赖特征列表
    required_features: List[str] = []

    # 参数默认值
    default_parameters: Dict[str, Any] = {}

    def __init__(self):
        """初始化策略"""
        self.config: Dict = {}
        self.is_initialized = False
        self._validate_metadata()

    def _validate_metadata(self):
        """验证策略元数据"""
        if not self.name:
            raise ValueError(f"Strategy must define 'name'")
        if not self.version:
            raise ValueError(f"Strategy '{self.name}' must define 'version'")
        if not self.author:
            raise ValueError(f"Strategy '{self.name}' must define 'author'")

    @abstractmethod
    async def initialize(self, config: Dict):
        """
        初始化策略

        Args:
            config: 配置字典，包含策略参数
        """
        pass

    @abstractmethod
    async def analyze(self, features: Dict) -> List[Signal]:
        """
        分析特征并生成信号

        Args:
            features: 特征字典，包含股票的各项指标

        Returns:
            信号列表
        """
        pass

    async def on_market_open(self):
        """开盘回调（可选实现）"""
        pass

    async def on_market_close(self):
        """收盘回调（可选实现）"""
        pass

    async def on_feature_update(self, feature_name: str, value: Any):
        """特征更新回调（可选实现）"""
        pass

    def get_metadata(self) -> Dict:
        """获取策略元数据"""
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "required_features": self.required_features,
            "default_parameters": self.default_parameters
        }

    def validate_features(self, features: Dict) -> bool:
        """验证特征是否满足要求"""
        for required in self.required_features:
            if required not in features:
                return False
        return True