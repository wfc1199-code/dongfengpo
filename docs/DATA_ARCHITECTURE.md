# 东风破系统 - 统一数据架构设计文档

## 📊 当前问题诊断

### 1. 数据源混乱
- `data_sources.py` (DataManager) - 腾讯API + 东财API + 模拟数据
- `market_scanner.py` (MarketScanner) - 东财API独立实现
- `akshare_realtime_source.py` - AkShare库
- `tushare_direct_source.py` - Tushare库
- **问题**：各自独立，没有统一fallback机制

### 2. API连接失败
- 东方财富API：`ServerDisconnectedError` / `Connection timeout`
- 腾讯API：`ServerDisconnectedError`
- AkShare：`Connection aborted`
- **原因**：网络封锁、防火墙、ISP限流

### 3. 数据不一致
- 自选股显示：使用data_manager（真实快照数据）
- 市场扫描显示：之前使用market_scanner（错误数据）
- 涨停预测显示：使用独立的AkShare调用
- **结果**：同一股票在不同模块显示不同价格

## 🎯 重构目标

### 1. 单一数据入口 (Single Source of Truth)
```
UnifiedDataSource (统一数据源)
    ↓
所有API路由 → 所有前端组件
```

### 2. 多层Fallback机制
```
1️⃣ 腾讯实时API (首选，速度快)
    ↓ 失败
2️⃣ 东方财富API (备选，数据全)
    ↓ 失败
3️⃣ AkShare (备选，稳定性好)
    ↓ 失败
4️⃣ 本地真实数据快照 (兜底，保证可用)
```

### 3. 统一数据模型
```python
@dataclass
class StockData:
    code: str              # 股票代码
    name: str              # 股票名称
    current_price: float   # 当前价
    change: float          # 涨跌额
    change_percent: float  # 涨跌幅
    volume: int            # 成交量
    amount: float          # 成交额
    turnover_rate: float   # 换手率
    high_price: float      # 最高价
    low_price: float       # 最低价
    open_price: float      # 开盘价
    yesterday_close: float # 昨收价
    pe_ratio: float        # 市盈率
    market_cap: float      # 市值
    update_time: datetime  # 更新时间
    data_source: str       # 数据来源标识
```

## 🏗️ 新架构设计

### 核心组件

#### 1. UnifiedDataSource (backend/core/unified_data_source.py)
```python
class UnifiedDataSource:
    """统一数据源 - 系统唯一数据入口"""

    def __init__(self):
        self.tencent_source = TencentDataSource()
        self.eastmoney_source = EastMoneyDataSource()
        self.akshare_source = AkShareSource()
        self.snapshot = RealDataSnapshot()
        self.cache = DataCache()

    async def get_realtime_data(self, codes: List[str]) -> Dict[str, StockData]:
        """获取实时数据 - 多源fallback"""
        # 1. 检查缓存（1分钟内有效）
        cached = self.cache.get(codes)
        if cached:
            return cached

        # 2. 尝试腾讯API
        try:
            data = await self.tencent_source.fetch(codes)
            if data:
                self.cache.set(data)
                return data
        except Exception as e:
            logger.warning(f"腾讯API失败: {e}")

        # 3. 尝试东财API
        try:
            data = await self.eastmoney_source.fetch(codes)
            if data:
                self.cache.set(data)
                return data
        except Exception as e:
            logger.warning(f"东财API失败: {e}")

        # 4. 尝试AkShare
        try:
            data = await self.akshare_source.fetch(codes)
            if data:
                self.cache.set(data)
                return data
        except Exception as e:
            logger.warning(f"AkShare失败: {e}")

        # 5. 使用本地真实快照
        logger.warning("所有API失败，使用本地快照数据")
        return self.snapshot.get(codes)
```

#### 2. DataValidator (backend/core/data_validator.py)
```python
class DataValidator:
    """数据验证器 - 确保数据质量"""

    @staticmethod
    def validate(data: StockData) -> bool:
        """验证股票数据合理性"""
        # 价格合理性检查
        if data.current_price <= 0 or data.current_price > 10000:
            return False

        # 涨跌幅合理性检查
        if abs(data.change_percent) > 20:
            return False

        # 换手率合理性检查
        if data.turnover_rate < 0 or data.turnover_rate > 100:
            return False

        # 名称不能为空
        if not data.name or data.name.startswith('股票'):
            return False

        return True
```

#### 3. RealDataSnapshot (backend/core/real_data_snapshot.py)
```python
class RealDataSnapshot:
    """真实数据快照管理器"""

    def __init__(self):
        self.snapshot_file = Path("data/stock_snapshot.json")
        self.load_snapshot()

    def load_snapshot(self):
        """从文件加载快照"""
        if self.snapshot_file.exists():
            with open(self.snapshot_file, 'r') as f:
                self.data = json.load(f)
        else:
            self.data = self._default_snapshot()

    def update_snapshot(self, realtime_data: Dict[str, StockData]):
        """更新快照数据（从真实API获取后保存）"""
        for code, stock in realtime_data.items():
            self.data[code] = asdict(stock)

        with open(self.snapshot_file, 'w') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get(self, codes: List[str]) -> Dict[str, StockData]:
        """获取快照数据"""
        result = {}
        for code in codes:
            if code in self.data:
                result[code] = StockData(**self.data[code])
        return result
```

## 📋 数据流向图

```
┌─────────────────────────────────────────────────────────┐
│                    前端组件层                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│
│  │ 自选股   │  │ 市场扫描 │  │ 涨停预测 │  │ 其他模块 ││
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘│
└───────┼─────────────┼─────────────┼─────────────┼──────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────────┐
        │         后端API路由层                      │
        │  /api/config/favorites                    │
        │  /api/market-scanner/scan/{type}          │
        │  /api/limit-up/quick-predictions          │
        │  /api/smart-selection/real-time           │
        └───────────────┬───────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────────┐
        │    UnifiedDataSource (统一数据源)         │
        │    • 缓存管理                              │
        │    • 数据验证                              │
        │    • Fallback链                           │
        └───────────────┬───────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌───────────────┐              ┌───────────────┐
│  实时数据源    │              │  兜底数据源    │
│               │              │               │
│ 1. 腾讯API    │──失败──┐     │ 本地快照       │
│ 2. 东财API    │        │     │ (真实历史数据)  │
│ 3. AkShare    │        └────▶│               │
└───────────────┘              └───────────────┘
```

## 🔧 实施步骤

### Phase 1: 核心组件开发 (1-2小时)
1. ✅ 创建 `unified_data_source.py`
2. ✅ 创建 `data_validator.py`
3. ✅ 创建 `real_data_snapshot.py`
4. ✅ 编写单元测试

### Phase 2: 迁移现有代码 (2-3小时)
1. ✅ 重构 `main.py` 使用UnifiedDataSource
2. ✅ 更新所有API路由引用
3. ✅ 移除冗余的数据源类
4. ✅ 清理旧代码

### Phase 3: 数据快照管理 (1小时)
1. ✅ 收集真实市场数据创建初始快照
2. ✅ 实现自动更新机制（成功API调用后保存）
3. ✅ 添加数据版本控制

### Phase 4: 测试验证 (1小时)
1. ✅ 测试所有前端模块数据一致性
2. ✅ 验证fallback机制工作正常
3. ✅ 性能测试和优化

## 📊 数据来源优先级说明

### 为什么这个顺序？

1. **腾讯API (首选)**
   - ✅ 速度快（<100ms）
   - ✅ 格式简单
   - ✅ 稳定性好
   - ❌ 部分字段缺失

2. **东方财富API (备选)**
   - ✅ 数据最全面
   - ✅ 支持高级查询
   - ❌ 速度较慢（200-500ms）
   - ❌ 最容易被限流

3. **AkShare (备选)**
   - ✅ 开源稳定
   - ✅ 数据质量高
   - ❌ 速度慢（1-3秒）
   - ❌ 需要安装依赖

4. **本地快照 (兜底)**
   - ✅ 100%可用
   - ✅ 零延迟
   - ❌ 数据可能过时
   - ✅ 基于真实历史数据

## 🎯 预期效果

### 1. 数据一致性
- ✅ 所有模块显示相同的股票数据
- ✅ 价格、涨跌幅、换手率完全一致
- ✅ 统一的更新时间戳

### 2. 系统可靠性
- ✅ API失败不影响系统运行
- ✅ 多层fallback保证数据可用
- ✅ 自动降级，无需人工干预

### 3. 可维护性
- ✅ 单一入口，易于调试
- ✅ 清晰的数据流向
- ✅ 统一的日志追踪

### 4. 性能优化
- ✅ 缓存机制减少API调用
- ✅ 批量获取提升效率
- ✅ 异步并发处理

## 📝 配置文件示例

### data/stock_snapshot.json
```json
{
  "metadata": {
    "version": "1.0",
    "last_update": "2025-09-30T16:15:00",
    "data_source": "腾讯API",
    "total_stocks": 5
  },
  "stocks": {
    "sh688307": {
      "code": "688307",
      "name": "中润光学",
      "current_price": 37.13,
      "change_percent": -1.01,
      "turnover_rate": 7.09,
      "yesterday_close": 37.51,
      "high_price": 37.98,
      "low_price": 36.80,
      "open_price": 37.34,
      "volume": 4178428,
      "amount": 155733321,
      "update_time": "2025-09-30T16:14:59"
    }
  }
}
```

## 🚀 立即执行计划

开始实施重构，预计总耗时：5-7小时
