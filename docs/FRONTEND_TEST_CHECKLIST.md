# 🧪 前端功能测试清单

**测试日期**: 2025-12-15  
**测试范围**: 3个已迁移端点对应的前端组件  
**测试目标**: 确认前端功能正常工作，用户体验无影响

---

## 📋 测试前准备

### 1. 启动服务

```bash
# 确认后端服务运行
curl http://localhost:8080/gateway/health
curl http://localhost:9001/health

# 启动前端（如果未启动）
cd frontend
npm start
```

### 2. 打开浏览器

访问: http://localhost:3000

---

## 🧪 测试项目

### 测试1: MarketAnomalyScanner 组件

**对应端点**: `GET /api/market-anomaly/scan`

**测试步骤**:
1. [ ] 打开包含 MarketAnomalyScanner 的页面
2. [ ] 检查组件是否正常渲染
3. [ ] 检查是否显示异动股票列表
4. [ ] 检查统计数据是否显示（极强、强势、活跃数量）
5. [ ] 检查筛选功能是否正常（异动类型、限制数量）
6. [ ] 检查自动刷新是否正常
7. [ ] 打开浏览器 Console，检查是否有错误

**预期结果**:
- ✅ 组件正常显示
- ✅ 数据正常加载
- ✅ 无 Console 错误
- ✅ 数据格式正确

**检查点**:
- [ ] 股票列表不为空
- [ ] 异动级别颜色正确显示
- [ ] 异动分数正确显示
- [ ] 统计数据正确

---

### 测试2: ManagementDashboard - 系统状态

**对应端点**: `GET /api/system/status`

**测试步骤**:
1. [ ] 打开 ManagementDashboard 页面
2. [ ] 切换到"系统状态"或"概览"标签
3. [ ] 检查系统状态是否显示
4. [ ] 检查各服务健康状态是否显示
5. [ ] 检查时间戳是否更新
6. [ ] 打开浏览器 Console，检查是否有错误

**预期结果**:
- ✅ 系统状态正常显示
- ✅ 服务健康状态正确
- ✅ 无 Console 错误

**检查点**:
- [ ] 状态显示为 "running" 或 "degraded"（部分服务未启动正常）
- [ ] 各服务状态正确显示
- [ ] 时间戳格式正确

---

### 测试3: ManagementDashboard - 监控股票列表

**对应端点**: `GET /api/system/monitoring-stocks`

**测试步骤**:
1. [ ] 在 ManagementDashboard 中找到"监控股票"部分
2. [ ] 检查用户自选股列表是否显示
3. [ ] 检查热门板块股票列表是否显示
4. [ ] 检查股票数量统计是否正确
5. [ ] 检查股票实时数据是否显示（价格、涨跌幅）
6. [ ] 打开浏览器 Console，检查是否有错误

**预期结果**:
- ✅ 监控股票列表正常显示
- ✅ 数据正常加载
- ✅ 无 Console 错误

**检查点**:
- [ ] 用户自选股列表显示（如果有）
- [ ] 热门板块股票列表显示
- [ ] 股票数量统计正确
- [ ] 实时数据格式正确

---

## 🔍 Console 错误检查

### 检查步骤

1. [ ] 打开浏览器开发者工具 (F12)
2. [ ] 切换到 Console 标签
3. [ ] 刷新页面
4. [ ] 检查是否有红色错误信息
5. [ ] 检查是否有黄色警告信息（非关键）

### 常见错误类型

- ❌ `404 Not Found` - 端点不存在
- ❌ `Network Error` - 网络连接问题
- ❌ `TypeError: Cannot read properties` - 数据格式问题
- ❌ `CORS Error` - 跨域问题

---

## 📊 数据格式验证

### MarketAnomalyScanner 数据格式

**期望格式**:
```json
{
  "status": "success",
  "stocks": [
    {
      "code": "000001",
      "name": "股票名称",
      "price": 10.5,
      "change_percent": 5.2,
      "anomaly_score": 80,
      "anomaly_level": "极强",
      "level_color": "#ff4444",
      "anomaly_reasons": ["原因1", "原因2"]
    }
  ],
  "stats": {
    "total_count": 10,
    "extreme_strong": 2,
    "strong": 3,
    "active": 5
  }
}
```

### ManagementDashboard - 系统状态数据格式

**期望格式**:
```json
{
  "status": "running",
  "monitoring_stocks": 0,
  "connected_clients": 0,
  "anomaly_engine_initialized": true,
  "data_manager_initialized": true,
  "services": {
    "signal-api": {
      "status": "healthy",
      "response_time_ms": 2.3
    }
  },
  "timestamp": "2025-12-15T08:30:00"
}
```

### ManagementDashboard - 监控股票数据格式

**期望格式**:
```json
{
  "total_monitoring": 35,
  "user_favorites_count": 5,
  "hot_sector_stocks_count": 30,
  "user_favorites": [
    {
      "code": "000001",
      "name": "股票名称",
      "current_price": 10.5,
      "change_percent": 2.3,
      "source": "favorite"
    }
  ],
  "hot_sector_stocks": [
    {
      "code": "BK1121",
      "name": "板块名称",
      "current_price": 1859.34,
      "change_percent": 6.78,
      "source": "hot_sector"
    }
  ],
  "timestamp": "2025-12-15T08:30:00"
}
```

---

## ✅ 测试通过标准

### 必须通过（否则不能删除旧版本）

- [ ] 所有3个组件正常显示
- [ ] 所有3个端点返回数据
- [ ] 无 Console 错误
- [ ] 数据格式正确

### 建议通过（影响用户体验）

- [ ] 数据刷新正常
- [ ] 交互功能正常
- [ ] 样式显示正常

---

## 📝 测试记录模板

```
测试时间: 2025-12-15 XX:XX
测试人员: [你的名字]

测试结果:
- MarketAnomalyScanner: ✅/❌
- ManagementDashboard - 系统状态: ✅/❌
- ManagementDashboard - 监控股票: ✅/❌

Console 错误: [记录任何错误]

备注: [其他发现的问题]
```

---

**创建时间**: 2025-12-15  
**测试状态**: 📋 待执行

