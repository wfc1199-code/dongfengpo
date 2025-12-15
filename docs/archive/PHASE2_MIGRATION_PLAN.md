# Phase 2 - 业务逻辑迁移详细计划

**启动时间**: 2025-10-01
**预计完成**: 2025-11-01 (4周)
**当前阶段**: Phase 1 完成 → Phase 2 启动

---

## 📊 Legacy系统分析

### 核心业务模块

| 模块 | 文件 | 代码量 | 功能 | 优先级 |
|------|------|--------|------|--------|
| **异动检测** | `anomaly_detection.py` | 874行 | 涨速异动、放量检测、大单监控 | P0 |
| **数据管理** | `data_sources.py` | 1647行 | 股票数据获取、缓存管理 | P0 |
| **涨停预测** | `limit_up_predictor.py` | 未统计 | 涨停概率计算 | P1 |
| **市场扫描** | `market_scanner.py` | 未统计 | 全市场异动扫描 | P1 |
| **主力行为** | `market_behavior_analyzer.py` | 未统计 | 主力资金分析 | P2 |

### 异动检测核心类

**backend/core/anomaly_detection.py** 包含:

```python
class StockState(Enum):
    IDLE, PRE_ALERT, STARTING, CONTINUING, NEAR_LIMIT, LIMIT_UP

class AnomalyType(Enum):
    PRE_VOLUME_SURGE    # 成交量预警
    SPEED_UP            # 涨速异动
    VOLUME_SURGE        # 放量异动
    BIG_ORDER           # 大单异动
    CAPITAL_INFLOW      # 资金流入
    BREAKTHROUGH        # 突破前高

class EarlyWarningDetector:
    """提前预警检测器"""

class BigOrderDetector:
    """大单检测器"""

class CapitalFlowCalculator:
    """资金流向计算器"""

class AnomalyDetector:
    """异动检测主引擎"""

class StockAnalysisEngine:
    """股票分析引擎 - 对外接口"""
```

### API路由依赖

**18个Legacy路由**:
1. `anomaly_routes` - 异动检测 (使用AnomalyDetector)
2. `limit_up_routes` - 涨停预测
3. `market_scanner_routes` - 市场扫描
4. `market_behavior_routes` - 主力行为
5. `transaction_routes` - 成交分析
6. ... (共31个路由)

---

## 🎯 Phase 2 目标

### 主要目标

1. ✅ **迁移异动检测逻辑** - 从Legacy迁移到strategy-engine
2. ✅ **统一数据源** - collector-gateway替代data_sources
3. ✅ **建立策略插件** - 异动检测、涨停预测等改造为策略
4. ✅ **验证数据一致性** - 新旧系统输出对比
5. ✅ **前端API切换** - 调用新服务API

### 成功标准

- [ ] 异动检测策略在strategy-engine正常运行
- [ ] 涨停预测策略在strategy-engine正常运行
- [ ] 新旧系统检测结果一致性>95%
- [ ] 前端成功调用新API
- [ ] Legacy相关路由标记为Deprecated

---

## 📋 迁移路线图

### Week 1: 异动检测迁移 (P0)

#### 任务1.1: 策略插件开发

**目标**: 将`anomaly_detection.py`改造为策略插件

**步骤**:
1. 分析现有异动检测逻辑
2. 设计策略接口
3. 实现`AnomalyDetectionStrategy`
4. 集成到strategy-engine

**输出文件**:
```
services/strategy-engine/strategies/
├── anomaly_detection/
│   ├── strategy.yaml
│   ├── strategy.py
│   ├── detectors.py  (EarlyWarningDetector, BigOrderDetector等)
│   └── README.md
```

**strategy.yaml示例**:
```yaml
name: anomaly_detection
version: 2.0.0
author: dongfengpo_team
description: 股票异动检测策略(涨速、放量、大单)

dependencies:
  - price_change_rate
  - volume_ratio
  - turnover_rate
  - bid_ask_ratio

parameters:
  speed_threshold: 0.02      # 涨速阈值2%
  volume_threshold: 2.0      # 量比阈值2倍
  big_order_threshold: 300   # 大单阈值300万
  early_warning: true        # 启用提前预警

risk_controls:
  max_signals_per_minute: 20
  min_confidence: 0.6
```

**strategy.py框架**:
```python
from strategy_engine.base import BaseStrategy
from typing import List

class AnomalyDetectionStrategy(BaseStrategy):
    name = "anomaly_detection"
    version = "2.0.0"

    required_features = [
        "price_change_rate",
        "volume_ratio",
        "turnover_rate"
    ]

    def __init__(self, config):
        super().__init__(config)
        self.early_warning = EarlyWarningDetector(config)
        self.big_order = BigOrderDetector(config)
        self.capital_flow = CapitalFlowCalculator(config)

    async def analyze(self, features: dict) -> List[Signal]:
        """分析特征并生成信号"""
        signals = []

        # 1. 涨速异动检测
        if features['price_change_rate'] > self.config['speed_threshold']:
            signals.append(Signal(
                type='speed_up',
                confidence=self._calc_confidence(features),
                reason=f"涨速异动: {features['price_change_rate']:.2%}"
            ))

        # 2. 放量异动检测
        if features['volume_ratio'] > self.config['volume_threshold']:
            signals.append(Signal(
                type='volume_surge',
                confidence=self._calc_confidence(features),
                reason=f"放量异动: 量比{features['volume_ratio']:.1f}"
            ))

        # 3. 大单检测
        big_orders = self.big_order.detect(features)
        signals.extend(big_orders)

        return signals
```

#### 任务1.2: 数据流适配

**目标**: 确保feature-pipeline输出的特征满足策略需求

**步骤**:
1. 检查现有特征计算
2. 添加缺失特征(bid_ask_ratio, money_flow等)
3. 验证特征准确性

**需要的特征**:
- price_change_rate (涨幅)
- volume_ratio (量比)
- turnover_rate (换手率)
- bid_ask_ratio (委比)
- money_flow_5min (5分钟资金流)
- speed (涨速)

#### 任务1.3: 新旧对比测试

**测试框架**:
```python
# tests/test_anomaly_migration.py

async def test_anomaly_consistency():
    """对比新旧异动检测结果"""

    # 获取相同股票的实时数据
    stock_codes = ['000001', '600000', '000002']

    for code in stock_codes:
        # 1. Legacy检测
        legacy_result = await legacy_anomaly_detect(code)

        # 2. 新策略检测
        new_result = await new_strategy_detect(code)

        # 3. 对比结果
        consistency = compare_results(legacy_result, new_result)
        assert consistency > 0.95, f"一致性不足: {consistency}"
```

### Week 2: 涨停预测迁移 (P1)

#### 任务2.1: 涨停预测策略

**文件**: `services/strategy-engine/strategies/limit_up_prediction/`

**核心逻辑**:
```python
class LimitUpPredictionStrategy(BaseStrategy):
    """涨停预测策略"""

    async def analyze(self, features: dict) -> List[Signal]:
        # 1. 计算涨停概率
        probability = self._calc_limit_up_probability(features)

        # 2. 判断是否接近涨停
        if probability > 0.7:
            return [Signal(
                type='near_limit_up',
                confidence=probability,
                metadata={'distance_to_limit': features['distance']}
            )]

        return []

    def _calc_limit_up_probability(self, features):
        """涨停概率计算"""
        # 从Legacy的limit_up_predictor.py迁移算法
        score = 0
        score += features['price_change_rate'] * 30
        score += features['volume_ratio'] * 20
        score += features['turnover_rate'] * 15
        # ...
        return min(score / 100, 1.0)
```

#### 任务2.2: 时间分段预测

**需求**: 支持多时间段预测(9:30-10:00, 10:00-10:30等)

**实现**: 在opportunity-aggregator中实现时间段聚合

### Week 3: 数据源统一 (P0)

#### 任务3.1: collector-gateway增强

**目标**: 替代Legacy的data_sources.py

**需要实现**:
1. 腾讯财经API适配器(已有)
2. 东方财富API适配器
3. 新浪财经API适配器
4. 数据缓存策略

**配置**:
```yaml
# services/collector-gateway/config.yaml
sources:
  - name: tencent
    enabled: true
    priority: 1
    symbols: ['000001', '600000', ...]

  - name: eastmoney
    enabled: true
    priority: 2
    symbols: ['000001', '600000', ...]

cache:
  ttl: 300  # 5分钟缓存
  redis_url: redis://localhost:6379/0
```

#### 任务3.2: 缓存层统一

**目标**: 将Legacy cache_manager迁移到Redis

**步骤**:
1. 分析Legacy缓存逻辑
2. 在collector-gateway实现Redis缓存
3. 配置缓存策略(TTL、淘汰算法)
4. 性能对比测试

### Week 4: 前端切换与验证 (P0)

#### 任务4.1: 新API端点开发

**signal-api新增端点**:
```python
# services/signal-api/routers/anomaly.py

@router.get("/api/v2/anomaly/detect")
async def detect_anomaly(stock_code: str):
    """异动检测接口 - 替代Legacy /api/anomaly/detect-legacy"""
    opportunities = await query_opportunities(
        symbol=stock_code,
        strategy="anomaly_detection",
        state=["NEW", "ACTIVE"]
    )
    return format_anomaly_response(opportunities)

@router.get("/api/v2/limit-up/predict")
async def predict_limit_up(stock_code: str):
    """涨停预测接口 - 替代Legacy /api/limit-up/*"""
    opportunities = await query_opportunities(
        symbol=stock_code,
        strategy="limit_up_prediction"
    )
    return format_limit_up_response(opportunities)
```

#### 任务4.2: 前端API切换

**修改文件**: `frontend/src/services/api.ts`

```typescript
// 旧API (通过网关访问Legacy)
const getLegacyAnomaly = (code: string) =>
  api.get(`/api/anomaly/detect-legacy?code=${code}`);

// 新API (通过网关访问signal-api)
const getNewAnomaly = (code: string) =>
  api.get(`/api/v2/anomaly/detect?stock_code=${code}`);

// 使用特性开关
export const getAnomaly = USE_NEW_API
  ? getNewAnomaly
  : getLegacyAnomaly;
```

#### 任务4.3: A/B测试

**策略**: 10% → 50% → 100%灰度切换

```typescript
const shouldUseNewApi = () => {
  const rollout = 0.5;  // 50%流量
  return Math.random() < rollout;
};

export const getAnomaly = (code: string) => {
  return shouldUseNewApi()
    ? getNewAnomaly(code)
    : getLegacyAnomaly(code);
};
```

#### 任务4.4: Legacy标记废弃

```python
# backend/api/anomaly_routes.py

@router.get("/api/anomaly/detect-legacy")
@deprecated(
    version="2.0.0",
    reason="请使用新API: /api/v2/anomaly/detect",
    sunset_date="2025-12-01"
)
async def detect_anomaly_legacy(code: str):
    """异动检测 [已废弃]"""
    logger.warning(f"Legacy API called: /anomaly/detect-legacy")
    # 返回Deprecation警告头
    headers = {
        "X-API-Deprecated": "true",
        "X-API-Sunset": "2025-12-01",
        "X-API-Alternative": "/api/v2/anomaly/detect"
    }
    return Response(..., headers=headers)
```

---

## 📊 迁移进度跟踪

### Week 1 - 异动检测迁移

| 任务 | 负责 | 状态 | 完成度 |
|------|------|------|--------|
| 策略插件设计 | - | 🔄 规划中 | 0% |
| 策略代码实现 | - | ⏸️ 待开始 | 0% |
| 特征适配 | - | ⏸️ 待开始 | 0% |
| 新旧对比测试 | - | ⏸️ 待开始 | 0% |

### Week 2 - 涨停预测迁移

| 任务 | 负责 | 状态 | 完成度 |
|------|------|------|--------|
| 策略插件实现 | - | ⏸️ 待开始 | 0% |
| 时间分段支持 | - | ⏸️ 待开始 | 0% |
| 测试验证 | - | ⏸️ 待开始 | 0% |

### Week 3 - 数据源统一

| 任务 | 负责 | 状态 | 完成度 |
|------|------|------|--------|
| 多数据源适配器 | - | ⏸️ 待开始 | 0% |
| Redis缓存实现 | - | ⏸️ 待开始 | 0% |
| 性能测试 | - | ⏸️ 待开始 | 0% |

### Week 4 - 前端切换

| 任务 | 负责 | 状态 | 完成度 |
|------|------|------|--------|
| 新API开发 | - | ⏸️ 待开始 | 0% |
| 前端切换 | - | ⏸️ 待开始 | 0% |
| A/B测试 | - | ⏸️ 待开始 | 0% |
| Legacy标记 | - | ⏸️ 待开始 | 0% |

---

## 🎯 验收标准

### 功能完整性

- [ ] 异动检测功能正常(涨速、放量、大单)
- [ ] 涨停预测功能正常
- [ ] 时间分段功能正常
- [ ] 实时推送功能正常

### 性能指标

- [ ] 异动检测延迟 < 2秒
- [ ] 数据一致性 > 95%
- [ ] API响应时间 < 100ms (P95)
- [ ] 系统吞吐量 > 100 req/s

### 代码质量

- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试通过
- [ ] 代码review完成
- [ ] 文档更新完成

### 用户体验

- [ ] 前端功能无变化
- [ ] 响应速度无明显下降
- [ ] 无重大bug
- [ ] 监控告警正常

---

## ⚠️ 风险评估

### 高风险

1. **数据一致性**
   - 风险: 新旧算法结果不一致
   - 缓解: 严格对比测试,差异<5%才上线
   - 应急: 快速回滚到Legacy

2. **性能下降**
   - 风险: 多层服务增加延迟
   - 缓解: 性能测试,优化瓶颈
   - 应急: 调整超时配置,增加缓存

### 中风险

3. **特征缺失**
   - 风险: feature-pipeline未计算某些特征
   - 缓解: 提前梳理所需特征
   - 应急: 在strategy-engine补充计算

4. **Legacy依赖**
   - 风险: 发现未知的隐藏依赖
   - 缓解: 详细代码审查
   - 应急: 保留Legacy作为fallback

### 低风险

5. **前端兼容**
   - 风险: API格式变化导致前端报错
   - 缓解: 保持API接口兼容
   - 应急: adapter层做格式转换

---

## 📚 参考文档

- [Phase 1 完成报告](MIGRATION_PHASE1_FINAL_REPORT.md)
- [架构统一迁移计划](docs/架构统一迁移计划.md)
- [策略引擎文档](services/strategy-engine/README.md)
- [数据合约定义](libs/data_contracts/)

---

## 🚀 启动清单

### 开始前准备

- [x] Phase 1完成验证
- [x] 数据流水线打通
- [x] 前端网关模式验证
- [ ] 团队资源分配
- [ ] 详细时间表制定

### Week 1 启动

- [ ] 创建feature分支: `feature/phase2-anomaly-migration`
- [ ] 分析anomaly_detection.py核心逻辑
- [ ] 设计策略插件接口
- [ ] 搭建测试框架

---

**Phase 2 迁移计划已制定,准备启动!** 🚀
