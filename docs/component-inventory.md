# Component Inventory

## Frontend (React/Vite)
- UI: Ant Design 5 components
- State: zustand stores (src/store)
- Charts: echarts via echarts-for-react
- API clients: axios-based helpers (src/api)
- Directories: `src/components`, `src/pages`, `src/services` (api), `src/hooks`, `src/utils`, `src/adapters`, `src/config`, `src/styles`, `src/types`
- Pages/Components: detailed listing pending

## Root HTML Tools (legacy/aux)
- trading_opportunity_hub.html (SPA with websocket + filters + modal)
- market_scanner.html, visual_comparison.html, debug_* etc. (utility/legacy)

## Backend (Python services)
- FastAPI routers per service (detailed API in `api-contracts-signal-api.md`; other services pending deep scan)
- Shared libs: strategy-sdk (strategy helpers), data_contracts (schemas/JSON)

## Other Services (high level)
- signal-streamer: Redis pubsub → WebSocket broadcast (`/ws/opportunities`)
- opportunity-aggregator: consume `dfp:strategy_signals`, manage lifecycle, emit `dfp:opportunities`
- stream-buffer: replicate/trim Redis Streams per pipeline config
- collector-gateway: fetch market data from sources (Tencent/Eastmoney/Tushare), publish to Stream

_Detailed per-component listing to be generated with deeper scan._

