"""
策略基类 - 所有量化策略的基础抽象类

设计原则：
1. 统一接口 - 回测和实盘使用相同的策略代码
2. 参数化 - 所有参数可配置，支持参数优化
3. 可测试 - 纯函数设计，便于单元测试
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class SignalResult:
    """策略信号结果"""
    
    action: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float  # 0-100, 信号置信度
    reason: str  # 信号原因说明
    detail: Optional[Dict[str, Any]] = None  # 详细信息


class BaseStrategy(ABC):
    """
    策略基类
    
    所有策略必须继承此类并实现抽象方法。
    
    Attributes:
        name: 策略名称
        params: 参数定义（供优化器使用）
    
    Example:
        >>> class MyStrategy(BaseStrategy):
        ...     params = {
        ...         'threshold': {'type': 'float', 'range': [1.0, 10.0], 'default': 5.0}
        ...     }
        ...     
        ...     def generate_signal(self, data):
        ...         if data['price'] > self.threshold:
        ...             return SignalResult('BUY', 80, 'Price above threshold')
        ...         return None
    """
    
    name: str = "BaseStrategy"
    
    # 参数定义（子类需要覆盖）
    params: Dict[str, Dict[str, Any]] = {}
    
    def __init__(self, **kwargs):
        """
        初始化策略
        
        Args:
            **kwargs: 策略参数（key-value pairs）
        """
        # 设置默认值
        for param_name, param_config in self.params.items():
            setattr(self, param_name, param_config.get('default'))
        
        # 覆盖用户提供的参数
        for key, value in kwargs.items():
            if key in self.params:
                setattr(self, key, value)
            else:
                raise ValueError(f"Unknown parameter: {key}")
    
    @abstractmethod
    def generate_signal(self, data: Dict[str, Any]) -> Optional[SignalResult]:
        """
        生成交易信号（必须实现）
        
        Args:
            data: 股票数据字典，至少包含:
                - code: 股票代码
                - current_price: 当前价格
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - volume: 成交量
                - ...更多字段根据策略需要
        
        Returns:
            SignalResult: 信号结果，如果不产生信号则返回None
        """
        pass
    
    def on_bar(self, context: Any, bar: Dict[str, Any]) -> Optional[SignalResult]:
        """
        K线数据回调（回测用）
        
        Args:
            context: 回测上下文
            bar: K线数据
        
        Returns:
            SignalResult or None
        """
        return self.generate_signal(bar)
    
    def on_tick(self, context: Any, tick: Dict[str, Any]) -> Optional[SignalResult]:
        """
        实时行情回调（实盘用）
        
        Args:
            context: 实盘上下文
            tick: 实时行情数据
        
        Returns:
            SignalResult or None
        """
        return self.generate_signal(tick)
    
    def get_param_space(self) -> Dict[str, Dict[str, Any]]:
        """
        获取参数空间（供优化器使用）
        
        Returns:
            参数空间定义
        """
        return self.params
    
    def validate_params(self) -> bool:
        """
        验证参数合法性
        
        Returns:
            True if all parameters are valid
        """
        for param_name, param_config in self.params.items():
            value = getattr(self, param_name, None)
            if value is None:
                return False
            
            # 检查范围
            if 'range' in param_config:
                min_val, max_val = param_config['range']
                if not (min_val <= value <= max_val):
                    return False
        
        return True
    
    def __repr__(self) -> str:
        """字符串表示"""
        params_str = ', '.join(f'{k}={getattr(self, k)}' for k in self.params.keys())
        return f"{self.name}({params_str})"
