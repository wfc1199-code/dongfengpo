# 模块重构标准 v1.0

## 1. 模块文件结构

每个模块必须包含以下文件：

```
modules/
└── {module_name}/
    ├── __init__.py          # 模块导出
    ├── module.py            # FastAPI路由定义 (< 200行)
    ├── service.py           # 业务逻辑层 (< 500行)
    ├── models.py            # Pydantic数据模型
    ├── constants.py         # 常量定义 (可选)
    ├── utils.py             # 工具函数 (可选)
    └── tests/               # 单元测试 (可选)
        └── test_service.py
```

## 2. 代码质量标准

### 2.1 模块层 (module.py)
- ✅ 继承 `BaseModule`
- ✅ 所有路由定义清晰，带类型注解
- ✅ 使用 Pydantic 模型验证请求/响应
- ✅ 每个路由有docstring说明
- ✅ 统一的错误处理 (HTTPException)
- ❌ 不包含业务逻辑，只负责路由和参数验证

### 2.2 服务层 (service.py)
- ✅ 所有业务逻辑在此实现
- ✅ 方法有完整的类型注解
- ✅ 异步方法使用 `async def`
- ✅ 日志记录关键操作
- ✅ 异常要有明确的错误信息
- ❌ 单个方法不超过50行
- ❌ 单个文件不超过500行 (超过需拆分)

### 2.3 数据模型层 (models.py)
```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class StockInfo(BaseModel):
    """股票基本信息"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    price: float = Field(..., description="当前价格")
    change_percent: float = Field(..., description="涨跌幅(%)")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "000001",
                "name": "平安银行",
                "price": 11.34,
                "change_percent": -0.26
            }
        }
```

### 2.4 常量定义 (constants.py)
```python
"""模块常量定义"""

# 时间常量
CACHE_TTL = 3600  # 缓存过期时间（秒）
REQUEST_TIMEOUT = 30  # API请求超时（秒）

# 业务常量
MAX_SEARCH_RESULTS = 100
DEFAULT_LIMIT = 20

# 配置路径（使用环境变量）
import os
CONFIG_DIR = os.getenv("CONFIG_DIR", "backend/data")
```

## 3. 依赖注入标准

### 3.1 使用shared模块获取依赖
```python
from modules.shared import get_data_source, get_cache_manager

class MyService:
    def __init__(self):
        self.data_manager = get_data_source()
        self.cache = get_cache_manager()
```

### 3.2 避免循环依赖
- ❌ 模块间不能直接相互导入
- ✅ 通过shared模块或依赖注入获取其他模块功能

## 4. 错误处理标准

### 4.1 统一的错误响应格式
```python
from fastapi import HTTPException

# 数据验证错误
raise HTTPException(status_code=400, detail="参数错误: 股票代码不能为空")

# 资源不存在错误
raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")

# 服务器错误
raise HTTPException(status_code=500, detail=f"获取数据失败: {str(e)}")
```

### 4.2 日志记录标准
```python
import logging
logger = logging.getLogger(__name__)

# 信息日志
logger.info(f"✅ 成功获取股票数据: {code}")

# 警告日志
logger.warning(f"⚠️  缓存未命中: {key}")

# 错误日志
logger.error(f"❌ API调用失败: {e}")
```

## 5. 性能优化标准

### 5.1 缓存策略
```python
from datetime import datetime, timedelta

class ServiceWithCache:
    def __init__(self):
        self._cache = {}
        self._cache_time = {}
        self._cache_ttl = 3600

    async def get_data(self, key: str):
        # 检查缓存
        if self._is_cache_valid(key):
            return self._cache[key]

        # 获取新数据
        data = await self._fetch_data(key)

        # 更新缓存
        self._cache[key] = data
        self._cache_time[key] = datetime.now()

        return data

    def _is_cache_valid(self, key: str) -> bool:
        if key not in self._cache_time:
            return False
        age = (datetime.now() - self._cache_time[key]).seconds
        return age < self._cache_ttl
```

### 5.2 异步IO优化
```python
import asyncio

# ✅ 并发请求
results = await asyncio.gather(
    fetch_stock_info(code1),
    fetch_stock_info(code2),
    fetch_stock_info(code3)
)

# ✅ 使用run_in_executor处理同步代码
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, blocking_function, arg)
```

## 6. 测试标准

### 6.1 单元测试结构
```python
# tests/test_service.py
import pytest
from modules.my_module.service import MyService

@pytest.fixture
def service():
    return MyService()

async def test_get_stock_info(service):
    """测试获取股票信息"""
    result = await service.get_stock_info("000001")
    assert result["code"] == "000001"
    assert "name" in result
    assert "price" in result

async def test_search_stocks(service):
    """测试股票搜索"""
    results = await service.search_stocks("平安")
    assert len(results) > 0
    assert any("平安" in r["name"] for r in results)
```

## 7. 文档标准

### 7.1 模块级文档
```python
"""
股票数据模块

提供股票的实时数据、历史K线、支撑阻力位等功能

主要功能：
- 实时行情查询
- K线数据获取
- 支撑阻力位计算
- 股票搜索（支持拼音）

依赖：
- akshare: 数据源
- pypinyin: 拼音搜索

示例：
```
GET /api/stocks/000001/realtime  # 获取实时行情
GET /api/stocks/search?keyword=平安  # 搜索股票
```
"""
```

### 7.2 函数级文档
```python
async def get_stock_info(self, code: str) -> Dict[str, Any]:
    """获取股票基本信息

    Args:
        code: 股票代码（6位数字）

    Returns:
        {
            "code": "000001",
            "name": "平安银行",
            "price": 11.34,
            "change_percent": -0.26,
            "volume": 123456
        }

    Raises:
        HTTPException: 404 - 股票不存在
        HTTPException: 500 - 数据获取失败

    Example:
        >>> info = await service.get_stock_info("000001")
        >>> print(info["name"])
        "平安银行"
    """
```

## 8. 重构检查清单

在重构每个模块时，确保：

- [ ] 文件结构符合标准 (module.py, service.py, models.py)
- [ ] 所有函数有类型注解
- [ ] 所有路由有docstring
- [ ] 使用Pydantic模型验证数据
- [ ] 错误处理统一使用HTTPException
- [ ] 日志记录关键操作
- [ ] 没有硬编码的路径和常量
- [ ] 异步IO使用正确
- [ ] 添加了单元测试
- [ ] 代码行数符合限制
- [ ] 没有循环依赖

## 9. 重构优先级

基于影响范围和改进收益，建议重构优先级：

1. **P0 - 立即重构**
   - `stocks` - 核心模块，自选股功能需要
   - `config` - 配置管理，影响所有模块

2. **P1 - 近期重构**
   - `limit_up` - 代码量大，需要拆分
   - `market_scanner` - 性能优化需求

3. **P2 - 后续优化**
   - `anomaly`, `options`, `transactions`, `websocket`

## 10. 迁移策略

重构时采用渐进式迁移：

1. **创建新版本模块** (不影响现有功能)
2. **编写单元测试** (确保功能一致)
3. **逐步切换路由** (灰度发布)
4. **验证功能正常** (监控错误率)
5. **删除旧代码** (清理遗留)

---

**版本**: 1.0
**更新时间**: 2025-10-02
**负责人**: Claude Code Refactoring Team
