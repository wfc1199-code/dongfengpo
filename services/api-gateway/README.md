# API Gateway - 统一网关服务

## 功能

- **统一路由**: 管理Legacy和微服务的路由
- **负载均衡**: 支持多实例负载均衡（待实现）
- **监控**: Prometheus指标导出
- **健康检查**: 监控后端服务状态
- **超时控制**: 不同服务不同超时配置

## 启动

```bash
cd services/api-gateway
pip install -r requirements.txt
python main.py
```

服务运行在 `http://localhost:8080`

## 路由规则

| 路径前缀 | 目标服务 | 端口 |
|---------|---------|------|
| `/api/stocks/*` | legacy | 9000 |
| `/api/anomaly/*` | legacy | 9000 |
| `/api/v2/signals/*` | signal-api | 8001 |
| `/api/v2/strategies/*` | strategy-engine | 8003 |
| `/api/v2/backtest/*` | backtest-service | 8004 |

## 端点

- `GET /gateway/health` - 网关和后端服务健康检查
- `GET /gateway/routes` - 列出所有路由规则
- `GET /metrics` - Prometheus监控指标

## 监控指标

- `gateway_requests_total` - 请求总数（按方法、端点、状态码）
- `gateway_request_latency_seconds` - 请求延迟（按端点）

## 配置

修改 `SERVICES` 字典来添加新服务或更改路由规则。

## 下一步

- [ ] 添加服务发现（Consul集成）
- [ ] 实现负载均衡算法
- [ ] 添加认证和限流
- [ ] 实现熔断器模式