# Architecture – strategy-engine

## Purpose
- Subscribe to feature snapshots (Redis pubsub channel) and emit strategy signals to Redis Stream.
- Default strategy: `RapidRiseStrategy` (price change + volume gate), unless strategies configured.

## Runtime
- Entry: `main.py` → `StrategyEngineService.start()`
- Subscribes channel: `settings.feature_channel`
- Emits stream: `settings.signal_stream` (XADD, optional maxlen/approximate trim)
- Redis client: asyncio (`redis.asyncio`)

## Strategies
- Default fallback: rapid rise (`strategy_engine.strategies.rapid_rise.RapidRiseStrategy`)
  - Params: `min_change` (default 2.0%), `min_volume` (default 50,000)
  - Triggers when change_percent >= min_change and volume_sum >= min_volume
  - Outputs `StrategySignal` with confidence/strength/reasons
- Pluggable via `settings.strategies` (module/class/parameters). Also ships YAML adapters under `strategies/*`.

## Data Contracts
- Input: `FeatureSnapshot` (from `libs/data_contracts`)
- Output: `StrategySignal` (from `libs/data_contracts`)

## Flow
1) Receive Redis pubsub payload (JSON dict or list) → validate as FeatureSnapshot(s)
2) For each snapshot, evaluate all loaded strategies
3) Collect StrategySignal(s); emit to Redis Stream `signal_stream`

## Key Config (StrategyEngineSettings)
- `redis_url`
- `feature_channel` (subscribe)
- `signal_stream` (XADD)
- `max_stream_length`, `approximate_trim`
- `strategies` (optional array of StrategyConfig)

## Notes
- Graceful shutdown via SIGINT/SIGTERM.
- Logs per snapshot and per strategy evaluation.

