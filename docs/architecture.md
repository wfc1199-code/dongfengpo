# Architecture (High-Level)

## System Topology
- API Gateway (`services/api-gateway`): unified ingress (FastAPI)
- Signal API (`services/signal-api`): core business APIs (stocks, anomaly, signals, opportunities, limit-up, config)
- Strategy Engine (`services/strategy-engine`): strategy execution and signal generation
- Signal Streamer (`services/signal-streamer`): websocket push for opportunities/signals
- Supporting services: collector-gateway, stream-buffer, opportunity-aggregator, risk-guard, feature-pipeline, data-cleaner, data-lake-writer, backtest-service, unified-gateway
- Frontend (`frontend/`): React + Vite SPA
- Shared libs: `libs/strategy-sdk`, `libs/data_contracts`

## Data & Flow (conceptual)
1) Upstream data ingestion (collector/stream-buffer/feature-pipeline/data-cleaner/data-lake-writer)
2) Strategy Engine generates signals → stored/retrieved by Signal API
3) Signal API exposes read-model endpoints; Signal Streamer pushes realtime opportunities
4) Frontend (or HTML tools) consumes API Gateway/Signal Streamer

## Tech Stack
- Backend: Python FastAPI, per-service requirements; AkShare used in limit-up endpoints
- Frontend: React 19 + Vite + AntD + zustand + echarts
- Orchestration: docker-compose

## Known Endpoints (see details)
- Signal API routes summarized in `api-contracts-signal-api.md`

## Next Docs To Generate
- Service-level deep dives (per service)
- Data models / schemas
- Integration architecture (cross-service contracts)
- Dev/deploy guides per part


