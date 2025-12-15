"""Risk guard service implementation."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict

import redis.asyncio as aioredis

from .config import RiskGuardSettings
from .models import Opportunity
from .rules import evaluate_risks

logger = logging.getLogger(__name__)


class RiskGuardService:
    def __init__(self, settings: RiskGuardSettings, redis_client: aioredis.Redis) -> None:
        self.settings = settings
        self.redis = redis_client
        self._shutdown = asyncio.Event()

    async def start(self) -> None:
        logger.info("Risk guard listening on stream %s", self.settings.opportunity_stream)
        last_id = "$"
        while not self._shutdown.is_set():
            try:
                response = await self.redis.xread({self.settings.opportunity_stream: last_id}, block=1000, count=50)
                if not response:
                    continue

                for _stream, entries in response:
                    for message_id, payload in entries:
                        data = payload.get("payload")
                        if not data:
                            continue
                        try:
                            opportunity = Opportunity.model_validate(json.loads(data))
                        except Exception:
                            continue
                        alerts = evaluate_risks(
                            opportunity,
                            volatility_threshold=self.settings.volatility_threshold,
                            drawdown_threshold=self.settings.drawdown_threshold,
                        )
                        for alert in alerts:
                            await self._publish_alert(alert)
                    last_id = entries[-1][0]
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.exception("Risk guard error: %s", exc)
                await asyncio.sleep(1)

    async def stop(self) -> None:
        self._shutdown.set()

    async def _publish_alert(self, alert) -> None:  # noqa: ANN001
        message = json.dumps({
            "type": "risk_alert",
            "payload": alert.model_dump()
        })
        await self.redis.publish(self.settings.risk_channel, message)


async def build_redis_client(settings: RiskGuardSettings) -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
