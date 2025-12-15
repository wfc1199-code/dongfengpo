"""
策略注册表
"""

import importlib.util
from pathlib import Path
from typing import Dict, List, Optional
import logging
import yaml

from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """策略注册表"""

    def __init__(self):
        self.strategies: Dict[str, BaseStrategy] = {}
        self.metadata: Dict[str, Dict] = {}

    async def register(self, strategy: BaseStrategy, config: Optional[Dict] = None):
        """
        注册策略实例

        Args:
            strategy: 策略实例
            config: 策略配置
        """
        if not isinstance(strategy, BaseStrategy):
            raise TypeError("Strategy must inherit from BaseStrategy")

        name = strategy.name
        if name in self.strategies:
            logger.warning(f"Strategy '{name}' already registered, overwriting")

        # 初始化策略
        init_config = config or strategy.default_parameters
        await strategy.initialize(init_config)
        strategy.is_initialized = True

        # 注册
        self.strategies[name] = strategy
        self.metadata[name] = strategy.get_metadata()

        logger.info(f"Registered strategy: {name} v{strategy.version}")

    async def register_from_path(self, strategy_path: str):
        """
        从路径注册策略

        Args:
            strategy_path: 策略目录路径，需包含strategy.yaml和strategy.py
        """
        path = Path(strategy_path)

        # 加载配置
        config_file = path / "strategy.yaml"
        if not config_file.exists():
            raise FileNotFoundError(f"strategy.yaml not found in {strategy_path}")

        with open(config_file) as f:
            config = yaml.safe_load(f)

        # 动态导入策略模块
        strategy_file = path / "strategy.py"
        if not strategy_file.exists():
            raise FileNotFoundError(f"strategy.py not found in {strategy_path}")

        spec = importlib.util.spec_from_file_location(
            f"strategies.{config['name']}",
            strategy_file
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # 查找BaseStrategy子类
        strategy_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and
                issubclass(attr, BaseStrategy) and
                attr != BaseStrategy):
                strategy_class = attr
                break

        if not strategy_class:
            raise ValueError(f"No BaseStrategy subclass found in {strategy_file}")

        # 实例化并注册
        strategy = strategy_class()
        await self.register(strategy, config.get('parameters', {}))

    async def discover_strategies(self, search_paths: List[str]):
        """
        自动发现并注册策略

        Args:
            search_paths: 搜索路径列表
        """
        for search_path in search_paths:
            path = Path(search_path)
            if not path.exists():
                logger.warning(f"Strategy path not found: {search_path}")
                continue

            for strategy_dir in path.iterdir():
                if strategy_dir.is_dir() and (strategy_dir / "strategy.yaml").exists():
                    try:
                        await self.register_from_path(str(strategy_dir))
                    except Exception as e:
                        logger.error(f"Failed to register strategy from {strategy_dir}: {e}")

    def get(self, name: str) -> Optional[BaseStrategy]:
        """获取策略实例"""
        return self.strategies.get(name)

    def get_all(self) -> Dict[str, BaseStrategy]:
        """获取所有策略"""
        return self.strategies

    def get_metadata(self, name: str) -> Optional[Dict]:
        """获取策略元数据"""
        return self.metadata.get(name)

    def list_strategies(self) -> List[str]:
        """列出所有已注册策略名称"""
        return list(self.strategies.keys())