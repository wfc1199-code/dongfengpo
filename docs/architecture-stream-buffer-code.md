# Architecture – stream-buffer (Code-level)

## Entry / Lifecycle
- `main.py` → load `BufferSettings` → build Redis → `StreamBufferService.start()`.
- Graceful shutdown via SIGINT/SIGTERM, tasks cancelled with AsyncExitStack.

## Config (`stream_buffer/config.py`, env prefix `BUFFER_`)
- `pipelines[]`: name, source_stream, start_from (`$`), block_ms (default 1000), batch_size (default 200), trim_source_to (optional), targets[].
- targets: name, max_length (optional), approximate (default True).
- `redis_url`, `log_level`.

## Core Logic (`service.py`)
- Per pipeline task `_run_pipeline`:
  - XREAD stream from `start_from`, count=batch_size, block=block_ms.
  - For each batch: `_handle_entries` → `_replicate_to_targets`.
  - Update `last_id`; optional `xtrim` source to `trim_source_to` (approximate).
  - On error: log, set metrics.last_error, sleep 1 then continue.
- Replication:
  - XADD to each target with optional maxlen/approximate per target config.
- Metrics: per pipeline (last_id, processed, replicated, last_processed_at, last_error).
- Shutdown: cancels all pipeline tasks.

## Notes / Behavior
- No consumer groups; simple XREAD tail from `$` (or configured start_from).
- No dedupe/transform; copies payload fields as-is.
- Backpressure: controlled via batch_size/block_ms; trimming source optional, target trim per target.
- If pipelines unset → waits idle.

## Potential Improvements
- Support consumer group (XREADGROUP) for at-least-once with pending handling.
- Retry/backoff per pipeline; alerting on repeated failures.
- Metrics endpoint/export; health checks.

