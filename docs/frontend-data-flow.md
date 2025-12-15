# Frontend Data Flow & API/WS Mapping

## Pages
- `AdvancedMonitorPage` → Components: `ConsolidationBreakoutMonitor`, `PeakBreakoutMonitor` (data flow not shown; likely via services).
- `TimeShareDemo` → Component: `TimeShareChartFixed`; stateful stock selection + support/resistance toggle.

## Components (sample mapped)
- `MarketScanner.tsx`
  - API: `marketScannerAPI.getScan(type, limit)` → `/api/market-scanner/{type}` (signal-api via gateway)
  - Scan types: top_gainers/losers/volume/turnover/volume_surge/price_breakout/reversal_signals
  - Refresh on type change; manual refresh; optional `onStockSelect` callback.
- (Others identified, pending deep scan):
  - `OpportunityFeed`, `SmartOpportunityFeed`
  - `MarketAnomalyScanner`, `MarketAnomalyPanel`
  - `MarketBehaviorPanel`
  - `PriceAlertOverlay`
  - `RealtimeMonitor`, `RealtimeLimitUpPredictor`
  - `TimelineTransactionPanel`, `TransactionAnalysisPanel`
  - `HotSectors`, `FavoriteStocks`, etc.

## Services (API wrappers)
- `backend.service.ts`
  - stock search: `/api/stocks/search`
  - limit-up: `/api/limit-up/predictions`, `/api/market-scanner/limit-up`
  - market scanner: `/api/market-scanner/{endpoint}` (type underscores→hyphen)
  - anomaly detect: `/api/anomaly/detect`
  - config/monitoring: `/api/config`, `/api/system/monitoring-stocks`
  - market data: realtime/kline/transactions, support-resistance, etc.

## WebSocket
- Signal Streamer: `/ws/opportunities` (message `{type: "opportunity"|"risk_alert", payload: ...}`)
- Hook sample: `frontend-ws-hook-example.md` (basic). Consider production upgrade (reconnect/heartbeat/buffer limit).
- For opportunities feed specifics: see `frontend-data-flow-opportunity.md`.
- For legacy realtime quotes: see `frontend-data-flow-realtime.md`.

## Suggested Next Steps
- Map remaining components to specific API/WS usage.
- Wire WS hook into opportunity/alert feeds (e.g., OpportunityFeed, SmartOpportunityFeed, alert panels).
- Centralize API base/config; add error handling/loading states per component.
- Migrate legacy WS consumers to unified WS client (with heartbeat/backoff) if backend supports signal-streamer or equivalent.

