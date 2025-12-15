# Architecture – opportunity-aggregator

## Purpose
- 消费策略信号 Stream，聚合去重并维护机会生命周期，输出机会 Stream/频道。

## Data Flow
1) 输入：Redis Stream `SIGNAL_STREAM`（默认 `dfp:strategy_signals`），使用 Consumer Group（默认 `opportunity-aggregator`）。
2) 解析：字段 `payload` JSON → `StrategySignal`（来自 `data_contracts`）。
3) 状态机：`OpportunityManager`（内存）按 symbol 聚合：
   - 新建：`NEW` → `ACTIVE`（首次信号）→ `TRACKING`（>1 信号）
   - 信心/强度取最大；notes 记录策略触发。
   - 超时 `TRACKING_EXPIRATION_SECONDS`（默认 600s）后自动 `CLOSED` 并输出。
4) 输出：
   - Redis Stream `OPPORTUNITY_STREAM`（默认 `dfp:opportunities`），字段 `payload` = Opportunity JSON
   - 可选 Redis pubsub `OPPORTUNITY_CHANNEL`（默认 `dfp:opportunities:ws`），消息形如：
     ```json
     {"type": "opportunity", "payload": { ...opportunity... }}
     ```

## Runtime
- Entry: `main.py` → `OpportunityAggregatorService.start()`
- Redis client: asyncio (`redis.asyncio`)
- Loop：XREADGROUP 批量消费 → 逐条处理 → ACK → 周期性 cleanup 并发布 CLOSED 机会
- Stream trim：`MAX_STREAM_LENGTH` + `APPROXIMATE_TRIM`（可选）

## Config (env prefix `OPPORTUNITY_AGG_`)
- `REDIS_URL` (default `redis://localhost:6379/0`)
- `SIGNAL_STREAM` / `OPPORTUNITY_STREAM`
- `OPPORTUNITY_CHANNEL` (pubsub, nullable)
- `CONSUMER_GROUP` / `CONSUMER_NAME`
- `READ_COUNT` (default 200) / `BLOCK_MS` (default 1000)
- `MAX_STREAM_LENGTH` (optional), `APPROXIMATE_TRIM` (default True)
- `TRACKING_EXPIRATION_SECONDS` (default 600)

## Contracts
- Input: `StrategySignal` (data_contracts)
- Output: `Opportunity` with state (`NEW/ACTIVE/TRACKING/CLOSED`), confidence/strength/notes/signals[]

## Notes
- In-memory state; restarts lose in-memory aggregation (but new signals will recreate).
- Ensure consumer group exists (`mkstream=True`, ignores BUSYGROUP).

