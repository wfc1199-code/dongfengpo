# 前端API不匹配问题分析

## 问题现象
用户界面除了"今日预测"有数据外，其他模块（二板候选、连板监控、机会流、板块热度、市场扫描）都没有数据显示。

## 根本原因
前端代码调用的API端点**与后端模块化架构的实际端点不匹配**。

## 详细分析

### 1. 前端调用的API端点（不存在）

#### SmartOpportunityFeed.tsx（机会流模块）
```typescript
// ❌ 这些端点都不存在
http://localhost:9000/api/smart-selection/real-time
http://localhost:9000/api/limit-up/quick-predictions
http://localhost:9000/api/market-anomaly/latest
```

#### HotSectorsContainer.tsx（板块热度模块）
```typescript
// ❌ 通过anomalyService调用pipeline API或legacy API
pipelineFetch('/hot-sectors?limit=10&sort_by=hot_score')
// fallback to:
legacyFetch('/api/anomaly/hot-sectors?sort_by=hot_score&limit=10')
```

### 2. 后端实际可用的API端点

#### AnomalyModule (/api/anomaly/*)
- ✅ `/api/anomaly/detect` - 实时异动检测
- ✅ `/api/anomaly/scan/{scan_type}` - 市场扫描
- ❌ `/api/anomaly/hot-sectors` - **不存在**

#### LimitUpModule (/api/limit-up/*)
- ✅ `/api/limit-up/predictions` - 涨停预测（时间分层）
- ❌ `/api/limit-up/quick-predictions` - **不存在**

#### MarketScannerModule (/api/market-scanner/*)
- ✅ `/api/market-scanner/top-gainers` - 涨幅榜
- ✅ `/api/market-scanner/limit-up` - 涨停板
- ✅ `/api/market-scanner/top-volume` - 成交量榜
- ✅ `/api/market-scanner/top-turnover` - 换手率榜

### 3. 数据流分析

```
前端组件                调用的API                     后端实际端点                状态
─────────────────────────────────────────────────────────────────────────────
TimeLayered...        /api/limit-up/predictions      /api/limit-up/predictions   ✅ 匹配
TomorrowSecond...     未知                            ?                          ❓
ContinuousBoard...    未知                            ?                          ❓
SmartOpportunity...   /api/smart-selection/*         不存在                      ❌ 不匹配
                      /api/limit-up/quick-*          不存在                      ❌ 不匹配
                      /api/market-anomaly/latest     不存在                      ❌ 不匹配
HotSectors...         /api/anomaly/hot-sectors       不存在                      ❌ 不匹配
MarketScanner         未知                            /api/market-scanner/*      ❓
```

## 解决方案

### 方案A：修改前端代码适配新后端（推荐）

#### 1. 修改SmartOpportunityFeed.tsx
```typescript
// 旧代码
const smartStocksRes = await fetch('http://localhost:9000/api/smart-selection/real-time');
const limitUpRes = await fetch('http://localhost:9000/api/limit-up/quick-predictions');
const anomalyRes = await fetch('http://localhost:9000/api/market-anomaly/latest');

// 新代码 - 使用实际存在的端点
const limitUpRes = await fetch('http://localhost:9000/api/limit-up/predictions?limit=50');
const anomalyRes = await fetch('http://localhost:9000/api/anomaly/detect?scan_all=true');
const topGainersRes = await fetch('http://localhost:9000/api/market-scanner/top-gainers?limit=20');
```

#### 2. 修改anomalyService.ts
```typescript
async getHotSectors(limit: number = 10, sortBy: string = 'hot_score') {
  // 暂时使用异动检测数据作为替代
  const anomalies = await this.getAnomalies(true);
  // 或者调用市场扫描
  return legacyFetch(`/api/market-scanner/top-gainers?limit=${limit}`);
}
```

#### 3. 需要检查的其他组件
- `TomorrowSecondBoardCandidates.tsx` - 检查调用的API
- `ContinuousBoardMonitor.tsx` - 检查调用的API
- `MarketScanner.tsx` - 检查调用的API

### 方案B：在后端添加兼容端点（临时方案）

在main_modular.py中添加兼容路由：

```python
# 兼容旧路由：/api/smart-selection/real-time
@app.get("/api/smart-selection/real-time")
async def smart_selection_compat():
    """智能选股（兼容路由，重定向到市场扫描）"""
    from modules.market_scanner.module import MarketScannerModule
    scanner = next((m for m in app.state.modules if isinstance(m, MarketScannerModule)), None)
    if scanner:
        return await scanner.service.scan_market("top_gainers", 50)
    raise HTTPException(status_code=503, detail="MarketScanner模块未加载")

# 兼容旧路由：/api/limit-up/quick-predictions
@app.get("/api/limit-up/quick-predictions")
async def quick_predictions_compat():
    """快速预测（兼容路由，重定向到涨停预测）"""
    from modules.limit_up.module import LimitUpModule
    limitup = next((m for m in app.state.modules if isinstance(m, LimitUpModule)), None)
    if limitup:
        return await limitup.service.get_predictions(50)
    raise HTTPException(status_code=503, detail="LimitUp模块未加载")

# 兼容旧路由：/api/market-anomaly/latest
@app.get("/api/market-anomaly/latest")
async def market_anomaly_compat():
    """市场异动（兼容路由，重定向到异动检测）"""
    from modules.anomaly.module import AnomalyModule
    anomaly = next((m for m in app.state.modules if isinstance(m, AnomalyModule)), None)
    if anomaly:
        result = await anomaly.service.detect_anomalies(scan_all=True)
        return result
    raise HTTPException(status_code=503, detail="Anomaly模块未加载")

# 兼容旧路由：/api/anomaly/hot-sectors
@app.get("/api/anomaly/hot-sectors")
async def hot_sectors_compat(limit: int = 10, sort_by: str = "hot_score"):
    """热门板块（兼容路由，暂时返回空数据）"""
    return {
        "code": 200,
        "message": "success",
        "data": {
            "sectors": [],
            "total": 0,
            "sort_by": sort_by
        }
    }
```

## 推荐执行步骤

1. **立即**：采用方案B，在后端添加兼容端点，让前端能立即看到数据
2. **后续**：采用方案A，逐步修改前端代码适配新后端架构
3. **最终**：移除方案B的兼容代码，完全使用模块化API

## 需要检查的前端文件

```bash
grep -r "api/smart-selection" frontend/src/
grep -r "api/market-anomaly" frontend/src/
grep -r "api/limit-up/quick" frontend/src/
grep -r "hot-sectors" frontend/src/
```

## 测试验证

### 方案B实施后测试
```bash
# 1. 测试智能选股兼容端点
curl http://localhost:9000/api/smart-selection/real-time

# 2. 测试快速预测兼容端点
curl http://localhost:9000/api/limit-up/quick-predictions

# 3. 测试市场异动兼容端点
curl http://localhost:9000/api/market-anomaly/latest

# 4. 测试热门板块兼容端点
curl http://localhost:9000/api/anomaly/hot-sectors
```

## 总结

**核心问题**: 前端代码是为**旧的单体架构**编写的，调用的API端点名称与**新的模块化架构**不匹配。

**影响范围**: 除"今日预测"外的所有模块（二板候选、连板监控、机会流、板块热度、市场扫描）

**解决方式**:
- 短期：添加兼容端点（1小时工作量）
- 长期：重构前端适配新架构（4-8小时工作量）
