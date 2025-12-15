# 分时数据处理中心服务目录

该目录用于存放重构后各独立服务/模块的源代码与配置。当前规划的服务如下：

- `collector-gateway`：多源行情采集服务。
- `stream-buffer`：流式缓冲与分发层。
- `data-cleaner`：数据清洗与标准化处理。
- `data-lake-writer`：历史数据落地与归档。
- `feature-pipeline`：特征计算与指标聚合。
- `strategy-engine`：策略执行与信号产出。
- `opportunity-aggregator`：多策略信号聚合与状态管理。
- `signal-api`：信号 REST API 服务。
- `signal-streamer`：WebSocket/SSE 推送服务。
- `backtest-service`：历史回测与报表生成。
- `risk-guard`：风险监控与提示服务。

> 各子服务目录内将包含源码、配置、部署脚本及测试用例。随着实施推进逐步补充。
