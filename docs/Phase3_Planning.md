# Phase 3 规划：完整流水线联调

**阶段**: Phase 3 - 完整流水线联调与生产部署
**开始时间**: 2025-09-30（Phase 2 完成后）
**预计时长**: 2-3周
**目标**: 打通完整数据流水线，实现端到端信号生成与推送

---

## 🎯 Phase 3 目标

### 核心目标

1. **启动完整服务链** ✅ 部分完成
   - [x] Collector Gateway (数据采集)
   - [x] Feature Pipeline (特征计算)
   - [x] Strategy Engine (策略评估)
   - [x] Opportunity Aggregator (机会聚合)
   - [x] Signal Streamer (WebSocket推送)
   - [x] Risk Guard (风险监控)

2. **实时数据流打通**
   - [ ] 实时行情采集
   - [ ] 特征实时计算
   - [ ] 策略实时评估
   - [ ] 信号实时推送

3. **前端集成**
   - [ ] 连接API Gateway
   - [ ] WebSocket实时推送
   - [ ] 信号可视化
   - [ ] 用户交互优化

4. **性能优化**
   - [ ] 压力测试
   - [ ] 性能调优
   - [ ] 资源优化

---

## 📋 详细任务列表

### Week 1: 服务启动与联调

#### 任务 1.1: 启动Feature-Pipeline (P0)
**目标**: 实时计算市场特征

**步骤**:
```bash
# 1. 检查依赖
cd services/feature-pipeline
pip install -r requirements.txt

# 2. 配置环境变量
export REDIS_URL="redis://localhost:6379"
export FEATURE_CHANNEL="dfp:features"
export SOURCE_STREAM="dfp:clean_ticks"

# 3. 启动服务
python main.py
```

**验证**:
- [ ] 服务成功启动
- [ ] 订阅 clean_ticks 流
- [ ] 计算特征并发布
- [ ] Feature-Pipeline 健康检查通过

**预期输出**:
```
INFO: Feature-Pipeline started
INFO: Subscribed to dfp:clean_ticks
INFO: Computing features for window=300s
INFO: Published feature snapshot for XXXXXX.XX
```

#### 任务 1.2: 调试Strategy-Engine消息处理 (P0)
**目标**: 确保策略引擎正确处理特征数据

**问题分析**:
- Strategy-Engine 订阅成功但未显示处理消息日志
- 可能是日志级别或消息处理逻辑问题

**解决步骤**:
1. 添加详细日志到 service.py
2. 验证 FeatureSnapshot 字段匹配
3. 测试手动发布特征数据
4. 确认信号生成

**代码修改** (建议):
```python
# services/strategy-engine/strategy_engine/service.py
async def _handle_payload(self, payload: str) -> None:
    logger.info(f"📥 Received message: {payload[:200]}...")  # 添加
    try:
        data = json.loads(payload)
        logger.info(f"✅ Parsed data for: {data.get('symbol', 'N/A')}")  # 添加
        # ... 现有逻辑
    except Exception as e:
        logger.error(f"❌ Error processing: {e}", exc_info=True)  # 添加
```

**验证**:
- [ ] 看到"📥 Received message"日志
- [ ] 看到策略评估日志
- [ ] 信号成功发布到 Redis Stream

#### 任务 1.3: 验证完整信号流 (P0)
**目标**: 端到端数据流验证

**测试流程**:
```
1. 发布测试特征 → Redis (dfp:features)
2. Strategy-Engine 接收 → 评估策略
3. 生成信号 → Redis (dfp:signals)
4. Signal-API 查询 → 返回信号
5. API Gateway 转发 → 前端接收
```

**测试脚本**:
```bash
# 使用现有脚本
python test_realtime_signal_generation.py

# 或创建新的端到端测试
python test_phase3_e2e.py
```

**验证清单**:
- [ ] 特征发布成功
- [ ] Strategy-Engine 接收并处理
- [ ] 信号生成到 Redis Stream
- [ ] Signal-API 可以查询到信号
- [ ] API Gateway 正确转发

---

### Week 2: 扩展服务与集成

#### 任务 2.1: 启动Opportunity-Aggregator (P1)
**功能**: 聚合信号，生成交易机会

**启动**:
```bash
cd services/opportunity-aggregator
python main.py
```

**验证**:
- [ ] 订阅 dfp:signals 流
- [ ] 聚合多个信号
- [ ] 发布机会到 dfp:opportunities
- [ ] Signal-API 可以查询机会

#### 任务 2.2: 启动Signal-Streamer (P1)
**功能**: WebSocket 实时推送

**启动**:
```bash
cd services/signal-streamer
python main.py  # 默认端口 8100
```

**验证**:
- [ ] WebSocket 服务启动
- [ ] 可以建立连接
- [ ] 实时推送机会
- [ ] 前端可以接收

#### 任务 2.3: 启动Risk-Guard (P1)
**功能**: 风险监控与告警

**启动**:
```bash
cd services/risk-guard
python main.py
```

**验证**:
- [ ] 风险规则加载
- [ ] 监控信号质量
- [ ] 发布风险告警

#### 任务 2.4: 前端接入API Gateway (P0)
**目标**: 前端通过网关访问所有服务

**前端配置**:
```javascript
// frontend/src/config.js
const API_CONFIG = {
  // 新的统一网关入口
  gateway: 'http://localhost:8888',

  // API端点（通过网关）
  endpoints: {
    health: '/health',
    opportunities: '/opportunities',
    signals: '/api/v2/signals',
    backtest: '/backtests',
  },

  // WebSocket（直连）
  websocket: 'ws://localhost:8100/ws/opportunities'
}
```

**修改要点**:
1. 替换所有 API 调用为网关地址
2. 添加 WebSocket 连接
3. 实现实时数据更新
4. 错误处理优化

**验证**:
- [ ] 前端可以查询健康状态
- [ ] 机会列表正常显示
- [ ] WebSocket 实时推送工作
- [ ] 所有API调用通过网关

---

### Week 3: 优化与部署

#### 任务 3.1: 性能压力测试 (P1)
**工具**: wrk, ab, locust

**测试场景**:
```bash
# 1. API Gateway 压力测试
wrk -t4 -c100 -d30s http://localhost:8888/opportunities

# 2. WebSocket 并发测试
# 使用 ws-benchmark 或自定义脚本

# 3. 策略引擎吞吐量测试
# 发布大量特征数据，测试处理能力
```

**性能目标**:
- API Gateway: >1000 req/s
- Strategy-Engine: >100 features/s
- Signal-API: <50ms p99
- WebSocket: >500 concurrent connections

#### 任务 3.2: 监控告警系统 (P1)
**工具**: Prometheus + Grafana

**监控指标**:
- 服务健康状态
- API响应时间
- 策略执行时间
- 信号生成数量
- 错误率
- 资源使用（CPU、内存）

**告警规则**:
- 服务宕机
- 响应时间超阈值
- 错误率过高
- 资源使用异常

#### 任务 3.3: 部署自动化 (P2)
**工具**: Docker Compose / Kubernetes

**Docker化**:
```yaml
# docker-compose.yml
version: '3.8'
services:
  redis:
    image: redis:7
    ports:
      - "6379:6379"

  signal-api:
    build: ./services/signal-api
    ports:
      - "8000:8000"
    depends_on:
      - redis

  strategy-engine:
    build: ./services/strategy-engine
    depends_on:
      - redis

  # ... 其他服务
```

**部署流程**:
```bash
# 构建镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

#### 任务 3.4: 文档完善 (P1)
**文档清单**:
- [ ] Phase 3 实施报告
- [ ] 完整部署指南
- [ ] 运维手册更新
- [ ] API 文档
- [ ] 前端集成指南
- [ ] 故障排查手册

---

## 🏗️ 完整架构图（Phase 3目标）

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (React)                          │
│                  http://localhost:3000                   │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  API调用: http://localhost:8888/*              │    │
│  │  WebSocket: ws://localhost:8100/ws/opportunities│   │
│  └────────────────────────────────────────────────┘    │
└──────────────┬─────────────────────┬────────────────────┘
               │                     │
               ▼                     ▼
    ┌──────────────────┐    ┌──────────────────┐
    │  API Gateway     │    │ Signal-Streamer  │
    │    (8888)        │    │     (8100)       │
    └────────┬─────────┘    └────────┬─────────┘
             │                       │
             ├───────────┬───────────┼───────────┬────────┐
             ▼           ▼           ▼           ▼        ▼
      ┌──────────┐ ┌──────────┐ ┌────────┐ ┌─────────┐ ...
      │Signal-API│ │Backtest  │ │Legacy  │ │ 更多... │
      │  (8000)  │ │ (8200)   │ │ (9000) │ │         │
      └────┬─────┘ └──────────┘ └────────┘ └─────────┘
           │
           ▼
    ┌────────────────────────────────────────────────┐
    │              Redis (6379)                       │
    │  ┌──────────────────────────────────────────┐  │
    │  │  Channels:                                │  │
    │  │  - dfp:raw_ticks (Stream)                │  │
    │  │  - dfp:clean_ticks (Stream)              │  │
    │  │  - dfp:features (Pubsub)                 │  │
    │  │  - dfp:signals (Stream)                  │  │
    │  │  - dfp:opportunities (Stream)            │  │
    │  │  - dfp:opportunities:ws (Pubsub)         │  │
    │  │  - dfp:risks (Stream)                    │  │
    │  └──────────────────────────────────────────┘  │
    └─────┬───────────┬───────────┬─────────┬────────┘
          │           │           │         │
          ▼           ▼           ▼         ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
    │Collector │ │Feature   │ │Strategy  │ │Opp.Agg   │
    │Gateway   │ │Pipeline  │ │Engine    │ │          │
    └──────────┘ └──────────┘ └──────────┘ └──────────┘
          ▲
          │
    [实时行情数据源]
```

---

## 📊 Phase 3 里程碑

### Milestone 1: 服务启动 (Week 1 Day 1-3)
- [x] Signal-API ✅
- [x] Strategy-Engine ✅
- [x] Backtest-Service ✅
- [x] API Gateway ✅
- [ ] Feature-Pipeline
- [ ] Opportunity-Aggregator
- [ ] Signal-Streamer
- [ ] Risk-Guard

### Milestone 2: 数据流打通 (Week 1 Day 4-7)
- [ ] 端到端数据流验证
- [ ] 实时信号生成
- [ ] WebSocket推送
- [ ] 前端接收显示

### Milestone 3: 功能完善 (Week 2)
- [ ] 添加更多策略
- [ ] 机会聚合优化
- [ ] 风险监控上线
- [ ] 前端功能完善

### Milestone 4: 生产部署 (Week 3)
- [ ] 性能优化
- [ ] 监控告警
- [ ] Docker部署
- [ ] 文档完善

---

## 🎯 成功标准

### 功能标准
- [ ] 所有核心服务运行正常
- [ ] 完整数据流端到端打通
- [ ] 前端可以实时接收信号
- [ ] WebSocket推送稳定
- [ ] 所有API响应正常

### 性能标准
- [ ] API Gateway: >1000 req/s
- [ ] P99延迟 < 100ms
- [ ] 策略评估 < 50ms
- [ ] WebSocket: >500 连接
- [ ] 无内存泄漏

### 质量标准
- [ ] 测试覆盖率 > 80%
- [ ] 无严重bug
- [ ] 文档完整
- [ ] 代码审查通过

---

## 🚨 风险识别

### 技术风险

1. **实时数据源** (High)
   - 风险: 没有真实行情数据源
   - 缓解: 使用模拟数据 / tushare / akshare

2. **并发性能** (Medium)
   - 风险: 高并发下性能下降
   - 缓解: 压力测试 + 优化

3. **WebSocket稳定性** (Medium)
   - 风险: 连接断开、消息丢失
   - 缓解: 重连机制 + 心跳检测

### 进度风险

1. **时间压力** (Medium)
   - 风险: 3周时间紧张
   - 缓解: 优先级管理，P0先行

2. **依赖阻塞** (Low)
   - 风险: 某个服务阻塞整体进度
   - 缓解: 并行开发，独立测试

---

## 💡 Phase 3 vs Phase 2

| 维度 | Phase 2 | Phase 3 |
|------|---------|---------|
| 服务数量 | 6个 | 11个 |
| 数据流 | 部分打通 | 完全打通 |
| 前端集成 | 未集成 | 完全集成 |
| 实时推送 | 无 | WebSocket |
| 监控告警 | 基础 | 完善 |
| 部署方式 | 手动 | 自动化 |

---

## 📚 参考资源

### 内部文档
- [Phase 2 交付文档](Phase2_Delivery_Document.md)
- [服务状态](../SERVICES_STATUS.md)
- [分时数据处理中心启动指南](分时数据处理中心启动指南.md)

### 外部资源
- WebSocket 最佳实践
- Redis Streams 文档
- FastAPI WebSocket 指南
- Docker Compose 文档

---

**Phase 3 准备就绪！**

让我们开始打通完整的数据流水线，实现端到端的实时信号生成与推送！

---

**文档编制**: Claude Code
**创建日期**: 2025-09-30
**版本**: v1.0-draft