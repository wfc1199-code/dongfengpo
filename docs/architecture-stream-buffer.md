# Architecture – stream-buffer

## Purpose
- 监听源 Redis Stream，将数据复制到一个或多个目标 Stream，支持裁剪以防堆积。

## Data Flow
1) 配置 PIPELINES（JSON/YAML 或环境变量）声明源/目标：
   ```json
   [
     {
       "name": "raw-backup",
       "source_stream": "dfp:raw_ticks",
       "targets": [
         {"name": "dfp:raw_ticks:backup", "max_length": 500000}
       ],
       "trim_source_to": 200000
     }
   ]
   ```
2) 服务订阅源 Stream，逐条 XREAD → 写入各 target；可对源和目标应用 `max_length`（approximate trim）。

## Runtime
- Entry: `python -m stream_buffer.main`
- Redis: `redis://...`（`BUFFER_REDIS_URL`）
- 并发：按配置管线循环复制，支持多 pipeline。

## Config (env prefix `BUFFER_`)
- `REDIS_URL` (default `redis://localhost:6379/0`)
- `PIPELINES`：JSON 定义源/目标/trim 参数

## Notes
- 无状态复制器；依赖 Redis Streams 持久化。
- 未配置目标时仅监听源（无输出）。

