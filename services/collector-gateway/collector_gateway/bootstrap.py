"""Bootstrap helpers for building collector components."""

from __future__ import annotations

import logging
from typing import Iterable, List, Optional

import redis.asyncio as aioredis

from .adapters.base import DataSourceAdapter
from .adapters.tencent import TencentAdapter, TencentAdapterConfig
from .adapters.akshare_adapter import AkShareAdapter
from .adapters.tushare_adapter import TushareAdapter
from .adapters.cached_adapter import CachedAdapter
from .config import CollectorSettings, DataSourceConfig

logger = logging.getLogger(__name__)


def build_adapters(settings: CollectorSettings, redis_client: Optional[aioredis.Redis] = None) -> List[DataSourceAdapter]:
    """Instantiate adapters based on configuration."""

    adapters: List[DataSourceAdapter] = []

    for ds_config in settings.data_sources:
        adapter = _create_adapter(ds_config, redis_client)
        if adapter:
            adapters.append(adapter)

    if adapters:
        return adapters

    logger.info("No data source configuration supplied; using default Tencent adapter")
    return [TencentAdapter()]


def _create_adapter(config: DataSourceConfig, redis_client: Optional[aioredis.Redis] = None) -> Optional[DataSourceAdapter]:
    if not config.enabled:
        logger.info("Skipping disabled data source: %s", config.name)
        return None

    name = config.name.lower()
    adapter = None

    if name == "tencent":
        ds_config = TencentAdapterConfig(
            base_url=str(config.base_url) if config.base_url else TencentAdapterConfig.base_url,
            poll_interval=config.poll_interval_seconds,
            request_timeout=config.timeout_seconds,
            max_symbols_per_request=config.max_batch_size,
        )
        adapter = TencentAdapter(config=ds_config)

    elif name == "akshare":
        try:
            adapter = AkShareAdapter(name="akshare", poll_interval=config.poll_interval_seconds)
        except ImportError as e:
            logger.error(f"Failed to create AkShare adapter: {e}")
            return None

    elif name == "tushare":
        try:
            adapter = TushareAdapter(name="tushare", poll_interval=config.poll_interval_seconds)
        except (ImportError, ValueError) as e:
            logger.error(f"Failed to create Tushare adapter: {e}")
            return None

    else:
        logger.warning("Unsupported data source adapter requested: %s", config.name)
        return None

    # Wrap with cache if enabled
    if config.enable_cache and adapter and redis_client:
        logger.info(f"Enabling Redis cache for {name} adapter")
        adapter = CachedAdapter(wrapped_adapter=adapter, redis_client=redis_client, cache_ttl_seconds=config.cache_ttl_seconds)

    return adapter


__all__ = ["build_adapters"]
