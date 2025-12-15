# Frontend Data Flow – Opportunities (API + WS)

## Components & Hooks
- `OpportunityFeed` → uses `useOpportunityFeed`
- `useOpportunityFeed`:
  - API: `opportunityAPI.list({ limit, state })` (pipeline.service) – initial load/refresh
  - WS: `usePipelineStream` handler → message `{type: "opportunity", payload}` → `deserializeOpportunity` → prepend list (limit-bound, state filter)
  - Errors: separates fetch vs stream errors
- `usePipelineStream`:
  - WS URL: `PIPELINE_WS_URL` (config)
  - Features: reconnect (max 3, 30s delay), delayed shutdown when no subscribers, status/error listeners; pipelineEnabled flag (disabled → error “Pipeline服务未启用（使用Legacy模式)”)
  - No heartbeat/ping; no buffer limit; minimal error handling on onerror.

## Message Contract
- WS message expected: `{ type: "opportunity", payload: <opportunity> }`
- payload deserialized via `deserializeOpportunity` (pipeline.service)
- State filter enforced client-side when adding to list

## Gaps / Improvements
- Add heartbeat/ping and server-side expectation if supported.
- Add backoff jitter and higher max reconnect attempts for production.
- Add max list length (already limit-bound) and de-dup by id (done).
- Handle `risk_alert` or other types gracefully (currently ignored).

## Suggested Integration
- Reuse `frontend-ws-hook-example` or upgrade `usePipelineStream` with:
  - Heartbeat interval & server ping
  - Reconnect with jitter/backoff and infinite attempts (configurable)
  - Error surfacing per consumer; optional pause/resume
  - Optional local buffer cap beyond limit to prevent churn


