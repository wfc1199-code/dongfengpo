# 🔍 端点检查报告

**检查时间**: 2025-12-15  
**检查方式**: 实际运行 `backend/tests/check_missing_endpoints.py`  
**目标服务器**: http://localhost:8080

---

## 📊 检查结果汇总

| 状态 | 数量 | 端点 |
|------|------|------|
| ✅ 存在 | 2 | `/api/config` (GET), `/api/config` (POST) |
| ❌ 缺失 | 7 | 见下方详细列表 |

---

## ❌ 缺失端点详情

### 🔴 高优先级（前端依赖，必须补充）

#### 1. `GET /api/market-anomaly/scan` - 市场异动扫描
- **前端使用**: `frontend/src/components/MarketAnomalyScanner.tsx:45`
- **Legacy实现**: ✅ `backend/main_modular.py:292` 已实现
- **实现复杂度**: ⭐⭐ (中等)
- **迁移来源**: `backend/main_modular.py` 第292-346行
- **建议位置**: `services/signal-api/signal_api/routers/anomaly.py`

**Legacy代码位置**:
```python
# backend/main_modular.py:292
@app.get("/api/market-anomaly/scan")
async def scan_market_anomaly(anomaly_type: str = "all", limit: int = 50):
    """市场异动扫描"""
    from modules.anomaly.service import AnomalyService
    # ... 实现代码 ...
```

#### 2. `GET /api/system/status` - 系统状态
- **前端使用**: `frontend/src/components/ManagementDashboard.tsx:45`
- **Legacy实现**: ✅ `backups/cleanup_20251002_102711/main_old.py:248` 已实现
- **实现复杂度**: ⭐ (简单)
- **迁移来源**: `backups/cleanup_20251002_102711/main_old.py` 第248-259行
- **建议位置**: `services/api-gateway/main.py` (系统级信息)

**Legacy代码位置**:
```python
# backups/cleanup_20251002_102711/main_old.py:248
@app.get("/api/system/status")
async def get_system_status():
    """获取系统状态（Legacy，建议使用 /health）"""
    return {
        "status": "running",
        "monitoring_stocks": len(dynamic_stock_codes),
        # ... 更多字段 ...
    }
```

#### 3. `GET /api/system/monitoring-stocks` - 监控股票列表
- **前端使用**: `frontend/src/components/ManagementDashboard.tsx:71`
- **Legacy实现**: ✅ `backups/cleanup_20251002_102711/main_old.py:262` 已实现
- **实现复杂度**: ⭐⭐ (中等)
- **迁移来源**: `backups/cleanup_20251002_102711/main_old.py` 第262-326行
- **建议位置**: `services/signal-api/signal_api/routers/config.py`

**Legacy代码位置**:
```python
# backups/cleanup_20251002_102711/main_old.py:262
@app.get("/api/system/monitoring-stocks")
async def get_monitoring_stocks():
    """获取当前监控的股票列表"""
    # ... 实现代码 ...
```

### 🟡 中优先级（建议补充）

#### 4. `GET /api/anomaly/strong-stocks` - 强势股票列表
- **Legacy实现**: ✅ `backups/cleanup_20251002_102711/main_old.py:1734` 已实现
- **实现复杂度**: ⭐⭐⭐ (较复杂)
- **建议**: 检查是否已合并到其他端点

#### 5. `GET /api/limit-up/tracking` - 涨停追踪
- **Legacy实现**: ❓ 未找到
- **实现复杂度**: ⭐⭐ (中等)
- **建议**: 检查是否已合并到 `limit-up/predictions`

#### 6. `GET /api/market-anomaly/latest` - 最新市场异动
- **Legacy实现**: ✅ `backups/cleanup_20251002_102711/main_old.py:2575` 已实现
- **实现复杂度**: ⭐⭐ (中等)
- **建议**: 检查是否已合并到 `anomaly/detect`

### 🟢 低优先级（可选）

#### 7. `POST /api/alert` - 预警管理
- **Legacy实现**: ✅ `backups/cleanup_20251002_102711/main_old.py:1707` 已实现
- **实现复杂度**: ⭐ (简单)
- **建议**: 检查是否已废弃或整合到其他功能

---

## ✅ 已存在的端点

1. `GET /api/config` - 获取配置 ✅
2. `POST /api/config` - 更新配置 ✅ (HTTP 405，需要添加POST方法)

---

## 🎯 迁移建议

### 立即迁移（高优先级）

1. **`/api/market-anomaly/scan`**
   - 从 `backend/main_modular.py:292` 迁移
   - 目标: `services/signal-api/signal_api/routers/anomaly.py`
   - 需要适配: 使用BMAD的数据源和服务

2. **`/api/system/status`**
   - 从 `backups/cleanup_20251002_102711/main_old.py:248` 迁移
   - 目标: `services/api-gateway/main.py`
   - 需要适配: 返回各微服务健康状态

3. **`/api/system/monitoring-stocks`**
   - 从 `backups/cleanup_20251002_102711/main_old.py:262` 迁移
   - 目标: `services/signal-api/signal_api/routers/config.py`
   - 需要适配: 使用BMAD的配置和数据源

### 评估迁移（中低优先级）

- 先检查是否已合并到其他端点
- 如未合并，再决定是否迁移

---

## 📝 下一步行动

1. ✅ **已完成**: 端点检查
2. ⏭️ **下一步**: 迁移3个高优先级端点
3. ⏭️ **然后**: 运行测试验证
4. ⏭️ **最后**: 更新API Gateway路由配置

---

**检查完成时间**: 2025-12-15  
**检查状态**: ✅ 完成

