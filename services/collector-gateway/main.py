"""Entry point for the collector gateway service."""

from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import AsyncExitStack
from typing import List

from collector_gateway.bootstrap import build_adapters
from collector_gateway.config import CollectorSettings, get_settings
from collector_gateway.service import CollectorService, build_redis_client


async def main(symbols: List[str] | None = None) -> None:
    settings: CollectorSettings = get_settings()
    logging.basicConfig(level=settings.log_level)

    if not symbols:
        # TODO: load from config or discovery service
        symbols = ["000001", "600000"]

    async with AsyncExitStack() as stack:
        redis_client = await build_redis_client(settings)
        stack.push_async_callback(redis_client.close)

        adapters = build_adapters(settings)
        service = CollectorService(settings=settings, redis_client=redis_client, adapters=adapters)

        await service.start(symbols)

        stop_event = asyncio.Event()

        def _set_stop() -> None:
            stop_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _set_stop)
            except NotImplementedError:
                # Windows compatibility
                pass

        try:
            await stop_event.wait()
        finally:
            await service.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
