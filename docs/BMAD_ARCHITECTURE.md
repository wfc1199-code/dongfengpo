# BMAD重构架构说明

## 📋 架构概览

BMAD重构后采用**微服务架构**，替代了原来的模块化单体架构。

## 🏗️ 服务架构

### 服务列表

| 服务 | 端口 | 说明 | 健康检查 |
|------|------|------|---------|
| **API Gateway** | 8080 | 统一网关，路由所有请求 | `/gateway/health` |
| **Signal API** | 9001 | 信号API服务，处理核心业务逻辑 | `/health` |
| **Signal Streamer** | 8002 | 流式服务，WebSocket推送 | - |
| **Strategy Engine** | 8003 | 策略引擎 | - |
| **前端** | 3000 | React前端界面 | - |

### 路由规则

API Gateway根据路径将请求路由到不同的后端服务：

| 路径前缀 | 目标服务 | 端口 |
|---------|---------|------|
| `/api/stocks/*` | Signal API | 9001 |
| `/api/anomaly/*` | Signal API | 9001 |
| `/api/limit-up/*` | Signal API | 9001 |
| `/api/market-scanner/*` | Signal API | 9001 |
| `/api/v2/opportunities` | Signal API | 9001 |
| `/api/v2/signals/*` | Signal API | 9001 |
| `/ws/opportunities` | Signal Streamer | 8002 |

## 🚀 启动方式

### 方式1: 使用启动脚本（推荐）

```bash
cd /Users/wangfangchun/东风破
./scripts/start_bmad_refactored.sh
```

### 方式2: 手动启动各服务

```bash
# 1. 启动Signal API
cd services/signal-api
python -m signal_api.main

# 2. 启动Signal Streamer
cd services/signal-streamer
python -m signal_streamer.main

# 3. 启动Strategy Engine
cd services/strategy-engine
python -m strategy_engine.main

# 4. 启动API Gateway
cd services/api-gateway
python main.py

# 5. 启动前端
cd frontend
npm start
```

## 🔍 验证服务

### 健康检查

```bash
# API Gateway
curl http://localhost:8080/gateway/health

# Signal API
curl http://localhost:9001/health

# 查看路由规则
curl http://localhost:8080/gateway/routes
```

### 测试API

```bash
# 通过Gateway访问（推荐）
curl "http://localhost:8080/api/stocks/search?keyword=000001"

# 直接访问Signal API（不推荐，仅用于调试）
curl "http://localhost:9001/api/stocks/search?keyword=000001"
```

## 📝 日志位置

| 服务 | 日志文件 |
|------|---------|
| API Gateway | `logs/api-gateway.log` |
| Signal API | `logs/signal-api.log` |
| Signal Streamer | `logs/signal-streamer.log` |
| Strategy Engine | `logs/strategy-engine.log` |
| 前端 | `logs/frontend.log` |

## 🔄 与旧架构对比

### 旧架构（模块化单体）

- **入口**: `backend/main_modular.py`
- **端口**: 9000
- **架构**: 模块化单体（所有模块在同一进程）
- **路由**: 直接路由到模块

### 新架构（微服务）

- **入口**: API Gateway (`services/api-gateway/main.py`)
- **端口**: 8080 (Gateway), 9001 (Signal API), 8002 (Streamer), 8003 (Strategy)
- **架构**: 微服务（服务分离，独立部署）
- **路由**: Gateway统一路由到各微服务

## ⚠️ 注意事项

1. **所有请求应通过API Gateway** (8080)，不要直接访问后端服务
2. **前端配置**: 前端应配置API Gateway地址 (`http://localhost:8080`)
3. **CORS**: API Gateway已配置CORS，允许前端访问
4. **WebSocket**: WebSocket连接也通过Gateway (`ws://localhost:8080/ws/opportunities`)

---

**创建时间**: 2025-01-02  
**状态**: ✅ BMAD微服务架构

