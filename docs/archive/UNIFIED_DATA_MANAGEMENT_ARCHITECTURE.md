# 统一数据管理架构方案

## 📋 问题根源分析

### 当前问题
您遇到的"今日预测模块又没有数据"问题是系统性的,根本原因:

1. **数据源分散**: 各模块独立调用AkShare/TuShare,没有统一管理
2. **API不稳定**: AkShare API频繁超时,缺少降级策略
3. **缺少缓存**: 重复调用相同API,浪费资源且不稳定
4. **数据验证缺失**: 没有检查数据是否有效(空数据、过期数据)
5. **前后端不匹配**: 前端调用的API在代码清理时被删除

### 具体表现
```
❌ 今日预测: 调用 /api/time-segmented/predictions → 404 (API已删除)
❌ 市场捕获: 调用 /api/capture/* → 404 (API已删除)
⚠️  板块热度: AkShare板块API超时 → 降级到热门股票聚合
✅ 涨停预测: /api/limit-up/predictions → 有数据(但可能不稳定)
```

---

## 🎯 统一数据管理架构

### 整体设计

```
┌─────────────────────────────────────────────────────────┐
│                    前端组件层                             │
│  今日预测 │ 板块热度 │ 市场扫描 │ 二板候选 │ 机会流      │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│              统一数据服务层 (Data Service Layer)          │
│                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │  涨停预测   │  │  板块热度   │  │  市场扫描   │      │
│  │   Service   │  │   Service   │  │   Service   │      │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘      │
│         │                 │                 │              │
│         └─────────────────┼─────────────────┘              │
│                           │                                │
└───────────────────────────┼────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────┐
│              统一数据源管理器 (Unified Data Source)         │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  缓存层      │  │  降级策略    │  │  数据验证    │    │
│  │  Redis/内存  │  │  3层fallback │  │  完整性检查  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  重试机制    │  │  健康检查    │  │  数据刷新    │    │
│  │  指数退避    │  │  API可用性   │  │  自动更新    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└───────────────────────────┬────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────┐
│                   外部数据源                                 │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐           │
│  │AkShare │  │TuShare │  │东方财富│  │新浪财经│           │
│  │ 主力   │  │ 备用   │  │ 补充   │  │ 补充   │           │
│  └────────┘  └────────┘  └────────┘  └────────┘           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏗️ 实施方案

### 第一阶段: 统一数据源管理器 (本周)

#### 1. 创建UnifiedDataSource基类

**文件**: `backend/core/unified_data_source.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)

class DataSourceStatus:
    """数据源状态"""
    def __init__(self):
        self.is_healthy = True
        self.last_success = None
        self.last_error = None
        self.error_count = 0
        self.total_requests = 0
        self.success_rate = 1.0

class UnifiedDataSource(ABC):
    """统一数据源基类"""

    def __init__(self):
        self.cache = {}  # 简单内存缓存
        self.status = DataSourceStatus()
        self.cache_ttl = 60  # 缓存60秒

    async def get_data(
        self,
        data_type: str,
        params: Dict[str, Any] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        获取数据的统一入口

        Args:
            data_type: 数据类型 (limit_up, hot_stocks, sectors等)
            params: 查询参数
            use_cache: 是否使用缓存

        Returns:
            标准化数据响应
        """
        # 1. 检查缓存
        if use_cache:
            cached = self._get_from_cache(data_type, params)
            if cached:
                logger.info(f"✅ 缓存命中: {data_type}")
                return cached

        # 2. 降级策略: 主数据源 → 备用源 → 模拟数据
        for source_name, source_func in self._get_sources(data_type):
            try:
                logger.info(f"🔍 尝试数据源: {source_name}")
                data = await self._fetch_with_retry(source_func, params)

                # 3. 数据验证
                if self._validate_data(data):
                    # 4. 更新缓存
                    self._save_to_cache(data_type, params, data)
                    # 5. 更新健康状态
                    self._update_status(success=True)
                    logger.info(f"✅ {source_name} 获取成功")
                    return data
                else:
                    logger.warning(f"⚠️  {source_name} 数据验证失败")

            except Exception as e:
                logger.warning(f"❌ {source_name} 失败: {e}")
                self._update_status(success=False, error=str(e))
                continue

        # 6. 所有数据源都失败,返回降级数据
        logger.error(f"❌ 所有数据源失败,返回降级数据: {data_type}")
        return self._get_fallback_data(data_type, params)

    async def _fetch_with_retry(
        self,
        fetch_func,
        params: Dict,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """带重试的数据获取"""
        for i in range(max_retries):
            try:
                return await fetch_func(params)
            except Exception as e:
                if i == max_retries - 1:
                    raise
                wait_time = 2 ** i  # 指数退避
                logger.warning(f"⏳ 重试 {i+1}/{max_retries}, 等待{wait_time}秒...")
                await asyncio.sleep(wait_time)

    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """数据有效性验证"""
        if not data:
            return False

        # 检查数据结构
        if 'code' not in data or data['code'] != 200:
            return False

        if 'data' not in data:
            return False

        # 检查数据不为空
        data_content = data['data']
        if isinstance(data_content, dict):
            if 'stocks' in data_content:
                return len(data_content['stocks']) > 0
            if 'sectors' in data_content:
                return len(data_content['sectors']) > 0

        return True

    def _get_from_cache(
        self,
        data_type: str,
        params: Dict
    ) -> Optional[Dict[str, Any]]:
        """从缓存获取数据"""
        cache_key = self._make_cache_key(data_type, params)
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=self.cache_ttl):
                return cached_data
        return None

    def _save_to_cache(
        self,
        data_type: str,
        params: Dict,
        data: Dict[str, Any]
    ):
        """保存到缓存"""
        cache_key = self._make_cache_key(data_type, params)
        self.cache[cache_key] = (data, datetime.now())

    def _make_cache_key(self, data_type: str, params: Dict) -> str:
        """生成缓存键"""
        import hashlib
        import json
        params_str = json.dumps(params or {}, sort_keys=True)
        return f"{data_type}:{hashlib.md5(params_str.encode()).hexdigest()}"

    def _update_status(self, success: bool, error: str = None):
        """更新数据源健康状态"""
        self.status.total_requests += 1
        if success:
            self.status.last_success = datetime.now()
            self.status.is_healthy = True
            self.status.error_count = 0
        else:
            self.status.last_error = error
            self.status.error_count += 1
            # 连续失败3次标记为不健康
            if self.status.error_count >= 3:
                self.status.is_healthy = False

        # 更新成功率
        if self.status.total_requests > 0:
            success_count = self.status.total_requests - self.status.error_count
            self.status.success_rate = success_count / self.status.total_requests

    @abstractmethod
    def _get_sources(self, data_type: str) -> List[tuple]:
        """获取数据源列表(需子类实现)"""
        pass

    @abstractmethod
    def _get_fallback_data(self, data_type: str, params: Dict) -> Dict[str, Any]:
        """获取降级数据(需子类实现)"""
        pass
```

#### 2. 实现具体数据源

**文件**: `backend/core/stock_data_source.py`

```python
from .unified_data_source import UnifiedDataSource
import akshare as ak
import asyncio

class StockDataSource(UnifiedDataSource):
    """股票数据源"""

    def __init__(self):
        super().__init__()
        self.cache_ttl = 30  # 股票数据30秒缓存

    def _get_sources(self, data_type: str) -> List[tuple]:
        """定义数据源优先级"""
        sources = {
            'limit_up': [
                ('AkShare涨停榜', self._fetch_limit_up_akshare),
                ('东方财富', self._fetch_limit_up_eastmoney),
            ],
            'hot_stocks': [
                ('AkShare热门榜', self._fetch_hot_stocks_akshare),
                ('模拟数据', self._fetch_hot_stocks_mock),
            ],
            'sectors': [
                ('AkShare板块', self._fetch_sectors_akshare),
                ('热门股票聚合', self._fetch_sectors_from_hot_stocks),
                ('模拟数据', self._fetch_sectors_mock),
            ],
        }
        return sources.get(data_type, [])

    async def _fetch_limit_up_akshare(self, params: Dict) -> Dict[str, Any]:
        """从AkShare获取涨停数据"""
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, ak.stock_zt_pool_em, params.get('date'))

        stocks = []
        for _, row in df.iterrows():
            stocks.append({
                'code': row['代码'],
                'name': row['名称'],
                'price': row['最新价'],
                'change_percent': row['涨跌幅'],
                'seal_time': row.get('封板时间', ''),
                'data_source': 'akshare'
            })

        return {
            'code': 200,
            'data': {
                'stocks': stocks,
                'count': len(stocks),
                'data_source': 'akshare'
            }
        }

    def _get_fallback_data(self, data_type: str, params: Dict) -> Dict[str, Any]:
        """降级数据"""
        return {
            'code': 200,
            'message': 'fallback data',
            'data': {
                'stocks': [],
                'count': 0,
                'data_source': 'fallback',
                'warning': '数据源暂时不可用,显示空数据'
            }
        }
```

---

### 第二阶段: 数据质量监控 (下周)

#### 1. 数据质量指标

```python
class DataQualityMetrics:
    """数据质量指标"""

    def __init__(self):
        self.metrics = {
            'completeness': 0.0,  # 完整性: 有数据的比例
            'freshness': 0.0,      # 新鲜度: 数据更新时间
            'accuracy': 0.0,       # 准确性: 数据验证通过率
            'availability': 0.0,   # 可用性: API成功率
        }

    def calculate_completeness(self, data: Dict) -> float:
        """计算数据完整性"""
        if not data or 'data' not in data:
            return 0.0

        stocks = data['data'].get('stocks', [])
        if not stocks:
            return 0.0

        # 检查关键字段完整性
        required_fields = ['code', 'name', 'price', 'change_percent']
        complete_count = 0

        for stock in stocks:
            if all(field in stock and stock[field] for field in required_fields):
                complete_count += 1

        return complete_count / len(stocks) if stocks else 0.0

    def calculate_freshness(self, data: Dict) -> float:
        """计算数据新鲜度 (0-1,越接近1越新鲜)"""
        if 'updated_at' not in data.get('data', {}):
            return 0.5  # 未知时间

        updated_at = datetime.fromisoformat(data['data']['updated_at'])
        age_seconds = (datetime.now() - updated_at).total_seconds()

        # 60秒内: 1.0, 5分钟: 0.5, 10分钟以上: 0.0
        if age_seconds < 60:
            return 1.0
        elif age_seconds < 300:
            return 1.0 - (age_seconds - 60) / 240 * 0.5
        elif age_seconds < 600:
            return 0.5 - (age_seconds - 300) / 300 * 0.5
        else:
            return 0.0
```

#### 2. 监控仪表板API

```python
@app.get("/api/monitoring/data-quality")
async def get_data_quality():
    """数据质量监控接口"""
    return {
        'limit_up': {
            'availability': 0.95,
            'completeness': 1.0,
            'freshness': 0.8,
            'last_update': '2025-10-02T14:30:00',
            'data_source': 'akshare',
            'health': 'healthy'
        },
        'sectors': {
            'availability': 0.60,
            'completeness': 0.85,
            'freshness': 0.9,
            'last_update': '2025-10-02T14:29:00',
            'data_source': 'hot_stocks_aggregation',
            'health': 'degraded'
        },
        'hot_stocks': {
            'availability': 0.90,
            'completeness': 1.0,
            'freshness': 1.0,
            'last_update': '2025-10-02T14:30:00',
            'data_source': 'akshare',
            'health': 'healthy'
        }
    }
```

---

### 第三阶段: 自动数据刷新 (下周)

#### 数据刷新调度器

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class DataRefreshScheduler:
    """数据刷新调度器"""

    def __init__(self, data_source: UnifiedDataSource):
        self.data_source = data_source
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """启动调度任务"""
        # 每30秒刷新热门股票
        self.scheduler.add_job(
            self._refresh_hot_stocks,
            'interval',
            seconds=30,
            id='refresh_hot_stocks'
        )

        # 每5分钟刷新板块数据
        self.scheduler.add_job(
            self._refresh_sectors,
            'interval',
            minutes=5,
            id='refresh_sectors'
        )

        # 交易时间内每1分钟刷新涨停数据
        self.scheduler.add_job(
            self._refresh_limit_up,
            'cron',
            hour='9-15',
            minute='*/1',
            id='refresh_limit_up'
        )

        self.scheduler.start()

    async def _refresh_hot_stocks(self):
        """刷新热门股票"""
        await self.data_source.get_data('hot_stocks', use_cache=False)

    async def _refresh_sectors(self):
        """刷新板块数据"""
        await self.data_source.get_data('sectors', use_cache=False)

    async def _refresh_limit_up(self):
        """刷新涨停数据"""
        await self.data_source.get_data('limit_up', use_cache=False)
```

---

## 🚀 立即行动: 修复今日预测

### 短期方案 (今天)

**直接将时间分层预测API迁移到LimitUpModule**:

```python
# backend/modules/limit_up/module.py

@self.router.get("/predictions/time-segmented")
async def get_time_segmented_predictions(limit: int = 100):
    """时间分层涨停预测"""
    return await self.service.get_time_segmented_predictions(limit)
```

### 前端更新

```typescript
// frontend/src/components/TimeLayeredLimitUpTracker.tsx

// 修改API调用
const response = await fetch(
  `http://localhost:9000/api/limit-up/predictions/time-segmented?limit=100`
);
```

---

## 📊 数据管理最佳实践

### 1. 统一数据格式

所有API返回统一格式:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "stocks": [...],
    "count": 10,
    "updated_at": "2025-10-02T14:30:00",
    "data_source": "akshare",
    "cache_hit": false,
    "quality_score": 0.95
  },
  "meta": {
    "api_version": "2.0",
    "request_id": "abc123",
    "processing_time": 0.5
  }
}
```

### 2. 数据源优先级

```
优先级1: AkShare (主力数据源)
优先级2: 东方财富API (备用)
优先级3: 热门股票聚合 (降级)
优先级4: 模拟数据 (兜底)
```

### 3. 缓存策略

| 数据类型 | 缓存时长 | 刷新策略 |
|---------|---------|---------|
| 实时行情 | 10秒 | 交易时间每10秒 |
| 涨停榜单 | 30秒 | 交易时间每30秒 |
| 板块热度 | 5分钟 | 每5分钟 |
| 历史数据 | 1小时 | 每小时 |

### 4. 错误处理

```python
# 统一错误响应
{
  "code": 500,
  "message": "数据获取失败",
  "error": {
    "type": "DataSourceError",
    "details": "AkShare API超时",
    "retry_after": 60,
    "fallback_available": true
  }
}
```

---

## 🎯 预期效果

实施统一数据管理后:

✅ **稳定性**: 99%+ API可用率 (多数据源降级)
✅ **实时性**: 数据延迟 < 30秒
✅ **准确性**: 数据完整性 > 95%
✅ **可维护性**: 统一管理,易于调试
✅ **可扩展性**: 新增数据源只需实现接口

---

**创建时间**: 2025-10-02
**优先级**: P0 (最高)
**状态**: 方案制定完成,待实施
