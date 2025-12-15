# Phase 3 实施计划 - 灰度发布与前端集成

**制定日期**: 2025-10-01
**预计工期**: 2-3周
**状态**: 计划中

---

## 📋 目标概述

Phase 3 的核心目标是实现新微服务架构的灰度发布，通过前端开关控制流量逐步从 Legacy 后端切换到新的微服务系统，同时确保系统稳定性和可回滚性。

### 关键成果
1. ✅ 前端集成Signal API
2. ✅ 灰度发布配置系统
3. ✅ 流量切换控制面板
4. ✅ 双系统并行运行
5. ✅ 性能对比监控

---

## 🏗️ 技术架构

### 当前架构分析

#### 前端配置系统
```typescript
// frontend/src/config.ts (已存在)
export const USE_API_GATEWAY = process.env.REACT_APP_USE_API_GATEWAY === 'true';
export const LEGACY_API_BASE_URL = 'http://localhost:9000';
export const PIPELINE_API_BASE_URL = 'http://localhost:8001';  // Signal API端口应改为8000
```

**发现的问题**:
- 现有配置中 `PIPELINE_API_BASE_URL` 指向端口8001，但我们的Signal API在端口8000
- 需要添加细粒度的功能开关，支持按功能模块切换

#### 后端服务
```
Legacy Backend (port 9000)
├── /api/anomaly/*           ← 异动检测接口
├── /api/limit-up/*          ← 涨停预测接口
└── /api/realtime/*          ← 实时数据接口

New Microservices
├── signal-api (port 8000)
│   ├── GET /signals         ← 统一信号查询
│   ├── GET /signals/stats   ← 统计信息
│   └── GET /health          ← 健康检查
├── strategy-engine
│   ├── anomaly_detection    ← 异动检测策略
│   └── limit_up_prediction  ← 涨停预测策略
└── Data Pipeline (collector → cleaner → features → signals)
```

### 目标架构

```
┌─────────────────────────────────────────────────────┐
│               Frontend (React + TypeScript)         │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │       Feature Flag Manager                   │  │
│  │  • 按功能模块控制流量                          │  │
│  │  • 支持百分比切换 (0% → 100%)                 │  │
│  │  │  • 支持用户粒度切换                          │  │
│  └──────────────────────────────────────────────┘  │
│          ↓                          ↓               │
│   ┌──────────┐              ┌──────────┐           │
│   │  Legacy  │              │   New    │           │
│   │ Service  │              │ Service  │           │
│   │  Client  │              │  Client  │           │
│   └──────────┘              └──────────┘           │
└─────────────────────────────────────────────────────┘
         ↓                            ↓
┌────────────────┐          ┌───────────────────┐
│ Legacy Backend │          │  Signal API       │
│  (port 9000)   │          │  (port 8000)      │
└────────────────┘          └───────────────────┘
```

---

## 📅 实施计划

### Week 1: Signal API 客户端集成

#### 任务1.1: 创建Signal API Service
**文件**: `frontend/src/services/signal.service.ts`

**功能**:
- 封装Signal API的所有端点调用
- 数据类型定义 (TypeScript接口)
- 错误处理和重试逻辑
- 缓存策略

**接口设计**:
```typescript
interface SignalAPIService {
  // 获取信号列表
  getSignals(params: {
    limit?: number;
    strategy?: string;
    symbol?: string;
    signal_type?: string;
    min_confidence?: number;
  }): Promise<StrategySignal[]>;

  // 获取统计信息
  getStats(): Promise<SignalStats>;

  // 获取特定股票的信号
  getSignalsBySymbol(symbol: string, limit?: number): Promise<StrategySignal[]>;

  // 健康检查
  healthCheck(): Promise<{ status: string }>;
}
```

**预计工作量**: 4小时

---

#### 任务1.2: 数据类型定义
**文件**: `frontend/src/types/signal.ts`

**内容**:
```typescript
export interface StrategySignal {
  strategy: string;
  symbol: string;
  signal_type: string;
  confidence: number;
  strength_score: number;
  reasons: string[];
  triggered_at: string;
  window: string;
  metadata: Record<string, any>;
}

export interface SignalStats {
  total_signals: number;
  average_confidence: number;
  strategies: Record<string, number>;
  signal_types: Record<string, number>;
  top_symbols: Record<string, number>;
}

export interface SignalQueryParams {
  limit?: number;
  strategy?: 'anomaly_detection' | 'limit_up_prediction';
  symbol?: string;
  signal_type?: string;
  min_confidence?: number;
}
```

**预计工作量**: 2小时

---

#### 任务1.3: 灰度配置系统
**文件**: `frontend/src/config/featureFlags.ts`

**功能**:
- 按功能模块控制切换
- 支持百分比流量切换
- localStorage持久化配置
- 运行时动态切换

**配置结构**:
```typescript
export interface FeatureFlags {
  // 异动检测模块
  anomalyDetection: {
    enabled: boolean;          // 是否启用新系统
    rolloutPercentage: number; // 流量百分比 (0-100)
    forceUsers?: string[];     // 强制使用新系统的用户ID
  };

  // 涨停预测模块
  limitUpPrediction: {
    enabled: boolean;
    rolloutPercentage: number;
    forceUsers?: string[];
  };

  // 全局开关
  global: {
    useNewArchitecture: boolean;  // 全局启用新架构
    fallbackToLegacy: boolean;    // 出错时回退到旧系统
  };
}
```

**实现要点**:
- 哈希算法决定用户分流 (基于用户ID或随机数)
- 本地开发环境支持手动覆盖
- 提供调试界面显示当前配置

**预计工作量**: 6小时

---

### Week 2: 前端组件改造

#### 任务2.1: 异动检测组件改造
**文件**: `frontend/src/components/AnomalyPanel.tsx`

**改造内容**:
```typescript
// 原有逻辑
const fetchAnomaliesLegacy = async () => {
  const response = await fetch(`${LEGACY_API_BASE_URL}/api/anomaly`);
  return response.json();
};

// 新增逻辑
const fetchAnomaliesNew = async () => {
  return await signalService.getSignals({
    strategy: 'anomaly_detection',
    limit: 100
  });
};

// 灰度切换逻辑
const fetchAnomalies = async () => {
  const flags = getFeatureFlags();

  if (shouldUseNewSystem('anomalyDetection', flags)) {
    try {
      return await fetchAnomaliesNew();
    } catch (error) {
      console.error('New system error, fallback to legacy:', error);
      if (flags.global.fallbackToLegacy) {
        return await fetchAnomaliesLegacy();
      }
      throw error;
    }
  } else {
    return await fetchAnomaliesLegacy();
  }
};
```

**验证要点**:
- 数据格式兼容性 (Legacy vs New)
- UI渲染一致性
- 性能对比 (加载时间, 内存占用)

**预计工作量**: 8小时

---

#### 任务2.2: 数据格式适配器
**文件**: `frontend/src/adapters/signalAdapter.ts`

**功能**:
- 将Signal API的数据格式转换为Legacy格式
- 确保组件无缝切换

**示例**:
```typescript
// Legacy格式
interface LegacyAnomaly {
  stock_code: string;
  stock_name: string;
  anomaly_type: string;
  confidence: number;
  timestamp: string;
  details: string[];
}

// 适配器
export const signalToLegacyAnomaly = (signal: StrategySignal): LegacyAnomaly => ({
  stock_code: signal.symbol,
  stock_name: signal.metadata.stock_name || signal.symbol,
  anomaly_type: signal.signal_type,
  confidence: signal.confidence,
  timestamp: signal.triggered_at,
  details: signal.reasons
});
```

**预计工作量**: 4小时

---

### Week 3: 灰度控制面板与监控

#### 任务3.1: 灰度控制面板
**文件**: `frontend/src/components/admin/FeatureFlagPanel.tsx`

**功能**:
- 可视化配置界面
- 实时切换流量百分比
- 显示双系统性能对比
- 一键回滚功能

**界面设计**:
```
┌────────────────────────────────────────────────┐
│      灰度发布控制面板                           │
├────────────────────────────────────────────────┤
│                                                │
│  【异动检测模块】                               │
│   ○ Legacy (旧系统)                            │
│   ● New (新系统)   [流量: ▓▓▓░░░░░░░ 30%]      │
│                                                │
│   性能对比:                                     │
│   • 平均响应时间: 45ms ← 120ms (↓62%)          │
│   • 错误率: 0.1% ← 0.5% (↓80%)                 │
│   • 信号数量: 532/min ← 450/min (↑18%)         │
│                                                │
│   [增加至50%]  [回滚到Legacy]                  │
│                                                │
├────────────────────────────────────────────────┤
│  【涨停预测模块】                               │
│   ● Legacy (旧系统)   [流量: ▓▓▓▓▓▓▓▓▓▓ 100%]  │
│   ○ New (新系统)      [流量: ░░░░░░░░░░ 0%]    │
│                                                │
│   [启用新系统]                                 │
│                                                │
└────────────────────────────────────────────────┘
```

**预计工作量**: 12小时

---

#### 任务3.2: 性能监控集成
**文件**: `frontend/src/utils/performanceMonitor.ts`

**监控指标**:
```typescript
interface PerformanceMetrics {
  system: 'legacy' | 'new';
  endpoint: string;
  responseTime: number;
  success: boolean;
  errorType?: string;
  timestamp: number;
  dataSize?: number;
}

class PerformanceMonitor {
  // 记录API调用性能
  recordAPICall(metrics: PerformanceMetrics): void;

  // 获取统计信息
  getStats(system: 'legacy' | 'new', timeRange: number): {
    avgResponseTime: number;
    p95ResponseTime: number;
    errorRate: number;
    requestCount: number;
  };

  // 对比两个系统
  compare(): ComparisonResult;
}
```

**上报机制**:
- 本地聚合 (localStorage)
- 定期上报到后端 (可选)
- 实时显示在控制面板

**预计工作量**: 6小时

---

## 🧪 测试策略

### 功能测试

#### 1. 单元测试
```typescript
// signal.service.test.ts
describe('SignalAPIService', () => {
  test('should fetch signals with correct params', async () => {
    const signals = await signalService.getSignals({
      strategy: 'anomaly_detection',
      limit: 10
    });
    expect(signals).toHaveLength(10);
    expect(signals[0]).toHaveProperty('strategy', 'anomaly_detection');
  });

  test('should handle API errors gracefully', async () => {
    // Mock network error
    await expect(signalService.getSignals({})).rejects.toThrow();
  });
});
```

#### 2. 集成测试
```typescript
// featureFlags.test.ts
describe('Feature Flags', () => {
  test('should route to new system when enabled', () => {
    setFeatureFlags({ anomalyDetection: { enabled: true, rolloutPercentage: 100 } });
    expect(shouldUseNewSystem('anomalyDetection')).toBe(true);
  });

  test('should respect rollout percentage', () => {
    setFeatureFlags({ anomalyDetection: { enabled: true, rolloutPercentage: 30 } });
    // 测试1000次调用，约30%应使用新系统
    const results = Array.from({ length: 1000 }, () =>
      shouldUseNewSystem('anomalyDetection')
    );
    const newSystemCount = results.filter(Boolean).length;
    expect(newSystemCount).toBeGreaterThan(250);
    expect(newSystemCount).toBeLessThan(350);
  });
});
```

### 性能测试

#### 基准测试场景
1. **响应时间测试**
   - Legacy: 期望 < 100ms
   - New: 期望 < 50ms

2. **并发测试**
   - 100个并发请求
   - 测量P95延迟

3. **数据一致性测试**
   - 对比两个系统返回的数据
   - 验证信号数量和质量

---

## 🚀 灰度发布流程

### 阶段1: 0% → 10% (第1周)
**时间**: Week 1, Day 1-2
**操作**:
```typescript
setFeatureFlags({
  anomalyDetection: {
    enabled: true,
    rolloutPercentage: 10
  }
});
```

**验证**:
- 错误率 < 1%
- P95响应时间 < 100ms
- 无数据异常

**回滚条件**:
- 错误率 > 5%
- P95响应时间 > 200ms
- 用户反馈负面

---

### 阶段2: 10% → 30% (第1周)
**时间**: Week 1, Day 3-5
**操作**:
```typescript
setFeatureFlags({
  anomalyDetection: {
    enabled: true,
    rolloutPercentage: 30
  }
});
```

**监控重点**:
- 数据流稳定性
- Redis内存使用
- 信号生成速率

---

### 阶段3: 30% → 50% (第2周)
**时间**: Week 2, Day 1-3

**验证**:
- 前端性能对比报告
- 用户体验调研
- 系统资源使用

---

### 阶段4: 50% → 100% (第2周)
**时间**: Week 2, Day 4-7

**最终验证**:
- 7天稳定运行
- 所有功能正常
- 性能优于Legacy

---

### 阶段5: Legacy下线 (第3周)
**时间**: Week 3

**操作**:
```typescript
setFeatureFlags({
  global: { useNewArchitecture: true },
  anomalyDetection: { enabled: true, rolloutPercentage: 100 },
  limitUpPrediction: { enabled: true, rolloutPercentage: 100 }
});
```

**清理工作**:
- 移除Legacy API调用代码
- 清理Feature Flag逻辑
- 更新文档

---

## 📊 成功指标

### 性能指标
| 指标 | Legacy基准 | 新系统目标 | 测量方法 |
|------|-----------|-----------|---------|
| 平均响应时间 | 100ms | <50ms | Performance API |
| P95响应时间 | 200ms | <100ms | Performance API |
| 错误率 | 0.5% | <0.1% | Error logging |
| 信号生成速率 | 450/min | >500/min | Signal count |
| 前端渲染时间 | 300ms | <200ms | React Profiler |

### 用户体验指标
- [ ] UI无闪烁或卡顿
- [ ] 数据刷新流畅
- [ ] 无功能缺失
- [ ] 错误提示友好

### 系统稳定性指标
- [ ] 7天无重大故障
- [ ] 自动回滚机制有效
- [ ] 日志完整可追溯

---

## 🛠️ 技术实施细节

### 1. Feature Flag实现

#### 存储方案
```typescript
// localStorage
const FEATURE_FLAGS_KEY = 'dfp_feature_flags';

export const getFeatureFlags = (): FeatureFlags => {
  const stored = localStorage.getItem(FEATURE_FLAGS_KEY);
  if (stored) {
    return JSON.parse(stored);
  }
  return DEFAULT_FLAGS;
};

export const setFeatureFlags = (flags: Partial<FeatureFlags>): void => {
  const current = getFeatureFlags();
  const updated = { ...current, ...flags };
  localStorage.setItem(FEATURE_FLAGS_KEY, JSON.stringify(updated));
  // 触发事件通知其他组件
  window.dispatchEvent(new CustomEvent('featureFlagsChanged', { detail: updated }));
};
```

#### 流量分配算法
```typescript
// 基于用户ID或随机数的哈希
export const shouldUseNewSystem = (
  feature: keyof FeatureFlags,
  flags: FeatureFlags
): boolean => {
  const config = flags[feature];
  if (!config.enabled) return false;
  if (config.rolloutPercentage === 100) return true;
  if (config.rolloutPercentage === 0) return false;

  // 使用sessionStorage中的随机ID确保同一会话内一致
  let sessionId = sessionStorage.getItem('dfp_session_id');
  if (!sessionId) {
    sessionId = Math.random().toString(36).substring(7);
    sessionStorage.setItem('dfp_session_id', sessionId);
  }

  // 简单哈希
  const hash = sessionId.split('').reduce((acc, char) =>
    acc + char.charCodeAt(0), 0
  );

  return (hash % 100) < config.rolloutPercentage;
};
```

---

### 2. 数据适配层

#### 统一接口
```typescript
// frontend/src/services/unified.service.ts
export class UnifiedAnomalyService {
  private legacyService: LegacyAnomalyService;
  private signalService: SignalAPIService;

  async getAnomalies(params: AnomalyQueryParams): Promise<NormalizedAnomaly[]> {
    const flags = getFeatureFlags();

    if (shouldUseNewSystem('anomalyDetection', flags)) {
      const signals = await this.signalService.getSignals({
        strategy: 'anomaly_detection',
        ...params
      });
      return signals.map(signalToLegacyAnomaly);
    } else {
      return await this.legacyService.getAnomalies(params);
    }
  }
}
```

---

### 3. 错误处理与回退

```typescript
class ResilientAPIClient {
  async call<T>(
    newSystemCall: () => Promise<T>,
    legacyCall: () => Promise<T>,
    options: { timeout?: number; retries?: number } = {}
  ): Promise<T> {
    const flags = getFeatureFlags();

    if (shouldUseNewSystem('...', flags)) {
      try {
        return await withTimeout(newSystemCall(), options.timeout || 5000);
      } catch (error) {
        console.error('New system failed:', error);

        // 记录失败
        this.recordFailure('new_system', error);

        // 自动回退
        if (flags.global.fallbackToLegacy) {
          console.warn('Falling back to legacy system');
          return await legacyCall();
        }

        throw error;
      }
    } else {
      return await legacyCall();
    }
  }
}
```

---

## 📁 文件清单

### 新增文件
```
frontend/src/
├── services/
│   ├── signal.service.ts              (新增, ~200行)
│   └── unified.service.ts             (新增, ~150行)
├── types/
│   └── signal.ts                      (新增, ~80行)
├── config/
│   └── featureFlags.ts                (新增, ~150行)
├── adapters/
│   └── signalAdapter.ts               (新增, ~100行)
├── components/admin/
│   └── FeatureFlagPanel.tsx           (新增, ~300行)
└── utils/
    └── performanceMonitor.ts          (新增, ~200行)
```

### 修改文件
```
frontend/src/
├── config.ts                          (修改端口配置)
├── components/
│   ├── AnomalyPanel.tsx               (集成灰度切换)
│   └── AnomalyAlerts.tsx              (集成灰度切换)
└── services/
    └── anomaly.service.ts             (添加新系统调用)
```

**代码量估算**: ~1200行新增代码

---

## 🎯 风险与对策

### 风险1: 数据格式不兼容
**影响**: 前端渲染错误
**对策**:
- 完善数据适配层
- 添加数据格式验证
- 提供降级方案

### 风险2: 性能不达预期
**影响**: 用户体验下降
**对策**:
- 性能监控实时告警
- 快速回滚机制
- 缓存策略优化

### 风险3: 新系统稳定性问题
**影响**: 频繁错误
**对策**:
- 自动回退到Legacy
- 错误日志详细记录
- 分阶段缓慢推进

### 风险4: 用户反馈负面
**影响**: 信任度下降
**对策**:
- 提供手动切换选项
- 及时响应用户问题
- 透明化灰度进度

---

## 📝 检查清单

### 开发阶段
- [ ] Signal API Service实现
- [ ] 数据类型定义完整
- [ ] Feature Flag系统实现
- [ ] 数据适配器实现
- [ ] 组件改造完成
- [ ] 单元测试覆盖率>80%
- [ ] 集成测试通过

### 灰度发布阶段
- [ ] 0%→10% 验证通过
- [ ] 10%→30% 验证通过
- [ ] 30%→50% 验证通过
- [ ] 50%→100% 验证通过
- [ ] 性能监控数据收集
- [ ] 用户反馈收集

### 清理阶段
- [ ] Legacy代码移除
- [ ] Feature Flag逻辑简化
- [ ] 文档更新
- [ ] 部署文档更新

---

## 📚 相关文档

- [PHASE2_DELIVERY_SUMMARY.md](./PHASE2_DELIVERY_SUMMARY.md) - Phase 2交付总结
- [PHASE2_FINAL_VERIFICATION.md](./PHASE2_FINAL_VERIFICATION.md) - Phase 2验证报告
- [QUICK_START_GUIDE.md](./QUICK_START_GUIDE.md) - 系统快速开始指南
- [README_V2.md](./README_V2.md) - 项目完整文档

---

## 🚀 下一步行动

### 立即执行 (本周)
1. 创建Signal API Service
2. 实现Feature Flag系统
3. 开发灰度控制面板

### 短期计划 (下周)
1. 改造异动检测组件
2. 开始0%→10%灰度发布
3. 收集性能数据

### 中期计划 (2周后)
1. 完成100%流量切换
2. Legacy系统下线
3. Phase 3验收

---

**制定人**: Claude Agent
**审批状态**: 待审批
**预计完成日期**: 2025-10-22
