"""Strategy plugin loader."""

from __future__ import annotations

import importlib
import logging
from typing import Dict, List

from .config import StrategyConfig
from .strategies.base import Strategy

logger = logging.getLogger(__name__)


def load_strategies(configs: List[StrategyConfig]) -> Dict[str, Strategy]:
    strategies: Dict[str, Strategy] = {}
    for config in configs:
        if not config.enabled:
            logger.info("Strategy %s disabled", config.name)
            continue

        try:
            # Check if this is an SDK strategy (by convention, SDK strategies use "sdk:" prefix)
            if config.module.startswith("sdk:"):
                strategy = _load_sdk_strategy(config)
            else:
                # Load traditional strategy-engine strategy
                module = importlib.import_module(config.module)
                strategy_cls = getattr(module, config.class_name)
                strategy: Strategy = strategy_cls(name=config.name, **config.parameters)

            strategy.on_load()
            strategies[config.name] = strategy
            logger.info("Loaded strategy %s from %s.%s", config.name, config.module, config.class_name)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to load strategy %s: %s", config.name, exc)

    return strategies


def _load_sdk_strategy(config: StrategyConfig) -> Strategy:
    """Load a strategy from the dongfengpo-strategy-sdk."""
    from .sdk_adapter import load_sdk_strategy

    # Remove "sdk:" prefix to get actual module path
    module_path = config.module[4:]
    return load_sdk_strategy(
        module=module_path,
        class_name=config.class_name,
        name=config.name,
        **config.parameters
    )


def unload_strategies(strategies: Dict[str, Strategy]) -> None:
    for strategy in strategies.values():
        try:
            strategy.on_unload()
        except Exception:  # noqa: BLE001
            logger.exception("Error while unloading strategy %s", strategy.name)
