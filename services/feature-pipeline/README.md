# feature-pipeline

特征计算服务：
- 消费 `dfp:clean_ticks`，计算量价、涨幅、成交额等滚动特征。
- 支持多窗口配置（默认 5 秒），可通过环境变量扩展。
- 将特征快照发布到 Redis 发布频道 `dfp:features`。

## 配置

- 环境变量前缀：`FEATURE_PIPELINE_`
- `REDIS_URL`：Redis 连接串。
- `INPUT_STREAM`：消费源 Stream（默认 `dfp:clean_ticks`）。
- `PUBLISH_CHANNEL`：特征输出频道（默认 `dfp:features`）。
- `WINDOWS`：可通过 JSON 定义，示例：

```json
[
  {"name": "5s", "window_size": 5, "window_unit": "seconds"},
  {"name": "1m", "window_size": 1, "window_unit": "minutes"}
]
```

## 运行

```bash
pip install -r requirements.txt
python -m feature_pipeline.main
```

## 开发与测试

```bash
pip install -r requirements-dev.txt
pytest services/feature-pipeline/tests
```
