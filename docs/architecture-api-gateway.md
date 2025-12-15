# Architecture – api-gateway

## Purpose
- FastAPI gateway routing to microservices; optional metrics (Prometheus), CORS, structured logging.

## Services & Routes (base_url from env overrides)
- signal-api (`DFP_SIGNAL_API_BASE_URL`, default http://localhost:9001)
- signal-streamer (`DFP_SIGNAL_STREAMER_BASE_URL`, default http://localhost:8100) — ws proxy patterns
- strategy-engine (`DFP_STRATEGY_ENGINE_BASE_URL`, default http://localhost:8003)
- backtest-service (`DFP_BACKTEST_SERVICE_BASE_URL`, default http://localhost:8200)
- Additional patterns include market data/support-resistance/config/anomaly/limit-up/opportunities etc. (wildcards matched via fnmatch; special handling for support-resistance single segment).

## Routing Logic
- `match_route` + `find_target_service` choose service based on best match (prioritize signal-api/streamer/opportunity-aggregator/risk-guard).
- Rewrites upstream path when needed; supports WebSocket proxy.
- HTTP clients created on startup (httpx AsyncClient pool); closed on shutdown.

## Observability
- Prometheus counters/histograms (graceful fallback if lib missing).
- Structured log with trace_id.

## CORS
- Allows localhost:3000/3001 with all methods/headers.

## Notes
- Timeout customization per service (e.g., signal-api 30s for slow upstream).
- Health routes patterns included in routes list.

