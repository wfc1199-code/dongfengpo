"""
策略模块 - 量化交易策略的基类和具体实现

所有策略必须继承BaseStrategy基类，确保回测和实盘使用相同的接口。
"""

from .base import BaseStrategy

__all__ = ["BaseStrategy"]
