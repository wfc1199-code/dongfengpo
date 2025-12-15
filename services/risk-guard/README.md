# risk-guard

风险监控与提示服务：
- 监听 `dfp:opportunities` 流，识别置信度低、动能衰减等风险信号。
- 将风险告警发布到 Redis 频道 `dfp:risk_alerts`，供前端/告警系统订阅。
- 支持通过环境变量调整阈值，后续可扩展更多规则。

## 运行

```bash
pip install -r requirements.txt
python -m risk_guard.main
```

## 配置

- 环境变量前缀 `RISK_GUARD_`
- `REDIS_URL`：Redis 连接串。
- `RISK_CHANNEL`：风险告警频道（默认 `dfp:risk_alerts`）。
- `VOLATILITY_THRESHOLD`、`DRAWDOWN_THRESHOLD`：风险阈值参数。

## 开发

```bash
pip install -r requirements-dev.txt
python -m compileall services/risk-guard
```
