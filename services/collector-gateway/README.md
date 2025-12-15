# collector-gateway

多源分时行情采集服务：
- 抽象统一的数据源适配器接口。
- 负责腾讯/东方财富/Tushare 等数据源的抓取、重试、节流。
- 输出原始 Tick Stream 至流式缓冲层（Redis Stream/Kafka）。
- 提供运行状态指标与健康检查接口。

## 配置说明

通过环境变量注入 `CollectorSettings`（前缀 `COLLECTOR_`）：

- `REDIS_URL`：Redis 连接串（默认 `redis://localhost:6379/0`）。
- `STREAM_NAME`：写入的 Stream 名称（默认 `dfp:raw_ticks`）。
- `DATA_SOURCES`：JSON 列表，用于声明启用的适配器。例如：

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

若未提供配置，将默认启用腾讯行情适配器。

## 开发与测试

运行时依赖：

```bash
pip install -r requirements.txt
```

开发环境可安装额外依赖：

```bash
pip install -r requirements-dev.txt
pytest services/collector-gateway/tests
```
