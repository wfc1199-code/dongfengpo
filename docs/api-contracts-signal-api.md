# API Contracts – signal-api

声明前缀（router）：
- `/api/stocks`
- `/api/anomaly`
- `/api/config`
- `/api/limit-up`
- `/api/options`
- `/signals`
- `/opportunities`

## Stocks
- `GET /api/stocks/search` — 本地快照+东财搜索
- `GET /api/stocks/{stock_code}/realtime` — 实时行情
- `GET /api/stocks/{stock_code}/minute` — 分钟线
- `GET /api/stocks/{stock_code}/timeshare` — 分时
- `GET /api/stocks/{stock_code}/kline` — K 线
- `GET /api/stocks/{stock_code}/transactions` — 逐笔
- `GET /api/stocks/{stock_code}/behavior/analysis` — 行为分析

## Anomaly
- `GET /api/anomaly/hot-sectors` — 热门板块
- `GET /api/anomaly/sector-stocks/{sector_name}` — 板块成份股
- `GET /api/anomaly/market-anomaly/scan` — 市场异动扫描

## Config
- `GET /api/config/favorites` — 查询自选
- `POST /api/config/favorites` — 添加自选
- `DELETE /api/config/favorites/{stock_code}` — 删除自选
- `GET /api/config` — 读取配置
- `GET /api/config/system/monitoring-stocks` — 系统监控标的

## Limit-Up
- `GET /api/limit-up/predictions` — 涨停池/连板数
- `GET /api/limit-up/second-board-candidates` — 二板候选
- `GET /api/limit-up/realtime-predictions` — 实时预测

## Options
- `GET /api/options/search` — 期权搜索（存根，返回空）

## Signals
- `GET /signals` — 列表（过滤：strategy/symbol/signal_type/min_confidence）
- `GET /signals/stats` — 信号统计
- `GET /signals/{symbol}` — 按标的查询

## Opportunities
- `GET /opportunities` — 机会列表（过滤 state）
- `GET /opportunities/{symbol}` — 机会详情


