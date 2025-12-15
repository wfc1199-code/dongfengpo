"""Entry point for the data cleaner service."""

from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import AsyncExitStack

from data_cleaner.config import CleanerSettings, get_settings
from data_cleaner.service import DataCleanerService, build_redis_client


async def main() -> None:
    settings: CleanerSettings = get_settings()
    logging.basicConfig(level=settings.log_level)

    async with AsyncExitStack() as stack:
        redis_client = await build_redis_client(settings)
        stack.push_async_callback(redis_client.close)

        service = DataCleanerService(settings=settings, redis_client=redis_client)
        task = asyncio.create_task(service.start())
        stack.push_async_callback(_cancel_task, task)

        stop_event = asyncio.Event()

        def _signal_handler() -> None:
            stop_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _signal_handler)
            except NotImplementedError:
                pass

        await stop_event.wait()
        await service.stop()


async def _cancel_task(task: asyncio.Task[None]) -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
