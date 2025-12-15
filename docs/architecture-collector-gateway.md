# Architecture – collector-gateway

## Purpose
- 多源分时行情采集，统一适配器接口，推送原始 tick 到 Redis Stream（或 Kafka，取决于实现配置）。

## Data Flow
1) 数据源适配器（如腾讯/Eastmoney/Tushare），按配置轮询/批量抓取。
2) 写入 Stream `STREAM_NAME`（默认 `dfp:raw_ticks`）。
3) 可与 downstream（stream-buffer、feature-pipeline 等）衔接。

## Config (env prefix `COLLECTOR_`)
- `REDIS_URL` (default `redis://localhost:6379/0`)
- `STREAM_NAME` (default `dfp:raw_ticks`)
- `DATA_SOURCES` JSON 列表：
  ```json
  [
    {
      "name": "tencent",
      "base_url": "http://qt.gtimg.cn/q=",
      "poll_interval_seconds": 1.0,
      "timeout_seconds": 5.0,
      "max_batch_size": 200
    }
  ]
  ```
- 未配置时默认启用腾讯行情适配器。

## Runtime
- Entry: `python -m collector_gateway.main`
- Deps: `pip install -r requirements.txt` (dev: `requirements-dev.txt`)

## Notes
- 关注节流/重试，确保 Stream 长度由下游（如 stream-buffer）或 Redis 配置控制。

