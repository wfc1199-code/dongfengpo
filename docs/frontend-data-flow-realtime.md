# Frontend Data Flow – Realtime Monitor

## Components & Hooks
- `RealtimeMonitor.tsx`
  - Hook: `useWebSocket` (now uses `SIGNAL_STREAMER_WS_URL` instead of legacy)
  - Message handler: expects `{ type: "data_update", data: { [code]: stockData } }`
  - Actions: subscribe/unsubscribe stocks; ping/refresh; add/remove codes; table view with metrics.
- `useWebSocket` (upgraded):
  - Heartbeat ping (default 15s), exponential backoff + jitter reconnect, reconnect attempts configurable; timers cleaned.
  - Methods: `subscribe(stocks)`, `unsubscribe(stocks)`, `ping()`, `sendMessage`, `connect/ disconnect`.

## Message Contract
- Current component仍期待旧格式：`{ type: "data_update", data: { code: payload } }`
- 如果 signal-streamer 实际推送机会流而非行情，需要在服务端或前端适配：
  - 方案A：在 signal-streamer 增加行情 channel/格式匹配 data_update。
  - 方案B：在前端转换 signal-streamer 消息为 data_update，再写入表。

## Open Questions
- signal-streamer 是否提供行情数据？若仅有 opportunities/risk_alert，需要调整 RealtimeMonitor 的解析逻辑。
- 若要兼容 legacy feed，保留 fallback URL 或增加模式切换。
# Frontend Data Flow – Realtime Monitor

## Components & Hooks
- `RealtimeMonitor.tsx`
  - Hook: `useWebSocket` (LEGACY_WS_URL)
  - Message handler: expects `{ type: "data_update", data: { [code]: stockData } }`
  - Actions: subscribe/unsubscribe stocks; ping/refresh; add/remove codes; table view with metrics.
- `useWebSocket`:
  - Options: reconnect (default true), interval 3s, attempts 5.
  - Parses JSON per message; no heartbeat; simple retry; no jitter/backoff.
  - Methods exposed: `subscribe(stocks)`, `unsubscribe(stocks)`, `ping()`, `sendMessage`, `connect/ disconnect`.

## Message Contract (legacy WS)
- `{ type: "data_update", data: { code: {price fields...} } }`
- RealtimeMonitor attaches `update_time` per client.

## Gaps / Improvements
- Add heartbeat/auto-resubscribe on reconnect (current onOpen subscribes defaultCodes, but updates to subscribedCodes rely on state).
- Add backoff jitter & higher attempts; detect stale connection.
- Align with new signal-streamer WS if intending to migrate (current uses LEGACY_WS_URL).

## Suggested Next Steps
- If using signal-streamer, create a new hook reusing upgraded WS base (heartbeat/backoff) and map to opportunity/risk streams.
- If retaining legacy feed, document server expectations for subscribe/unsubscribe/ping and ensure backend supports them.

