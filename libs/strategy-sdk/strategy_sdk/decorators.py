"""
策略装饰器
"""

from functools import wraps
from typing import Dict, Any


def strategy(name: str, version: str, author: str, description: str = ""):
    """
    策略类装饰器

    用法:
        @strategy(name="my_strategy", version="1.0", author="john")
        class MyStrategy(BaseStrategy):
            pass
    """
    def decorator(cls):
        cls.name = name
        cls.version = version
        cls.author = author
        cls.description = description
        return cls
    return decorator


def on_market_open(func):
    """开盘事件装饰器"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        print(f"[{self.name}] Market opened")
        return await func(self, *args, **kwargs)
    return wrapper


def on_market_close(func):
    """收盘事件装饰器"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        print(f"[{self.name}] Market closed")
        return await func(self, *args, **kwargs)
    return wrapper


def require_features(*features):
    """
    特征依赖装饰器

    用法:
        @require_features('price', 'volume', 'ma5')
        async def analyze(self, features):
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, features: Dict, *args, **kwargs):
            # 检查必要特征
            missing = [f for f in features if f not in features]
            if missing:
                raise ValueError(f"Missing required features: {missing}")
            return await func(self, features, *args, **kwargs)
        return wrapper
    return decorator