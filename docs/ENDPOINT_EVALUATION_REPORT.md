# 🔍 中低优先级端点评估报告

**评估日期**: 2025-12-15  
**评估范围**: 4个中低优先级端点  
**评估目标**: 确定是否需要补充或可以废弃

---

## 📊 评估结果汇总

| 端点 | 前端使用 | 功能合并 | 建议 | 优先级 |
|------|---------|---------|------|--------|
| `/api/anomaly/strong-stocks` | ⚠️ 间接使用 | ❓ 待检查 | 🟡 建议补充 | 🟡 中 |
| `/api/limit-up/tracking` | ❌ 未使用 | ❓ 待检查 | 🟢 可废弃 | 🟡 中 |
| `/api/market-anomaly/latest` | ❌ 未使用 | ❓ 待检查 | 🟢 可废弃 | 🟡 中 |
| `/api/alert` (POST) | ❌ 未使用 | ❓ 待检查 | 🟢 可废弃 | 🟢 低 |

---

## 🔍 详细评估

### 1. `/api/anomaly/strong-stocks` - 强势股票列表

**Legacy实现**: `backups/cleanup_20251002_102711/main_old.py:1734`

**前端使用情况**:
- ✅ **间接使用**: `frontend/src/components/SectorFlow.tsx` 中有 `strongStocks` 字段
- ⚠️ **注意**: 前端使用 `strongStocks` 作为数据字段，但未直接调用 `/api/anomaly/strong-stocks` 端点
- 📝 **数据来源**: 可能从其他端点（如 `anomaly/detect`）获取数据后计算得出

**功能分析**:
- 功能: 获取强势股排行榜（多维度评分：涨幅、换手率、成交额、形态等）
- 实现复杂度: ⭐⭐⭐ (较复杂，约200行代码)
- 可能合并到: `anomaly/detect` 或 `market-anomaly/scan`

**评估决策**:
- ⚠️ **间接使用** → 🟡 **建议补充**（中优先级）
- 理由: 虽然前端未直接调用，但功能有价值，可能被其他组件间接使用

**建议**: 
- 如果 `SectorFlow` 组件需要强势股数据，建议补充
- 或者确认数据可以从其他端点获取

---

### 2. `/api/limit-up/tracking` - 涨停追踪

**Legacy实现**: ❌ **未找到**（可能从未实现或已删除）

**前端使用情况**:
- ❌ **未使用**: 前端代码中未找到任何引用

**功能分析**:
- 功能: 涨停追踪（可能已合并到 `limit-up/predictions`）
- 实现复杂度: ⭐⭐ (中等)
- 可能合并到: `limit-up/predictions` 或 `limit-up/realtime-predictions`

**评估决策**:
- ✅ **未使用且未实现** → 🟢 **可废弃**（低优先级）

**建议**: 
- ✅ **可以废弃** - 前端未使用，Legacy版本中也未找到实现
- 功能可能已整合到 `limit-up/predictions` 中

---

### 3. `/api/market-anomaly/latest` - 最新市场异动

**Legacy实现**: `backups/cleanup_20251002_102711/main_old.py:2575`

**前端使用情况**:
- ❌ **未使用**: 前端代码中未找到任何引用

**功能分析**:
- 功能: 获取最新市场异动（快速拉升、放量突破等）
- 实现复杂度: ⭐⭐ (中等，约45行代码)
- 可能合并到: `anomaly/detect` 或 `market-anomaly/scan`

**功能对比**:
- `market-anomaly/scan`: 返回异动股票列表和统计
- `market-anomaly/latest`: 返回最新异动（快速拉升、放量突破）
- **结论**: 功能已合并到 `market-anomaly/scan` ✅

**评估决策**:
- ✅ **功能已合并** → 🟢 **可废弃**

**建议**: 
- ✅ **可以废弃** - 功能已合并到 `market-anomaly/scan`
- `market-anomaly/scan` 已提供更完整的异动数据

---

### 4. `/api/alert` (POST) - 预警管理

**Legacy实现**: `backups/cleanup_20251002_102711/main_old.py:1707`

**前端使用情况**:
- ❌ **未使用**: 前端代码中未找到 `/api/alert` 的调用
- ⚠️ **注意**: 前端有 `AlertPanel.tsx` 组件，但调用的是 `/api/market-scanner/alerts`，不是 `/api/alert`
- 📝 **数据来源**: 前端使用 `backend.service.ts` 中的 `getAlerts()` 和 `scanAlerts()`，但这些调用不同的端点

**功能分析**:
- 功能: 发送预警消息（通过WebSocket广播）
- 实现复杂度: ⭐ (简单，约25行代码)
- 可能整合到: WebSocket推送功能或 Signal Streamer

**评估决策**:
- ✅ **未使用且功能可替代** → 🟢 **可废弃**（低优先级）

**建议**: 
- ✅ **可以废弃** - 前端未使用，功能可通过WebSocket推送实现
- 如果需要预警功能，可以通过 Signal Streamer 的 WebSocket 推送

---

## 🎯 评估决策树

```
端点X
├─ 前端使用？
│  ├─ 是 → 🔴 必须补充 (优先级：高)
│  └─ 否 → 继续评估
│
├─ 功能已合并？
│  ├─ 是 → ✅ 标记为废弃
│  └─ 否 → 继续评估
│
└─ 核心业务功能？
   ├─ 是 → 🟡 建议补充 (优先级：中)
   └─ 否 → 🟢 可废弃 (优先级：低)
```

---

## 📝 评估结果

### 待执行评估

1. **前端代码搜索** - 检查前端是否调用这些端点
2. **功能对比** - 检查是否已合并到其他端点
3. **业务价值** - 评估是否为核心业务功能

---

**报告生成时间**: 2025-12-15  
**评估状态**: ⏳ 进行中

