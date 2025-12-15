# 东风破系统 - 快速启动指南 🚀

**版本**: 2.0 (微服务架构)
**最后更新**: 2025-10-01

---

## 📋 前置要求

### 必需软件

- **Python**: 3.12.3+
- **Redis**: Latest
- **Node.js**: 16+ (可选，用于前端开发)

### 安装依赖

```bash
# 后端依赖
cd backend
pip install -r requirements.txt

# 前端依赖 (可选)
cd frontend
npm install
```

---

## ⚡ 5分钟快速启动

### 1. 启动 Redis

```bash
# macOS
brew services start redis

# Linux
sudo systemctl start redis

# 验证
redis-cli ping
# 应返回: PONG
```

### 2. 启动所有微服务

```bash
# 一键启动所有服务
bash scripts/manage_services.sh start

# 预期输出:
# [SUCCESS] Redis is running
# [SUCCESS] collector-gateway started (PID: xxxxx)
# [SUCCESS] data-cleaner started (PID: xxxxx)
# [SUCCESS] feature-pipeline started (PID: xxxxx)
# [SUCCESS] strategy-engine started (PID: xxxxx)
# [SUCCESS] signal-api started (PID: xxxxx)
# [SUCCESS] All services started
```

### 3. 验证服务状态

```bash
# 查看服务状态
bash scripts/manage_services.sh status

# 测试 Signal API
curl http://localhost:8000/health
# 应返回: {"status":"ok"}
```

### 4. 测试数据

```bash
# 获取信号列表
curl http://localhost:8000/signals?limit=10

# 获取统计信息
curl http://localhost:8000/signals/stats
```

---

## 🎛️ 灰度发布管理

### 查看当前灰度状态

```bash
bash scripts/grayscale_rollout.sh status
```

### 调整灰度比例

```bash
# 设置为50%
bash scripts/grayscale_rollout.sh set 50

# 或使用阶段快捷方式
bash scripts/grayscale_rollout.sh stage 3  # 50%
```

### 灰度阶段

| 命令 | 灰度比例 | 说明 |
|------|---------|------|
| `stage 0` | 0% | 全部使用Legacy API |
| `stage 1` | 10% | 初始灰度 |
| `stage 2` | 30% | 扩大灰度 |
| `stage 3` | 50% | 过半流量 |
| `stage 4` | 80% | 接近全量 |
| `stage 5` | 100% | 全量Signal API |

### 回滚操作

```bash
# 回滚到上一阶段
bash scripts/grayscale_rollout.sh rollback

# 紧急回滚到0%
bash scripts/grayscale_rollout.sh emergency
```

---

## 📊 性能监控

### 运行性能测试

```bash
# 60秒性能监控
bash scripts/monitor_performance.sh 60

# 快速30秒测试
bash scripts/monitor_performance.sh 30
```

### 输出指标

- 成功率
- 平均响应时间
- P50/P95延迟
- 错误率
- 性能标准验证

---

## 🛠️ 服务管理

### 启动服务

```bash
# 启动所有服务
bash scripts/manage_services.sh start

# 启动单个服务
cd services/signal-api && python main.py
```

### 查看状态

```bash
bash scripts/manage_services.sh status
```

### 停止服务

```bash
# 停止所有服务
bash scripts/manage_services.sh stop

# 停止单个服务
pkill -f "signal-api"
```

### 查看日志

```bash
# 查看特定服务日志
bash scripts/manage_services.sh logs signal-api

# 实时查看日志
tail -f services/signal-api/logs/app.log
```

---

## 🌐 API 使用

### Signal API 端点

**基础URL**: `http://localhost:8000`

#### 健康检查

```bash
curl http://localhost:8000/health
```

**响应**:
```json
{
  "status": "ok"
}
```

#### 获取信号列表

```bash
# 基础查询
curl http://localhost:8000/signals?limit=10

# 按策略过滤
curl "http://localhost:8000/signals?strategy=anomaly_detection&limit=20"

# 按股票代码过滤
curl "http://localhost:8000/signals?symbol=sh600000&limit=10"

# 按置信度过滤
curl "http://localhost:8000/signals?min_confidence=0.8&limit=10"
```

**响应示例**:
```json
[
  {
    "strategy": "anomaly_detection",
    "symbol": "sh600000",
    "signal_type": "volume_surge",
    "confidence": 1.0,
    "strength_score": 0.95,
    "reasons": ["成交量异常", "价格突破"],
    "triggered_at": "2025-10-01T10:00:00Z",
    "window": "5m",
    "metadata": {
      "stock_name": "浦发银行",
      "volume_ratio": 2.5
    }
  }
]
```

#### 获取统计信息

```bash
curl http://localhost:8000/signals/stats
```

**响应**:
```json
{
  "total_signals": 500,
  "average_confidence": 1.0,
  "strategies": {
    "anomaly_detection": 500
  },
  "signal_types": {
    "volume_surge": 500
  },
  "top_symbols": {
    "sh600000": 250,
    "sz000001": 250
  }
}
```

#### 获取特定股票信号

```bash
curl http://localhost:8000/signals/sh600000?limit=10
```

#### API 文档

访问交互式API文档:
```bash
open http://localhost:8000/docs
```

---

## 🔧 前端集成

### 使用 Unified Service

```typescript
import { unifiedAnomalyService } from './services/unified.service';

// 获取异动数据 (自动路由到Signal API或Legacy API)
const result = await unifiedAnomalyService.getAnomalies(true);

console.log(`数据来源: ${result.source}`);
console.log(`响应时间: ${result.responseTime}ms`);
console.log(`异动数量: ${result.anomalies.length}`);
```

### Feature Flags 配置

```typescript
import { getFeatureFlags, setRolloutPercentage } from './config/featureFlags';

// 获取当前配置
const flags = getFeatureFlags();

// 设置灰度比例
setRolloutPercentage('anomalyDetection', 50);
```

### 浏览器调试工具

```javascript
// Feature Flags
window.featureFlags.get()
window.featureFlags.setRollout('anomalyDetection', 50)
window.featureFlags.debug()

// Unified Service
window.unifiedService.getMetrics()
await window.unifiedService.testSignalApi()

// Performance Monitor
window.performanceMonitor.getReport()
window.performanceMonitor.getHealth()
```

---

## 🐛 故障排查

### 问题1: Redis连接失败

**症状**:
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**解决方案**:
```bash
# 检查Redis是否运行
redis-cli ping

# 如未运行，启动Redis
brew services start redis  # macOS
sudo systemctl start redis # Linux
```

### 问题2: 端口被占用

**症状**:
```
OSError: [Errno 48] Address already in use
```

**解决方案**:
```bash
# 查看占用端口的进程
lsof -ti:8000

# 杀死进程
kill -9 $(lsof -ti:8000)

# 或使用管理脚本
bash scripts/manage_services.sh stop
```

### 问题3: 服务启动失败

**症状**:
```
ModuleNotFoundError: No module named 'xxx'
```

**解决方案**:
```bash
# 重新安装依赖
pip install -r backend/requirements.txt

# 验证Python版本
python --version  # 应为 3.12.3+
```

### 问题4: 无信号数据

**症状**:
```json
{
  "total_signals": 0
}
```

**解决方案**:
```bash
# 检查所有服务是否运行
bash scripts/manage_services.sh status

# 检查Redis streams
redis-cli
> XLEN dfp:raw_ticks
> XLEN dfp:strategy_signals

# 重启服务
bash scripts/manage_services.sh stop
bash scripts/manage_services.sh start
```

---

## 📈 性能优化建议

### 1. Redis配置优化

```bash
# 编辑 redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### 2. 服务并发配置

```python
# services/signal-api/main.py
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=4,  # 增加工作进程
        log_level="info"
    )
```

### 3. 数据库连接池

```python
# 配置连接池大小
REDIS_POOL_SIZE = 10
```

---

## 🔒 安全建议

### 1. API访问控制

```python
# 添加API Key验证
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=403)
```

### 2. CORS配置

```python
# main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 仅允许前端域名
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### 3. 速率限制

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.get("/signals")
@limiter.limit("100/minute")
async def get_signals():
    pass
```

---

## 📚 常用命令速查

### 服务管理

```bash
# 启动
bash scripts/manage_services.sh start

# 停止
bash scripts/manage_services.sh stop

# 状态
bash scripts/manage_services.sh status

# 重启
bash scripts/manage_services.sh stop && bash scripts/manage_services.sh start
```

### 灰度管理

```bash
# 状态
bash scripts/grayscale_rollout.sh status

# 设置
bash scripts/grayscale_rollout.sh set 50

# 阶段
bash scripts/grayscale_rollout.sh stage 3

# 回滚
bash scripts/grayscale_rollout.sh rollback

# 测试
bash scripts/grayscale_rollout.sh test
```

### 监控

```bash
# 性能测试
bash scripts/monitor_performance.sh 60

# 查看日志
tail -f services/signal-api/logs/app.log

# 查看进程
ps aux | grep "python.*main.py"
```

### Redis

```bash
# 连接
redis-cli

# 查看streams
XLEN dfp:raw_ticks
XLEN dfp:clean_ticks
XLEN dfp:strategy_signals

# 清空数据
FLUSHALL
```

---

## 🎯 下一步

### 开发环境

1. 启动前端开发服务器
```bash
cd frontend
npm run dev
```

2. 访问: http://localhost:3000

### 生产部署

1. 配置环境变量
2. 启动所有服务
3. 配置反向代理 (Nginx)
4. 设置监控告警

### 扩展功能

1. 添加新策略插件
2. 集成更多数据源
3. 实现策略回测
4. 添加机器学习模型

---

## 📞 获取帮助

### 文档

- [项目总结](PROJECT_FINAL_SUMMARY.md)
- [Phase 3完成报告](docs/PHASE3_FINAL_COMPLETE.md)
- [API文档](http://localhost:8000/docs)

### 故障排查

1. 检查服务状态
2. 查看日志文件
3. 验证配置文件
4. 参考故障排查章节

---

**祝使用愉快！🎉**

_最后更新: 2025-10-01_
_版本: 2.0_
