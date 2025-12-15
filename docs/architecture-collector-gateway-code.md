# Architecture – collector-gateway (Code-level)

## Entry / Lifecycle
- `main.py` → load `CollectorSettings` → build Redis → build adapters (bootstrap) → `CollectorService.start(symbols)`; graceful shutdown on SIGINT/SIGTERM.
- Symbols: default ["000001","600000"] if not provided (TODO in code).

## Config (`collector_gateway/config.py`, env prefix `COLLECTOR_`)
- `redis_url`, `stream_name` (default `dfp:raw_ticks`), `batch_size`, `flush_interval_seconds`.
- `data_sources[]` (DataSourceConfig): name, enabled, base_url, api_key, rate_limit_per_minute, timeout_seconds, retry_attempts, poll_interval_seconds, max_batch_size.

## Service (`collector_gateway/service.py`)
- For each adapter (built via `build_adapters`): start → async iterate `adapter.stream(symbols)` → `_write_tick`.
- `_write_tick`: wraps tick into `TickRecord` (from data_contracts), adds `ingested_at`, XADD to `stream_name` with field `payload` (JSON), no maxlen (approximate=False).
- Shutdown: cancel tasks, stop adapters.

## Adapters
- Base (`adapters/base.py`): `AdapterTick` dataclass; abstract `stream(symbols)` and `fetch_snapshot`.
- Tencent (`adapters/tencent.py`):
  - Polling loop: chunk symbols (max 200), GET `http://qt.gtimg.cn/q=...`, parse GBK text, map to AdapterTick (price/volume/turnover; bid/ask omitted), timestamp=UTC now.
  - Config: base_url, poll_interval (default 1s), request_timeout 5s, max_symbols_per_request 200.
  - Error handling: logs exception, sleeps poll_interval, continues.
- Other adapters present (akshare_adapter, tushare_adapter, cached_adapter) not analyzed here but follow base interface.

## Notes / Behavior
- No rate-limit enforcement beyond poll_interval; relies on per-adapter settings.
- No backpressure/trim on stream writes (maxlen=None).
- No dedupe/transform beyond TickRecord mapping.
- Retry strategy minimal (sleep on exception).

## Potential Improvements
- Add maxlen/approximate trim on stream writes or rely on downstream buffer (stream-buffer).
- Add per-adapter backoff/jitter and explicit rate limiting.
- Externalize symbol list (config/service).
- Health/metrics endpoint for adapter status, error counts, throughput.

