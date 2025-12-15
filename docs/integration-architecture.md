# Integration Architecture (Initial)

## High-Level Flow
- Data ingestion/services (collector-gateway, stream-buffer, feature-pipeline, data-cleaner, data-lake-writer) feed cleaned data.
- Strategy Engine consumes data → produces signals.
- Signal API exposes read-model APIs for signals/opportunities; Limit-up uses AkShare for market data; Config uses JSON storage.
- Signal Streamer publishes realtime opportunities via websocket.
- Frontend/HTML tools consume API Gateway/Signal API and websocket.

## Interfaces
- REST via API Gateway/Signal API (see `api-contracts-signal-api.md`)
- WebSocket via signal-streamer (port 8002; details pending deeper scan)
- Redis pubsub: `feature_channel` → Strategy Engine input
- Redis stream: `signal_stream` (XADD) → downstream consumers (e.g., Signal API / streamer)
- Redis streams/pipelines:
  - collector-gateway → raw tick stream (configurable)
  - stream-buffer → replicate/trim streams to targets
  - opportunity-aggregator → consume `dfp:strategy_signals`, emit `dfp:opportunities`
- API Gateway proxies HTTP/WebSocket to services per route map

## Next Deep-Dive Items
- Cross-service contracts (payload schemas) between strategy-engine ↔ signal-api
- Message/buffer topics (stream-buffer/opportunity-aggregator) if any
- Auth/config propagation (none detected yet)


