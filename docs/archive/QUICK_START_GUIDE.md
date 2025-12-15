# 东风破系统 - 快速启动指南

## 系统概述

东风破是一个**股票分析与交易信号生成系统**,采用**微服务架构**,通过事件驱动的数据处理管道实时分析市场异动和涨停潜力。

---

## 前置要求

### 必需软件
- **Python**: 3.12+
- **Redis**: 7.0+
- **Node.js**: 18+ (前端)
- **npm**: 9+

### Python依赖
```bash
pip install fastapi uvicorn redis asyncio aioredis pydantic
```

### 可选依赖 (数据源)
```bash
pip install akshare  # AkShare数据源
pip install tushare  # Tushare数据源 (需要token)
```

---

## 快速启动 (5分钟)

### 1. 启动Redis
```bash
redis-server
```

### 2. 启动数据管道服务

**方式一: 手动启动 (推荐用于开发)**
```bash
# 终端1: 数据采集
cd services/collector-gateway && python main.py

# 终端2: 数据清洗
cd services/data-cleaner && python main.py

# 终端3: 特征生成
cd services/feature-pipeline && python main.py

# 终端4: 策略引擎
cd services/strategy-engine && python main.py

# 终端5: Signal API
cd services/signal-api && python main.py
```

**方式二: 后台启动 (推荐用于生产)**
```bash
# 使用提供的脚本
bash scripts/start_all_services.sh
```

### 3. 验证服务状态

```bash
# 检查Redis数据流
redis-cli XLEN dfp:raw_ticks
redis-cli XLEN dfp:clean_ticks
redis-cli XLEN dfp:strategy_signals

# 检查API健康
curl http://localhost:8000/health
```

### 4. 访问API

```bash
# 获取最新信号
curl http://localhost:8000/signals?limit=10

# 获取统计信息
curl http://localhost:8000/signals/stats

# 按策略过滤
curl http://localhost:8000/signals?strategy=anomaly_detection

# 按股票查询
curl http://localhost:8000/signals/sh600000
```

### 5. 启动前端 (可选)

```bash
cd frontend
npm install
npm start
```

访问: `http://localhost:3000`

---

## 服务端口一览

| 服务 | 端口 | 说明 |
|------|------|------|
| Frontend | 3000 | React前端 |
| Signal API | 8000 | 新版信号API |
| API Gateway | 8080 | 统一网关 |
| Legacy Backend | 9000 | 旧版API (待下线) |
| Redis | 6379 | 数据存储 |

---

## 配置说明

### 策略配置

编辑 `services/strategy-engine/strategies_config.json`:

```json
[
  {
    "name": "anomaly_detection",
    "enabled": true,
    "parameters": {
      "speed_threshold": 0.02,
      "volume_threshold": 2.0,
      "min_confidence": 0.60
    }
  },
  {
    "name": "limit_up_prediction",
    "enabled": true,
    "parameters": {
      "min_change_percent": 2.0,
      "min_probability": 0.5
    }
  }
]
```

### 数据源配置

编辑 `services/collector-gateway/config.yaml` (如果存在):

```yaml
data_sources:
  - name: tencent
    enabled: true
    poll_interval: 1.0
  - name: akshare
    enabled: false
    poll_interval: 2.0
  - name: tushare
    enabled: false
    poll_interval: 3.0
```

---

## 监控与调试

### 查看日志

```bash
# 实时查看策略引擎日志
tail -f services/strategy-engine/logs/strategy.log

# 查看API日志
tail -f services/signal-api/logs/api.log
```

### Redis数据检查

```bash
# 查看原始数据
redis-cli XREVRANGE dfp:raw_ticks + - COUNT 10

# 查看清洗后数据
redis-cli XREVRANGE dfp:clean_ticks + - COUNT 10

# 查看策略信号
redis-cli XREVRANGE dfp:strategy_signals + - COUNT 10

# 查看流长度
redis-cli XINFO STREAM dfp:strategy_signals
```

### 性能监控

```bash
# Redis性能
redis-cli INFO stats | grep instantaneous

# 进程资源使用
ps aux | grep python

# 网络连接
netstat -an | grep 8000
```

---

## 常见问题

### Q1: 策略引擎没有生成信号?

**检查清单**:
1. ✅ Redis是否运行: `redis-cli ping`
2. ✅ 数据采集是否正常: `redis-cli XLEN dfp:raw_ticks`
3. ✅ 策略是否启用: 检查`strategies_config.json`
4. ✅ 日志是否有错误: 查看策略引擎日志

### Q2: API返回空数组?

**原因**: Redis Stream中还没有数据

**解决**:
```bash
# 等待数据采集
sleep 10

# 再次查询
curl http://localhost:8000/signals?limit=5
```

### Q3: 数据采集失败?

**检查**:
- Tencent数据源: 网络连接是否正常
- AkShare数据源: 是否安装`akshare`包
- Tushare数据源: 是否设置`TUSHARE_TOKEN`环境变量

### Q4: 端口冲突?

**解决**:
```bash
# 查找占用端口的进程
lsof -i :8000

# 杀死进程
kill -9 <PID>
```

---

## 停止服务

### 手动停止
```bash
# 按Ctrl+C停止各终端的服务
```

### 批量停止
```bash
# 停止所有Python进程
pkill -f "python main.py"

# 或使用脚本
bash scripts/stop_all_services.sh
```

---

## 开发指南

### 添加新策略

1. 创建策略目录:
```bash
mkdir -p services/strategy-engine/strategies/my_strategy
```

2. 实现策略类:
```python
# strategy.py
class MyStrategy:
    def analyze_sync(self, snapshot):
        # 你的策略逻辑
        return [signal]
```

3. 创建适配器:
```python
# adapter.py
class MyStrategyAdapter(Strategy):
    def evaluate(self, feature):
        return self.strategy.analyze_sync(...)
```

4. 注册策略:
```json
// strategies_config.json
{
  "name": "my_strategy",
  "module": "strategies.my_strategy",
  "class_name": "MyStrategyAdapter",
  "enabled": true
}
```

### 添加新数据源

1. 实现适配器:
```python
# services/collector-gateway/adapters/my_adapter.py
class MyAdapter(DataSourceAdapter):
    async def stream(self, symbols):
        # 实现数据流
        yield tick
```

2. 注册到bootstrap:
```python
# bootstrap.py
elif name == "my_source":
    adapter = MyAdapter(...)
```

---

## API文档

### 完整API文档

访问 `http://localhost:8000/docs` 查看Swagger UI

### 核心端点

**列表查询**:
```
GET /signals?limit=50&strategy=anomaly_detection&symbol=sh600000&min_confidence=0.8
```

**统计信息**:
```
GET /signals/stats
```

**按股票查询**:
```
GET /signals/{symbol}
```

---

## 性能调优

### 策略并行度

编辑 `strategies_config.json`, 启用更多策略:
```json
[
  {"name": "anomaly_detection", "enabled": true},
  {"name": "limit_up_prediction", "enabled": true},
  {"name": "custom_strategy_1", "enabled": true},
  {"name": "custom_strategy_2", "enabled": true}
]
```

### Redis配置优化

编辑 `redis.conf`:
```
# 最大内存
maxmemory 2gb

# 淘汰策略
maxmemory-policy allkeys-lru

# AOF持久化
appendonly yes
appendfsync everysec
```

### 数据采集频率

调整 `poll_interval` 参数 (秒):
- 高频: 0.5-1.0s (更多数据,更高负载)
- 中频: 1.0-2.0s (平衡)
- 低频: 3.0-5.0s (更少数据,更低负载)

---

## 生产部署建议

### 1. 使用进程管理器

**Supervisor**:
```ini
[program:strategy-engine]
command=python main.py
directory=/path/to/services/strategy-engine
autostart=true
autorestart=true
```

**systemd**:
```ini
[Unit]
Description=Strategy Engine

[Service]
ExecStart=/usr/bin/python3 main.py
WorkingDirectory=/path/to/services/strategy-engine
Restart=always

[Install]
WantedBy=multi-user.target
```

### 2. 配置反向代理

**Nginx**:
```nginx
upstream signal_api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    location /api/signals {
        proxy_pass http://signal_api;
    }
}
```

### 3. 设置监控

- **Prometheus**: metrics导出
- **Grafana**: 可视化dashboard
- **Alertmanager**: 告警通知

### 4. 日志管理

- **ELK**: Elasticsearch + Logstash + Kibana
- **Loki**: Grafana Loki
- **日志轮转**: logrotate

---

## 相关文档

- [完整迁移报告](MIGRATION_COMPLETE_REPORT.md)
- [架构设计文档](docs/ARCHITECTURE.md)
- [API参考](http://localhost:8000/docs)
- [策略开发指南](docs/STRATEGY_DEVELOPMENT.md)

---

## 技术支持

- **问题反馈**: GitHub Issues
- **文档**: [docs/](docs/)
- **示例**: [examples/](examples/)

---

*最后更新*: 2025-10-01
*版本*: v2.0
*状态*: ✅ Production Ready
