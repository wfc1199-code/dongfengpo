# Frontend Data Flow – Additional Components

## MarketAnomalyPanel
- API: `marketScannerAPI.getAnomalies(params)` → `/api/anomaly/detect?...`
- Scan trigger: `marketScannerAPI.getScanSummary()` (start/summary) then fetch anomalies.
- Filters: type (surge/plunge/volume/limit), severity (S/A/B/C), frontend filter for limit_up/down.
- Refresh: auto (default 30s) + manual scan; stats/time shown.
- Notes: uses gateway URL; consider centralizing base URL and error handling.

## MarketAnomalyScanner
- API: hardcoded `http://localhost:8080/api/market-anomaly/scan` and `.../ai-prediction`.
- Controls: anomaly_type, limit, auto-refresh (10s), manual scan + AI预测.
- Notes: should switch to config base URL; add loading/error states, retry/backoff if needed.

## RealtimeLimitUpPredictor
- API: `GET /api/limit-up/realtime-predictions` (legacy base via config).
- Refresh: auto (default 30s) + manual; tabs per segment.
- Notes: REST-only; could be extended with WS for push if backend supports.

## SmartOpportunityFeed
- Aggregates multiple REST calls (hardcoded gateway):
  - `/api/market-scanner/top-gainers?limit=20`
  - `/api/limit-up/predictions?limit=50`
  - `/api/anomaly/detect?scan_all=true`
- Merges into local opportunities list (scored, sorted), refresh every 30s.
- Notes: no WS; duplicated data vs OpportunityFeed; hardcoded URLs → unify config; add error handling.

## PriceAlertOverlay
- No API/WS; local analysis on timeshare data prop.
- Detects 5min/1min surge/plunge and volume anomalies; raises local alerts.
- Notes: purely client-side; ensure timeshare data granularity & volume fields are provided.

## RealtimeMonitor (legacy WS)
- Hook: `useWebSocket` with `LEGACY_WS_URL`; subscribes/unsubscribes codes; expects `{type:"data_update", data:{code: payload}}`.
- Notes: consider migrating to upgraded WS client (heartbeat/backoff) or unify with pipeline streamer if backend supports same schema.

## Recommendations
- Unify API base (avoid hardcoded `http://localhost:8080`), route via gateway config.
- Prefer upgraded WS client (heartbeat/backoff) for realtime consumers; migrate RealtimeMonitor/useWebSocket to shared client.
- Consider feeding SmartOpportunityFeed from pipeline/opportunity stream to avoid triple REST fetch and duplication.

## Other components with hardcoded legacy URLs (to normalize)
- Limit-up trackers: `TimeLayeredLimitUpTracker` (`/api/limit-up/predictions`), `TodayLimitUpTracker` (`/api/limit-up-tracker/today`).
- Smart selection: `SmartSelectionPool` (`/api/smart-selection/strategies`, `/api/smart-selection/selected-stocks`), `SmartSelectorPanel` (`/api/smart-selector/top-picks`, `/api/smart-selector/realtime-anomaly`).
- ManagementDashboard/StockList/FavoriteStocks: config/favorites/system monitoring paths; should use `backend.service` helpers.
- VersionManager: `/api/versions/*`.
- MarketBehaviorPanel: `/api/stocks/{code}/behavior/analysis`.
- ContinuousBoardHistoryTable: `/api/eastmoney/continuous-board-history`.
- TransactionAnalysisPanel: `/api/transactions/{stockCode}/details?...`.
- StockChart: support-resistance calc uses `getLegacyApiUrl` (already), but fetch segments elsewhere—review.

## Pipeline REST base
- `pipeline.service.ts` uses `PIPELINE_API_BASE_URL` for opportunity list/get; aligns with pipeline backend.

