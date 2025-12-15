# opportunity-aggregator

机会聚合服务：
- 从 `dfp:strategy_signals` 读取策略输出，进行去重、状态管理。
- 自动维护机会生命周期（NEW/ACTIVE/TRACKING/CLOSED）。
- 将聚合后的机会写入 `dfp:opportunities` Stream。

## 配置

- 环境变量前缀 `OPPORTUNITY_AGG_`
- `REDIS_URL`：Redis 连接串。
- `SIGNAL_STREAM`：策略信号输入 (默认 `dfp:strategy_signals`)
- `OPPORTUNITY_STREAM`：机会结果输出 (默认 `dfp:opportunities`)
- `TRACKING_EXPIRATION_SECONDS`：超时自动关闭机会的秒数。

## 运行

```bash
pip install -r requirements.txt
python -m opportunity_aggregator.main
```

## 开发与测试

```bash
pip install -r requirements-dev.txt
pytest services/opportunity-aggregator/tests
```
