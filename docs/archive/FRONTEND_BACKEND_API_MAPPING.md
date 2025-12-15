# 前后端API映射表

## 前端调用的API vs 后端模块化API

### 1. 涨停预测相关

| 前端调用 | 后端实际端点 | 状态 | 需要行动 |
|---------|-------------|------|---------|
| `/api/limit-up-tracker/today` | ❌ 不存在 | 缺失 | 需要兼容端点 |
| `/api/limit-up-tracker/second-board-candidates` | ❌ 不存在 | 缺失 | 需要兼容端点 |
| `/api/time-segmented/predictions` | ✅ `/api/limit-up/predictions` | 存在 | 已有临时路由 |
| `/api/limit-up/quick-predictions` | ✅ `/api/limit-up/predictions` | 兼容 | ✅ 已添加 |

### 2. 市场扫描相关

| 前端调用 | 后端实际端点 | 状态 | 需要行动 |
|---------|-------------|------|---------|
| `/api/market-scanner/top_gainers` | ✅ `/api/market-scanner/top-gainers` | 匹配 | ✅ 完美 |
| `/api/market-scanner/top_losers` | ✅ `/api/market-scanner/top-losers` | 匹配 | ✅ 完美 |
| `/api/market-scanner/top_volume` | ✅ `/api/market-scanner/top-volume` | 匹配 | ✅ 完美 |
| `/api/market-scanner/top_turnover` | ✅ `/api/market-scanner/top-turnover` | 匹配 | ✅ 完美 |
| `/api/market-scanner/limit_up` | ✅ `/api/market-scanner/limit-up` | 匹配 | ✅ 完美 |
| `/api/market-scanner/volume_surge` | ✅ `/api/market-scanner/volume-surge` | 匹配 | ✅ 完美 |
| `/api/market-scanner/price_breakout` | ✅ `/api/market-scanner/price-breakout` | 匹配 | ✅ 完美 |
| `/api/market-scanner/reversal_signals` | ✅ `/api/market-scanner/reversal-signals` | 匹配 | ✅ 完美 |
| `/api/market-scanner/alerts` | ❌ 不存在 | 缺失 | 需要添加 |
| `/api/market-scanner/anomalies` | ❌ 不存在 | 缺失 | 可映射到异动检测 |

### 3. 连板监控相关

| 前端调用 | 后端实际端点 | 状态 | 需要行动 |
|---------|-------------|------|---------|
| `/api/eastmoney/continuous-board-history` | ❌ 不存在 | 缺失 | 需要兼容端点 |

### 4. 智能机会流相关

| 前端调用 | 后端实际端点 | 状态 | 需要行动 |
|---------|-------------|------|---------|
| `/api/smart-selection/real-time` | ✅ 兼容到market-scanner | 兼容 | ✅ 已添加 |
| `/api/market-anomaly/latest` | ✅ 兼容到anomaly/detect | 兼容 | ✅ 已添加 |

### 5. 板块热度相关

| 前端调用 | 后端实际端点 | 状态 | 需要行动 |
|---------|-------------|------|---------|
| `/api/anomaly/hot-sectors` | ✅ 兼容到market-scanner | 兼容 | ✅ 已添加 |

### 6. 股票数据相关

| 前端调用 | 后端实际端点 | 状态 | 需要行动 |
|---------|-------------|------|---------|
| `/api/stocks/{code}/realtime` | ✅ `/api/stocks/{code}/realtime` | 匹配 | ✅ 完美 |
| `/api/stocks/{code}/transactions` | ✅ `/api/transactions/{code}/details` | 映射 | 需要兼容端点 |
| `/api/stocks/{code}/behavior/analysis` | ❌ 不存在 | 缺失 | 需要添加 |

### 7. 配置相关

| 前端调用 | 后端实际端点 | 状态 | 需要行动 |
|---------|-------------|------|---------|
| `/api/config/favorites` | ✅ `/api/config/favorites` | 匹配 | ✅ 完美 |
| `/api/system/status` | ❌ 不存在 | 缺失 | 需要添加 |

### 8. 期权相关

| 前端调用 | 后端实际端点 | 状态 | 需要行动 |
|---------|-------------|------|---------|
| `/api/options/{code}/info` | ✅ `/api/options/{code}/info` | 匹配 | ✅ 完美 |

### 9. 版本管理相关

| 前端调用 | 后端实际端点 | 状态 | 需要行动 |
|---------|-------------|------|---------|
| `/api/versions/*` | ❌ 不存在 | 缺失 | 需要添加 |

## 优先级

### P0 - 立即修复（影响核心功能）
1. ✅ `/api/smart-selection/real-time` - 机会流模块
2. ✅ `/api/limit-up/quick-predictions` - 机会流模块
3. ✅ `/api/market-anomaly/latest` - 机会流模块
4. ✅ `/api/anomaly/hot-sectors` - 板块热度模块
5. ⬜ `/api/limit-up-tracker/second-board-candidates` - 二板候选模块
6. ⬜ `/api/eastmoney/continuous-board-history` - 连板监控模块

### P1 - 重要修复（影响用户体验）
7. ⬜ `/api/limit-up-tracker/today` - 涨停追踪
8. ⬜ `/api/stocks/{code}/transactions` - 成交明细（映射到transactions模块）
9. ⬜ `/api/stocks/{code}/behavior/analysis` - 行为分析

### P2 - 可选修复（锦上添花）
10. ⬜ `/api/market-scanner/alerts` - 市场预警
11. ⬜ `/api/system/status` - 系统状态
12. ⬜ `/api/versions/*` - 版本管理

## 实现计划

### 已完成 ✅
- [x] `/api/smart-selection/real-time` → MarketScannerModule
- [x] `/api/limit-up/quick-predictions` → LimitUpModule
- [x] `/api/market-anomaly/latest` → AnomalyModule
- [x] `/api/anomaly/hot-sectors` → MarketScannerModule

### 待实现（P0）
- [ ] `/api/limit-up-tracker/second-board-candidates`
- [ ] `/api/eastmoney/continuous-board-history`
- [ ] `/api/limit-up-tracker/today`
- [ ] `/api/stocks/{code}/transactions` 映射
- [ ] `/api/stocks/{code}/behavior/analysis`

### 实现方式

所有兼容端点都添加到 `backend/main_modular.py` 的"前端兼容路由"区域。
