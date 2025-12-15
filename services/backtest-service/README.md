# backtest-service

回测与评估服务：
- 提供 REST 接口触发策略回测，支持模拟数据兜底。
- 返回收益、回撤、胜率等核心指标及交易序列。
- 后续可接入真实数据湖、参数网格扫描与任务编排。

## 运行

```bash
pip install -r requirements.txt
python -m backtest_service.main
```

默认监听 `0.0.0.0:8200`，健康检查 `GET /health`，回测接口 `POST /backtests`。

## 请求示例

```json
{
  "symbol": "sh600000",
  "start_date": "2024-01-01",
  "end_date": "2024-03-01",
  "strategy": {"name": "rapid-rise", "config": {"threshold": 2.0}}
}
```

## 开发

```bash
pip install -r requirements-dev.txt
python -m compileall services/backtest-service
```
