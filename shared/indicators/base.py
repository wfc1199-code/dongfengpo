"""
指标基类 - 所有技术指标的基础抽象类
"""

from abc import ABC, abstractmethod
from typing import Any, Union
import pandas as pd
import numpy as np


class BaseIndicator(ABC):
    """
    技术指标基类
    
    所有技术指标必须继承此类并实现calculate方法。
    
    Example:
        >>> class MAIndicator(BaseIndicator):
        ...     def __init__(self, period=20):
        ...         self.period = period
        ...     
        ...     def calculate(self, data):
        ...         return data['close'].rolling(self.period).mean()
    """
    
    name: str = "BaseIndicator"
    
    @abstractmethod
    def calculate(self, data: Union[pd.DataFrame, np.ndarray]) -> Union[pd.Series, np.ndarray]:
        """
        计算指标值
        
        Args:
            data: 价格数据（DataFrame或ndarray）
        
        Returns:
            计算后的指标值
        """
        pass
    
    def __call__(self, data: Any) -> Any:
        """使指标对象可调用"""
        return self.calculate(data)
    
    def __repr__(self) -> str:
        return f"{self.name}()"
