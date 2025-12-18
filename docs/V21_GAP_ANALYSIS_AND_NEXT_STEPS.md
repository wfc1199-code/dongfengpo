# v21 融合方案 Gap 分析与下一步计划

**分析日期**: 2025-12-17  
**对照文件**: 
- v20需求: `implementation_plan.md.resolved.22`
- v21现状: `.gemini/antigravity/brain/.../implementation_plan.md.resolved`

---

## 📊 完成度总览

| Phase | 内容 | v20要求 | 当前状态 | 完成度 |
|-------|------|---------|----------|--------|
| **Phase 1** | 统一评分系统 | 5维评分+集成 | ✅ 已完成 | **100%** |
| **Phase 2** | 策略连通 | Ignition+Ambush融合 | ⚠️ 部分完成 | **60%** |
| **Phase 3** | 基础设施 | DuckDB+数据质量 | ⚠️ 部分完成 | **40%** |
| **Phase 4** | AI+可观测性 | AI审核+监控 | ✅ 基本完成 | **90%** |

---

## 🔍 详细 Gap 分析

### Phase 1: 统一评分系统 ✅ **100% 完成**

| 需求项 | v20要求 | 当前状态 | 差距 |
|--------|---------|----------|------|
| UnifiedScorer 类 | 5维评分算法 | ✅ `scorer.py` 已实现 | 无 |
| 适配不同数据源 | 日线/分钟线 | ✅ `StockMetrics` 通用 | 无 |
| 集成盯盘雷达 | `get_realtime_predictions()` | ✅ 已集成 | 无 |
| 集成明日潜力 | `get_second_board_candidates()` | ✅ 已集成 | 无 |
| 前端显示 | 各维度得分详情 | ⚠️ 部分完成 | 需UI增强 |

**结论**: Phase 1 已完成，仅需前端UI增强（P2优先级）。

---

### Phase 2: 策略连通 ⚠️ **60% 完成**

#### 2.1 盯盘雷达 + Ignition策略

| 需求项 | v20要求 | 当前状态 | 差距 |
|--------|---------|----------|------|
| IgnitionAdapter | 异动→点火策略 | ✅ `adapters.py` 已实现 | 无 |
| **分钟线数据源** | Tushare Pro接入 | ⚠️ 代码存在但未集成 | **P0缺失** |
| 数据缓存机制 | 实时缓存 | ✅ 评分缓存已有 | 需扩展 |
| 数据质量检查 | 240根K线校验 | ❌ 未实现 | **P0缺失** |
| **WebSocket推送** | 实时信号推送 | ⚠️ 代码存在但未集成 | **P1缺失** |
| 风控检查集成 | RiskManager调用 | ✅ P0修复已完成 | 无 |

**关键发现**:
- ✅ `TushareClient` 已存在 (`tushare_client.py`)
- ✅ `DataManager` 已存在 (`data/manager.py`)
- ⚠️ **但未集成到 `IgnitionAdapter._evaluate_ignition()`**
- ⚠️ **当前使用简化评估，未真正调用 `IgnitionStrategy`**

**代码证据**:
```python
# adapters.py 第173-215行：简化的点火评估
def _evaluate_ignition(self, stock_data: Dict, score_result: ScoringResult) -> tuple:
    # 简化的点火评估（无分钟线数据时）
    # ⚠️ 未真正调用 IgnitionStrategy
    # ⚠️ 未使用分钟线数据
```

#### 2.2 明日潜力 + Ambush策略

| 需求项 | v20要求 | 当前状态 | 差距 |
|--------|---------|----------|------|
| AmbushAdapter | 首板→潜伏策略 | ✅ `adapters.py` 已实现 | 无 |
| **DuckDB数据层** | 30天历史数据查询 | ⚠️ 代码存在但未集成 | **P0缺失** |
| 数据完整性校验 | 240根K线校验 | ❌ 未实现 | **P0缺失** |
| 断点续传机制 | checkpoint记录 | ❌ 未实现 | **P1缺失** |
| Ambush因子计算 | volume_ratio, bb_width等 | ⚠️ 简化版实现 | 需完善 |
| AI分析服务 | DeepSeek Agent | ✅ `reviewer.py` 已实现 | 无 |

**关键发现**:
- ✅ `DuckDBManager` 已存在 (`duckdb_manager.py`)
- ✅ `DataManager` 支持DuckDB查询
- ⚠️ **但 `AmbushAdapter._evaluate_ambush()` 未使用DuckDB**
- ⚠️ **当前使用简化评估，未真正调用 `AmbushStrategy`**

**代码证据**:
```python
# adapters.py 第359-408行：简化的潜伏评估
def _evaluate_ambush(self, candidate_data: Dict, score_result: ScoringResult) -> tuple:
    # 评估潜伏策略条件（简化版，无历史数据时）
    # ⚠️ 未真正调用 AmbushStrategy
    # ⚠️ 未使用DuckDB历史数据
```

---

### Phase 3: 基础设施 ⚠️ **40% 完成**

| 需求项 | v20要求 | 当前状态 | 差距 |
|--------|---------|----------|------|
| SignalPipeline | 统一处理流程 | ✅ `pipeline.py` 已实现 | 无 |
| **DuckDB数据湖** | 30天历史存储 | ⚠️ 代码存在但未搭建 | **P0缺失** |
| 断点续传 | checkpoint记录 | ❌ 未实现 | **P1缺失** |
| 每日备份 | Parquet备份 | ❌ 未实现 | **P2缺失** |
| 风控规则表 | 4条核心规则 | ✅ `RiskManager` 已有 | 无 |
| **数据质量校验** | 240根K线完整性 | ❌ 未实现 | **P0缺失** |

**关键发现**:
- ✅ `DuckDBManager` 已实现完整功能
- ✅ 支持Parquet存储、查询、备份
- ⚠️ **但未初始化数据目录结构**
- ⚠️ **未实现定时任务同步数据**
- ⚠️ **未实现数据质量校验器**

---

### Phase 4: AI + 可观测性 ✅ **90% 完成**

| 需求项 | v20要求 | 当前状态 | 差距 |
|--------|---------|----------|------|
| DeepSeek复核 | Top50→Top5 | ✅ `reviewer.py` 已实现 | 无 |
| AI重试机制 | 指数退避 | ✅ 已实现 | 无 |
| 统计追踪 | 胜率统计 | ✅ SQLite版已实现 | 无 |
| 性能监控 | SLA<5秒 | ✅ `monitor.py` 已实现 | 无 |
| 告警系统 | 延迟超标告警 | ✅ `AlertConfig` 已实现 | 无 |

**结论**: Phase 4 基本完成，仅需生产环境验证。

---

## 🔴 P0 关键缺失（必须修复）

### 1. 分钟线数据源集成 ⚠️

**问题**: `IgnitionAdapter` 未真正使用分钟线数据

**影响**: Ignition策略无法精确评估，只能使用简化评分

**现状**:
- ✅ `TushareClient.get_minute_data()` 已实现
- ✅ `DataManager.get_minute()` 已实现
- ❌ `IgnitionAdapter._evaluate_ignition()` 未调用

**修复方案**:
```python
# adapters.py 需要修改
def _evaluate_ignition(self, stock_data: Dict, score_result: ScoringResult) -> tuple:
    # 1. 获取分钟线数据
    from ..data.manager import DataManager
    dm = DataManager()
    minute_df = dm.get_minute(stock_data['code'], days=1, freq='1min')
    
    # 2. 转换为IgnitionStrategy输入格式
    # 3. 调用真正的IgnitionStrategy
    signal = self.ignition.generate_signal(minute_df)
    
    # 4. 返回真实评分
    return signal.confidence * 100, signal is not None, signal.reason
```

**工作量**: 2天

---

### 2. DuckDB数据湖搭建 ⚠️

**问题**: DuckDB未初始化，Ambush策略无法读取30天历史

**影响**: Ambush策略无法计算真实因子（volume_ratio, bb_width, obv_divergence）

**现状**:
- ✅ `DuckDBManager` 已实现
- ✅ 支持保存和查询
- ❌ 未初始化数据目录
- ❌ 未实现定时同步任务

**修复方案**:
```python
# 需要创建初始化脚本
# scripts/init_duckdb.py
from signal_api.core.quant.data.duckdb_manager import DuckDBManager

dm = DuckDBManager(data_root="./quant_data")
dm.initialize()  # 创建目录结构

# 需要创建定时同步任务
# services/signal-api/signal_api/core/quant/data/sync_task.py
async def sync_daily_data():
    """每日16:30后同步分钟线数据"""
    dm = DataManager()
    # 1. 从Tushare拉取今日分钟线
    # 2. 保存到DuckDB
    # 3. 验证数据完整性（240根K线）
```

**工作量**: 2天

---

### 3. 数据质量校验 ⚠️

**问题**: 未实现240根K线完整性检查

**影响**: 可能产生错误信号，数据不一致

**现状**:
- ❌ 未实现数据质量校验器
- ❌ 未实现断点续传

**修复方案**:
```python
# services/signal-api/signal_api/core/quant/data/validator.py
class DataQualityValidator:
    """数据质量校验器"""
    
    def validate_daily_completeness(self, df: pd.DataFrame, date: str) -> bool:
        """验证每日240根K线完整性"""
        daily_bars = df[df['datetime'].dt.date == date]
        return len(daily_bars) >= 240
    
    def validate_minute_data(self, symbol: str, date: str) -> QualityResult:
        """验证分钟线数据质量"""
        # 1. 检查数量（240根）
        # 2. 检查时间连续性
        # 3. 检查价格合理性
        # 4. 返回质量报告
```

**工作量**: 1天

---

## 🟡 P1 重要缺失（建议修复）

### 4. WebSocket推送集成 ⚠️

**问题**: WebSocket代码存在但未集成到融合流程

**影响**: 信号无法实时推送到前端

**现状**:
- ✅ `quant.py` 已有WebSocket路由 (`/quant/signals`)
- ✅ 前端已有 `useQuantWebSocket` hook
- ❌ `SignalPipeline` 未调用 `broadcast_signal()`

**修复方案**:
```python
# pipeline.py 需要修改
def _process_radar_single(self, stock: Dict) -> SignalResult:
    # ... 现有处理逻辑 ...
    
    # 5. 通过WebSocket推送
    if result.status == SignalStatus.PASSED:
        from ..routers.quant import broadcast_signal
        await broadcast_signal({
            "code": result.code,
            "unified_score": result.unified_score,
            "action": result.action,
            # ...
        })
    
    return result
```

**工作量**: 1天

---

### 5. 断点续传机制 ⚠️

**问题**: 未实现checkpoint记录，数据同步可能中断

**影响**: 数据同步失败后无法自动恢复

**现状**:
- ✅ `TushareClient` 支持checkpoint
- ❌ 未实现checkpoint持久化
- ❌ 未实现自动补录

**修复方案**:
```python
# services/signal-api/signal_api/core/quant/data/checkpoint.py
class CheckpointManager:
    """断点续传管理器"""
    
    def save_checkpoint(self, symbol: str, date: str, status: str):
        """保存同步进度"""
        # 保存到SQLite或JSON
    
    def get_missing_dates(self, symbol: str, start_date: str, end_date: str) -> List[str]:
        """获取缺失日期列表"""
        # 对比checkpoint和日期范围
        # 返回需要补录的日期
```

**工作量**: 1天

---

### 6. 前端评分详情UI ⚠️

**问题**: 前端未显示5维分项得分

**影响**: 用户无法看到评分依据

**现状**:
- ✅ 后端已返回分项得分
- ❌ 前端未显示

**修复方案**:
```typescript
// RealtimeLimitUpPredictor.tsx
// 添加评分详情展开/收起
<div className="score-details">
  <div>涨幅异动: {score.change_score}</div>
  <div>换手活跃: {score.turnover_score}</div>
  <div>成交规模: {score.volume_score}</div>
  <div>形态强势: {score.shape_score}</div>
  <div>量价配合: {score.combo_score}</div>
</div>
```

**工作量**: 1天

---

## 🟢 P2 可选改进

### 7. Parquet备份 ⚠️

**问题**: 未实现每日备份策略

**影响**: 数据无法恢复

**工作量**: 1天

### 8. 用户行为分析 ⚠️

**问题**: 未实现用户行为追踪

**影响**: 无法优化用户体验

**工作量**: 后续迭代

---

## 📅 下一步计划（3周）

### Week 1: 数据源集成 (P0) - 4天

**目标**: 激活Ignition和Ambush策略的真实计算能力

#### Day 1-2: Tushare分钟线集成

**任务清单**:
- [ ] 修改 `IgnitionAdapter._evaluate_ignition()`
  - [ ] 集成 `DataManager.get_minute()`
  - [ ] 转换为 `IgnitionStrategy` 输入格式
  - [ ] 调用真正的 `IgnitionStrategy.generate_signal()`
  - [ ] 返回真实评分和信号
- [ ] 测试验证
  - [ ] 单元测试：分钟线数据转换
  - [ ] 集成测试：完整点火流程
  - [ ] 性能测试：延迟<5秒

**验收标准**:
- ✅ Ignition策略能使用真实分钟线数据
- ✅ 信号延迟 < 5秒
- ✅ 评分准确性提升

#### Day 3-4: DuckDB数据湖搭建

**任务清单**:
- [ ] 创建初始化脚本
  - [ ] `scripts/init_duckdb.py` - 初始化数据目录
  - [ ] 创建 `quant_data/` 目录结构
  - [ ] 初始化SQLite元数据库
- [ ] 创建定时同步任务
  - [ ] `services/signal-api/signal_api/core/quant/data/sync_task.py`
  - [ ] 每日16:30后同步分钟线数据
  - [ ] 保存到DuckDB
- [ ] 修改 `AmbushAdapter._evaluate_ambush()`
  - [ ] 集成 `DataManager.get_daily()` (30天)
  - [ ] 转换为 `AmbushStrategy` 输入格式
  - [ ] 调用真正的 `AmbushStrategy.calculate_factors()`
  - [ ] 返回真实因子和评分
- [ ] 测试验证
  - [ ] 单元测试：DuckDB查询
  - [ ] 集成测试：完整潜伏流程
  - [ ] 数据完整性测试

**验收标准**:
- ✅ DuckDB数据湖正常初始化
- ✅ 定时同步任务正常运行
- ✅ Ambush策略能使用真实30天历史数据
- ✅ 因子计算准确

---

### Week 2: 数据质量与WebSocket (P1) - 3天

#### Day 5: 数据质量校验

**任务清单**:
- [ ] 创建数据质量校验器
  - [ ] `services/signal-api/signal_api/core/quant/data/validator.py`
  - [ ] 实现240根K线完整性检查
  - [ ] 实现时间连续性检查
  - [ ] 实现价格合理性检查
- [ ] 集成到同步任务
  - [ ] 同步后自动校验
  - [ ] 校验失败自动告警
  - [ ] 记录校验日志
- [ ] 测试验证
  - [ ] 单元测试：各种异常情况
  - [ ] 集成测试：完整校验流程

**验收标准**:
- ✅ 数据质量校验器正常工作
- ✅ 校验失败能正确告警
- ✅ 数据完整性 > 95%

#### Day 6: WebSocket推送集成

**任务清单**:
- [ ] 修改 `SignalPipeline`
  - [ ] 在 `_process_radar_single()` 中调用 `broadcast_signal()`
  - [ ] 在 `_process_tomorrow_single()` 中调用 `broadcast_signal()`
  - [ ] 处理推送异常
- [ ] 前端集成验证
  - [ ] 确认 `useQuantWebSocket` 能接收信号
  - [ ] 测试实时推送延迟
- [ ] 测试验证
  - [ ] 单元测试：推送逻辑
  - [ ] 集成测试：端到端推送
  - [ ] 性能测试：并发推送

**验收标准**:
- ✅ 信号能实时推送到前端
- ✅ 推送延迟 < 1秒
- ✅ 前端能正确显示信号

#### Day 7: 断点续传机制

**任务清单**:
- [ ] 创建Checkpoint管理器
  - [ ] `services/signal-api/signal_api/core/quant/data/checkpoint.py`
  - [ ] 实现checkpoint保存/加载
  - [ ] 实现缺失日期检测
- [ ] 集成到同步任务
  - [ ] 同步前检查checkpoint
  - [ ] 同步后更新checkpoint
  - [ ] 自动补录缺失数据
- [ ] 测试验证
  - [ ] 单元测试：checkpoint逻辑
  - [ ] 集成测试：断点续传流程

**验收标准**:
- ✅ 断点续传功能正常
- ✅ 能自动补录缺失数据
- ✅ 数据同步完整性 > 99%

---

### Week 3: 前端增强与集成测试 (P1/P2) - 3天

#### Day 8: 前端评分详情UI

**任务清单**:
- [ ] 修改 `RealtimeLimitUpPredictor.tsx`
  - [ ] 添加评分详情展开/收起
  - [ ] 显示5维分项得分
  - [ ] 添加评分雷达图（可选）
- [ ] 修改 `TomorrowSecondBoardCandidates.tsx`
  - [ ] 添加评分详情显示
  - [ ] 显示各维度得分
- [ ] 测试验证
  - [ ] UI测试：显示正确
  - [ ] 交互测试：展开/收起流畅

**验收标准**:
- ✅ 前端能显示5维分项得分
- ✅ UI交互流畅
- ✅ 样式统一

#### Day 9-10: 端到端测试

**任务清单**:
- [ ] 完整信号流程测试
  - [ ] 盯盘雷达 → Ignition → 评分 → 风控 → 推送
  - [ ] 明日潜力 → Ambush → 评分 → AI → 保存
- [ ] 性能压力测试
  - [ ] 100只股票批量处理
  - [ ] 并发WebSocket连接
  - [ ] 内存使用情况
- [ ] SLA达标验证
  - [ ] 信号延迟 < 5秒
  - [ ] 数据同步延迟 < 10分钟
  - [ ] 系统可用性 > 99%

**验收标准**:
- ✅ 所有端到端测试通过
- ✅ 性能指标达标
- ✅ SLA达标

---

## 📋 优先级建议

| 优先级 | 任务 | 工作量 | 收益 | 风险 |
|--------|------|--------|------|------|
| **P0** | Tushare分钟线集成 | 2天 | 激活Ignition策略 | 低 |
| **P0** | DuckDB数据湖搭建 | 2天 | 激活Ambush策略 | 低 |
| **P0** | 数据质量校验 | 1天 | 数据可靠性 | 低 |
| **P1** | WebSocket推送集成 | 1天 | 实时信号体验 | 低 |
| **P1** | 断点续传机制 | 1天 | 数据同步可靠性 | 中 |
| **P1** | 前端评分详情UI | 1天 | 用户体验 | 低 |
| **P2** | Parquet备份 | 1天 | 数据恢复能力 | 低 |

**总工作量**: 约10个工作日（2周）

---

## ⚠️ 关键依赖

### TUSHARE_TOKEN

**状态**: ❓ 未确认是否已配置

**检查命令**:
```bash
echo $TUSHARE_TOKEN
```

**如未配置**:
1. 在 [Tushare](https://tushare.pro) 注册获取Token
2. 配置到环境变量或 `.env` 文件

### 数据目录权限

**需要确认**:
- `quant_data/` 目录写入权限
- `backup/` 目录写入权限

---

## 📊 预期成果

### Week 1 结束后

- ✅ Ignition策略使用真实分钟线数据
- ✅ Ambush策略使用真实30天历史数据
- ✅ 数据湖正常运转

### Week 2 结束后

- ✅ 数据质量保障机制完善
- ✅ 实时信号推送正常
- ✅ 断点续传功能正常

### Week 3 结束后

- ✅ 前端用户体验提升
- ✅ 系统性能达标
- ✅ 端到端测试通过

---

## 🎯 成功标准

### 技术指标

- ✅ 信号延迟 < 5秒
- ✅ 数据完整性 > 95%
- ✅ 系统可用性 > 99%
- ✅ 数据同步延迟 < 10分钟

### 功能指标

- ✅ Ignition策略真实计算
- ✅ Ambush策略真实计算
- ✅ 实时信号推送
- ✅ 数据质量保障

---

**下一步**: 请确认TUSHARE_TOKEN配置，然后开始Week 1任务。

