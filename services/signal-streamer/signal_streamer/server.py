"""WebSocket server that broadcasts opportunity updates."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Set

import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from .config import SignalStreamerSettings

logger = logging.getLogger(__name__)


class OpportunityStreamer:
    def __init__(self, settings: SignalStreamerSettings, redis_client: aioredis.Redis) -> None:
        self.settings = settings
        self.redis = redis_client
        self.clients: Set[WebSocket] = set()
        self._shutdown = asyncio.Event()

    async def start(self) -> None:
        channels = [self.settings.channel_name]
        if self.settings.risk_channel:
            channels.append(self.settings.risk_channel)

        pubsub = self.redis.pubsub()
        await pubsub.subscribe(*channels)
        logger.info("Subscribed to channels %s", ", ".join(channels))

        try:
            while not self._shutdown.is_set():
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if not message:
                    continue

                data = message.get("data")
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                channel = message.get("channel")
                if isinstance(channel, bytes):
                    channel = channel.decode("utf-8")

                payload = None
                try:
                    payload = json.loads(data)
                except Exception:
                    logger.debug("Received non-JSON message on %s: %s", channel, data)
                    payload = {"type": "raw", "payload": data}

                if channel == self.settings.risk_channel and payload.get("type") != "risk_alert":
                    payload = {"type": "risk_alert", "payload": payload}
                elif channel == self.settings.channel_name and payload.get("type") != "opportunity":
                    payload = {"type": "opportunity", "payload": payload}

                await self.broadcast(payload)
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()

    async def stop(self) -> None:
        self._shutdown.set()

    async def register(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.clients.add(websocket)
        logger.info("Client connected: %s (total=%d)", websocket.client, len(self.clients))

    async def unregister(self, websocket: WebSocket) -> None:
        self.clients.discard(websocket)
        logger.info("Client disconnected: %s (total=%d)", websocket.client, len(self.clients))

    async def broadcast(self, message) -> None:  # noqa: ANN001
        if not self.clients:
            return
        payload = json.dumps(message)
        living_clients: Set[WebSocket] = set()
        for client in self.clients:
            try:
                await client.send_text(payload)
                living_clients.add(client)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to send to client %s: %s", client.client, exc)
        self.clients = living_clients


def create_app(streamer: OpportunityStreamer) -> FastAPI:
    app = FastAPI(title="Opportunity Signal Stream", version="1.0.0")

    @app.get("/health")
    async def health() -> Dict[str, str]:
        # Basic liveness; for deeper checks, add Redis ping or channel state as needed.
        return {"status": "ok"}

    @app.websocket("/ws/opportunities")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await streamer.register(websocket)
        try:
            while True:
                await websocket.receive_text()  # keep connection alive / support ping
        except WebSocketDisconnect:
            await streamer.unregister(websocket)

    @app.on_event("startup")
    async def startup() -> None:
        asyncio.create_task(streamer.start())

    @app.on_event("shutdown")
    async def shutdown() -> None:
        await streamer.stop()

    return app
