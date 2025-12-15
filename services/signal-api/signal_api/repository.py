"""Repository for retrieving opportunities from Redis streams."""

from __future__ import annotations

import json
from typing import List, Optional

import redis.asyncio as aioredis

from .models import Opportunity


class OpportunityRepository:
    def __init__(self, redis_client: aioredis.Redis, stream: str, max_records: int) -> None:
        self.redis = redis_client
        self.stream = stream
        self.max_records = max_records

    async def list_opportunities(self, limit: Optional[int] = None, state: Optional[str] = None) -> List[Opportunity]:
        limit = min(limit or self.max_records, self.max_records)
        result = await self.redis.xrevrange(self.stream, count=limit)
        opportunities: List[Opportunity] = []
        for _message_id, payload in result:
            data = payload.get("payload")
            if not data:
                continue
            try:
                obj = json.loads(data)
                if state and obj.get("state") != state:
                    continue
                opportunities.append(Opportunity.model_validate(obj))
            except Exception:
                continue
        return opportunities

    async def get_opportunity(self, symbol: str) -> Optional[Opportunity]:
        # Fetch more records to increase chance of finding symbol
        result = await self.redis.xrevrange(self.stream, count=self.max_records)
        for _message_id, payload in result:
            data = payload.get("payload")
            if not data:
                continue
            try:
                obj = json.loads(data)
            except Exception:
                continue
            if obj.get("symbol") == symbol:
                return Opportunity.model_validate(obj)
        return None
