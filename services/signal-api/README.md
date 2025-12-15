# signal-api

信号 REST API 服务：
- 提供机会查询接口，读取 `dfp:opportunities` 流中的聚合结果。
- 支持按状态过滤、按证券代码查询单条机会。
- 预留认证/限流扩展点，默认单节点运行。

## 运行

```bash
pip install -r requirements.txt
python -m signal_api.main
```

默认监听 `0.0.0.0:8000`，健康检查 `GET /health`，机会查询 `GET /opportunities`。

## 配置

- 环境变量前缀 `SIGNAL_API_`
- `REDIS_URL`：Redis 连接串。
- `OPPORTUNITY_STREAM`：机会流名称（默认 `dfp:opportunities`）。
- `MAX_RECORDS`：最大读取记录数。

## 开发与测试

```bash
pip install -r requirements-dev.txt
pytest services/signal-api/tests
```
