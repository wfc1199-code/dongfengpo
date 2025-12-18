"""
Shared Module - 策略、指标、模型的共享代码库

这个模块包含回测系统和实盘系统共享的核心组件，确保策略代码100%一致。

Modules:
    - strategies: 量化策略
    - indicators: 技术指标
    - models: 数据模型
"""

__version__ = "1.0.0"
__author__ = "东风破开发团队"

from . import strategies
from . import indicators
from . import models

__all__ = ["strategies", "indicators", "models"]
