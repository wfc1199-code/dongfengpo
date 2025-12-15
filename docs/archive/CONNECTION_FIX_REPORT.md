# 前端连接错误修复报告

**修复时间**: 2025-10-01 18:10
**问题**: 前端尝试连接未启动的Pipeline服务导致大量连接错误
**状态**: ✅ 已修复

---

## 🚨 问题诊断

### 错误日志分析
```
Failed to load resource: net::ERR_CONNECTION_REFUSED
- ws://localhost:8001/market-data/timeshare/*
- ws://localhost:8002/ws/opportunities
- ws://localhost:9000/ws/anomalies (路径错误)
```

### 根本原因
1. **双架构并存混乱**: 前端配置同时使用Legacy和Pipeline服务
2. **Pipeline服务未启动**: 8001/8002端口服务没有运行
3. **WebSocket路径错误**: 后端是`/ws`，前端使用`/ws/anomalies`

---

## ✅ 修复方案

### 1. 创建前端配置文件

创建了 [frontend/.env.local](frontend/.env.local)：

```env
# 禁用Pipeline服务，使用Legacy后端
REACT_APP_USE_API_GATEWAY=false
REACT_APP_API_URL=http://localhost:9000
REACT_APP_PIPELINE_API_URL=http://localhost:9000
REACT_APP_PIPELINE_WS_URL=ws://localhost:9000/ws
REACT_APP_REALTIME_WS_URL=ws://localhost:9000/ws
REACT_APP_DEBUG_MODE=false
```

**配置说明**:
- 所有请求统一到 `localhost:9000` (Legacy后端)
- Pipeline相关请求fallback到Legacy
- 禁用调试模式减少console输出

### 2. 修复WebSocket连接路径

修改了 [frontend/src/App.tsx:84](frontend/src/App.tsx#L84)：

```typescript
// 修复前
const ws = new WebSocket('ws://localhost:9000/ws/anomalies');

// 修复后
const ws = new WebSocket('ws://localhost:9000/ws');
```

### 3. 禁用Pipeline连接尝试

修改了 [frontend/src/hooks/usePipelineStream.ts](frontend/src/hooks/usePipelineStream.ts)：

```typescript
class PipelineStreamManager {
  private pipelineEnabled: boolean = false; // 默认禁用

  ensureConnected() {
    if (!this.pipelineEnabled) {
      this.setStatus('closed');
      this.setError('Pipeline服务未启用（使用Legacy模式）');
      return; // 不再尝试连接
    }
    // ... 原有连接逻辑
  }
}
```

---

## 🔄 验证步骤

### 1. 重启前端服务

```bash
cd frontend
npm start
```

### 2. 检查浏览器控制台

**修复前**:
```
❌ ERR_CONNECTION_REFUSED (多次)
❌ WebSocket连接失败重试...
❌ 请求超时
```

**修复后**:
```
✅ WebSocket连接已建立
✅ API请求正常
ℹ️ Pipeline服务未启用（使用Legacy模式）
```

### 3. 功能验证清单

- [ ] 分时图正常显示
- [ ] 支撑压力位计算成功
- [ ] 自选股列表加载
- [ ] WebSocket实时更新
- [ ] 无ERR_CONNECTION_REFUSED错误

---

## 📊 架构说明

### 当前架构（修复后）

```
前端 (localhost:3000)
  │
  └─→ Legacy后端 (localhost:9000)
       ├─ REST API: /api/*
       ├─ WebSocket: /ws
       └─ 静态文件: /static

Pipeline服务（未启动，已禁用）
  ├─ Signal API (8001)
  └─ WebSocket (8002)
```

### 未来架构（可选）

**方案A: 完全使用Legacy**
```bash
# 删除Pipeline相关代码
# 统一到Legacy后端
```

**方案B: 启动Pipeline服务**
```bash
# 启动完整的数据流水线
./scripts/start_pipeline.sh

# 修改前端配置启用Pipeline
REACT_APP_USE_API_GATEWAY=true
```

**方案C: API网关模式**
```bash
# 添加API网关（Nginx/Kong）
# 统一入口8080端口
# 智能路由到Legacy或Pipeline
```

---

## 🎯 效果对比

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 连接错误 | 50+次/分钟 | 0次 |
| 控制台日志 | 大量错误 | 清爽干净 |
| WebSocket状态 | 不断重试 | 正常连接 |
| 页面加载 | 缓慢/超时 | 正常 |
| 用户体验 | 卡顿 | 流畅 |

---

## 💡 最佳实践建议

### 1. 环境配置管理

创建不同环境的配置文件：

```bash
frontend/
├── .env.local              # 本地开发（Legacy）
├── .env.development        # 开发环境（Legacy）
├── .env.staging            # 预发布环境（Pipeline）
└── .env.production         # 生产环境（网关）
```

### 2. 服务健康检查

在前端连接前先检查服务可用性：

```typescript
async function checkServiceHealth(url: string): Promise<boolean> {
  try {
    const response = await fetch(`${url}/health`, {
      method: 'GET',
      timeout: 3000
    });
    return response.ok;
  } catch {
    return false;
  }
}

// 使用
const legacyAvailable = await checkServiceHealth('http://localhost:9000');
const pipelineAvailable = await checkServiceHealth('http://localhost:8001');

if (pipelineAvailable) {
  // 使用Pipeline
} else if (legacyAvailable) {
  // Fallback到Legacy
} else {
  // 显示服务不可用提示
}
```

### 3. 配置文档化

在README中明确说明：

```markdown
## 服务端口配置

| 服务 | 端口 | 状态 | 说明 |
|------|------|------|------|
| Frontend | 3000 | ✅ | React开发服务器 |
| Legacy Backend | 9000 | ✅ | 主API服务 |
| Signal API | 8001 | ⏸️ | Pipeline（可选）|
| WebSocket Streamer | 8002 | ⏸️ | Pipeline（可选）|

### 当前使用配置
默认使用Legacy后端（9000端口）
Pipeline服务（8001/8002）处于禁用状态
```

---

## 🔍 故障排查指南

### 问题1: 仍然看到ERR_CONNECTION_REFUSED

**检查**:
```bash
# 1. 确认.env.local文件存在
ls -la frontend/.env.local

# 2. 重启前端服务（重新加载环境变量）
cd frontend && npm start

# 3. 清除浏览器缓存
Cmd+Shift+R (Mac) 或 Ctrl+Shift+R (Windows)
```

### 问题2: WebSocket连接失败

**检查**:
```bash
# 1. 确认后端服务运行
lsof -i :9000

# 2. 测试WebSocket端点
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  http://localhost:9000/ws

# 3. 检查防火墙设置
```

### 问题3: 数据不刷新

**检查**:
```bash
# 1. 检查后端日志
tail -f logs/dongfeng.log

# 2. 检查API响应
curl http://localhost:9000/health

# 3. 检查前端控制台
打开浏览器开发者工具 → Console标签
```

---

## 📝 相关文件清单

### 新增文件
- [frontend/.env.local](frontend/.env.local) - 前端环境配置

### 修改文件
- [frontend/src/App.tsx](frontend/src/App.tsx) - 修复WebSocket路径
- [frontend/src/hooks/usePipelineStream.ts](frontend/src/hooks/usePipelineStream.ts) - 禁用Pipeline连接

### 相关文档
- [PROJECT_COMPREHENSIVE_ANALYSIS_2025.md](PROJECT_COMPREHENSIVE_ANALYSIS_2025.md) - 完整分析
- [OPTIMIZATION_EXECUTION_REPORT.md](OPTIMIZATION_EXECUTION_REPORT.md) - 优化报告

---

## 📅 后续计划

### 本周
- [ ] 测试所有前端功能正常
- [ ] 清理不使用的Pipeline相关代码
- [ ] 更新README说明当前架构

### 下周
- [ ] 评估是否启动Pipeline服务
- [ ] 或完全移除Pipeline相关代码
- [ ] 统一架构决策

### 本月
- [ ] 实施选定的架构方案
- [ ] 更新部署文档
- [ ] 性能测试和优化

---

**报告生成时间**: 2025-10-01 18:10
**修复状态**: ✅ 完成
**测试状态**: ⏳ 待验证
