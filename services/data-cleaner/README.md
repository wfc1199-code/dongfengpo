# data-cleaner

流式 Tick 数据清洗与标准化服务：
- 消费 `dfp:raw_ticks` Stream，执行基础修正与质量标记。
- 将结果写入 `dfp:clean_ticks` 供特征流水线与策略引擎使用。
- 维护 Redis 消费者组状态，后续可挂载监控指标。

## 配置

通过环境变量（前缀 `CLEANER_`）覆盖默认值：

- `REDIS_URL`：Redis 连接串，默认 `redis://localhost:6379/0`。
- `INPUT_STREAM` / `OUTPUT_STREAM`：输入与输出 Stream 名称。
- `CONSUMER_GROUP` / `CONSUMER_NAME`：消费者组与消费者标识。
- `READ_COUNT`：每批读取的最大条数，默认 200。
- `BLOCK_MS`：阻塞读取毫秒数，默认 1000。
- `MAX_OUTPUT_LEN`：可选，限制输出 Stream 最大长度。

## 运行

```bash
pip install -r requirements.txt
python -m data_cleaner.main
```

## 开发与测试

```bash
pip install -r requirements-dev.txt
pytest services/data-cleaner/tests
```
