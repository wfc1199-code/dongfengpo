# Service Health & Metrics (Quick Notes)

- API Gateway: `/health` added; Prometheus counters/histograms registered if `prometheus_client` available; endpoints typically exposed via FastAPI default routes (check deployment for `/metrics`). CORS enabled for localhost:3000/3001.
- Signal Streamer: Added `/health` (liveness). Still relies on Redis pubsub; websocket `/ws/opportunities`. For deeper checks, consider Redis ping/channel subscription metrics.
- Strategy Engine: No explicit health route; logs subscribe to `feature_channel`, emits to `signal_stream`. Add `/health` or Redis ping if deploying.
- Opportunity Aggregator: No HTTP health; uses Redis XREADGROUP on `dfp:strategy_signals`, emits `dfp:opportunities` and optional pubsub channel. Could expose metrics (processed/replicated) similar to stream-buffer.
- Stream Buffer: Metrics available in-memory (`service.metrics()`), not exposed; add HTTP/metrics endpoint if required. Pipelines log start/stop and last error.
- Collector Gateway: No HTTP health; adapters log failures. Consider adding /health and per-adapter status/throughput metrics.
- Frontend: rely on app host health (e.g., Vite/production server) and availability of gateway/streamer endpoints.

Recommended next steps:
- Expose `/health` + `/metrics` (Prometheus) per service where missing.
- Add simple Redis ping and stream lag stats for pipeline/aggregator/stream-buffer.
- Gateway: ensure `/metrics` wired in deployment; add `/health` if not present.

