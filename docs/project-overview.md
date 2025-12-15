# Project Overview

## Summary
- Architecture: Multi-part (frontend + Python microservices + shared libs)
- Frontend: React 19 + Vite + Ant Design 5 + zustand + echarts
- Backend services: FastAPI-based microservices (api-gateway, signal-api, strategy-engine, signal-streamer, etc.)
- Shared libs: `strategy-sdk`, `data_contracts`
- Orchestration: `docker-compose.yml`

## Key Services (sample)
- api-gateway: entry FastAPI gateway
- signal-api: stocks/signals/opportunities/anomaly/limit-up/config APIs
- strategy-engine: strategy execution
- signal-streamer: websocket streaming
- others: collector-gateway, stream-buffer, opportunity-aggregator, risk-guard, feature-pipeline, data-cleaner, data-lake-writer, backtest-service, unified-gateway

## Frontend
- Vite + React + AntD; state via zustand; axios/http helpers; charting via echarts.

## Existing Docs
- `docs/` (multiple guides), `services/README.md`, `frontend/README.md`

## Pending Detailed Docs
- Architecture per service/part
- Data models, component inventory, dev/deploy guides, integration architecture


