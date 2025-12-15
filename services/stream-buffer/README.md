# stream-buffer

流数据缓冲与分发服务：
- 监听 Redis Stream 并将数据复制到多个目标 Stream，形成多 Topic 输出。
- 支持按配置限制源/目标 Stream 长度，避免无限堆积。
- 聚合基础运行指标，可供外部监控系统采集。

## 配置

- 默认环境变量前缀：`BUFFER_`
- `REDIS_URL`：Redis 连接串，默认 `redis://localhost:6379/0`
- `PIPELINES`：可以通过 JSON/YAML 环境变量或 `.env` 定义，例如：

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

未配置目标时服务将仅监听源 Stream。

## 运行

```bash
pip install -r requirements.txt
python -m stream_buffer.main
```

## 开发与测试

```bash
pip install -r requirements-dev.txt
pytest services/stream-buffer/tests
```
