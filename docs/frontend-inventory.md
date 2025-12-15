# Frontend Inventory (React + Vite)

## Stack
- React 19, Vite, Ant Design 5, zustand, axios, echarts (echarts-for-react).

## Directories (src/)
- `pages`: `AdvancedMonitorPage.tsx`, `TimeShareDemo.tsx` (+ css)
- `components`: examples include `MarketScanner.tsx`, `MarketAnomalyScanner.tsx`, `OpportunityFeed.tsx`, `AnomalyNotification.tsx`, `MarketBehaviorPanel.tsx`, `PriceAlertOverlay.tsx`, `TimelineTransactionPanel.tsx`, `ErrorBoundary.tsx`, plus many CSS files.
- `services` (api), `hooks`, `utils`, `adapters`, `config`, `styles`, `types`, `store` (zustand).

## Page → Component map (observed)
- `AdvancedMonitorPage`: uses `ConsolidationBreakoutMonitor`, `PeakBreakoutMonitor` (no API wiring shown in file).
- `TimeShareDemo`: uses `TimeShareChartFixed`; local state for stock code, toggles support/resistance overlay.

## Suggested next drill-down
- Map pages → components → services (API) and WS usage; verify where `MarketScanner`, `OpportunityFeed`, etc. fetch data.
- Integrate WS hook (`frontend-ws-hook-example.md`) for opportunities/risk alerts into relevant components/pages.

