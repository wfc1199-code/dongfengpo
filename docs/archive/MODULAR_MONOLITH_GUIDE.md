# 🏗️ 模块化单体架构指南

## 📋 概述

**模块化单体** (Modular Monolith) 是介于传统单体和微服务之间的最佳实践架构：

- ✅ **保持单体的简单性** - 单进程，易部署
- ✅ **获得微服务的清晰性** - 模块独立，职责明确
- ✅ **平滑迁移路径** - 未来可无痛拆分为微服务

---

## 🎯 为什么选择模块化单体？

### 对比传统单体（Legacy）

| 维度 | Legacy单体 | 模块化单体 |
|------|-----------|-----------|
| 代码组织 | 36个文件混在`api/`目录 | 10个独立模块目录 |
| 职责划分 | ❌ 不清晰 | ✅ 非常清晰 |
| 测试难度 | ⭐⭐⭐⭐ 困难 | ⭐⭐ 简单 |
| 新人上手 | ⭐⭐ 难 | ⭐⭐⭐⭐ 容易 |
| 部署复杂度 | ⭐ 简单 | ⭐ 简单 |

### 对比完整微服务

| 维度 | 模块化单体 | 完整微服务 |
|------|-----------|-----------|
| 进程数 | 1个 | 11+个 |
| 部署复杂度 | ⭐ 简单 | ⭐⭐⭐⭐⭐ 复杂 |
| 响应延迟 | 10-50ms | 50-200ms |
| 开发效率 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 可扩展性 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 📁 目录结构

```
backend/
├── modules/                    # 📦 业务模块层
│   ├── shared/                # 共享组件
│   │   ├── __init__.py
│   │   ├── base_module.py     # 模块基类
│   │   └── dependencies.py    # 依赖注入
│   │
│   ├── limit_up/              # 涨停预测模块
│   │   ├── __init__.py
│   │   ├── module.py          # 模块主文件
│   │   ├── service.py         # 业务逻辑（可选）
│   │   └── models.py          # 数据模型（可选）
│   │
│   ├── anomaly/               # 异动检测模块
│   ├── market/                # 市场分析模块
│   ├── stocks/                # 股票数据模块
│   ├── selection/             # 智能选股模块
│   ├── options/               # 期权模块
│   ├── fundamental/           # 基本面模块
│   ├── alerts/                # 预警模块
│   ├── websocket/             # 实时推送模块
│   └── system/                # 系统管理模块
│
├── api/                       # 🗂️ Legacy路由（逐步废弃）
├── core/                      # 🔧 核心组件（继续使用）
├── main.py                    # 🔴 Legacy主程序
├── main_modular.py            # 🟢 模块化主程序 ⭐新⭐
└── requirements.txt
```

---

## 🚀 快速开始

### 1. 启动模块化版本

```bash
cd backend
../venv/bin/python main_modular.py
```

### 2. 访问API文档

```
http://localhost:9000/docs
```

### 3. 查看已加载模块

```bash
curl http://localhost:9000/modules
```

---

## 🔨 创建新模块

### 步骤1：创建模块目录

```bash
mkdir -p backend/modules/my_feature
```

### 步骤2：创建模块文件

```python
# backend/modules/my_feature/__init__.py
from .module import MyFeatureModule
__all__ = ["MyFeatureModule"]

# backend/modules/my_feature/module.py
from modules.shared import BaseModule

class MyFeatureModule(BaseModule):
    def __init__(self):
        super().__init__(
            name="my_feature",
            prefix="/api/my-feature",
            tags=["我的功能"],
            description="这是我的新功能模块"
        )

    def register_routes(self):
        @self.router.get("/hello")
        async def hello():
            return {"message": "Hello from MyFeature!"}
```

### 步骤3：注册到主程序

```python
# backend/main_modular.py
from modules.my_feature import MyFeatureModule

def init_modules():
    modules = [
        LimitUpModule(),
        AnomalyModule(),
        StocksModule(),
        MyFeatureModule(),  # 👈 添加这里
    ]
    ...
```

### 步骤4：重启服务

```bash
# 自动重载，无需手动重启
# 访问: http://localhost:9000/api/my-feature/hello
```

---

## 📚 迁移策略

### 阶段1：创建模块框架（✅ 已完成）

- [x] 创建`modules/`目录结构
- [x] 实现`BaseModule`基类
- [x] 创建共享组件层
- [x] 创建3个示例模块

### 阶段2：逐步迁移API（进行中）

**优先级顺序**：

1. **P0 - 核心功能**
   - [ ] limit_up - 涨停预测（框架已建立）
   - [ ] anomaly - 异动检测
   - [ ] stocks - 股票数据

2. **P1 - 重要功能**
   - [ ] market - 市场分析
   - [ ] selection - 智能选股
   - [ ] websocket - 实时推送

3. **P2 - 增强功能**
   - [ ] options - 期权
   - [ ] fundamental - 基本面
   - [ ] alerts - 预警
   - [ ] system - 系统管理

### 阶段3：清理Legacy代码

- [ ] 删除`api/`目录下的旧文件
- [ ] 更新`main.py`为`main_modular.py`
- [ ] 更新文档和脚本

---

## 💡 最佳实践

### 1. 模块设计原则

✅ **单一职责**
```python
# Good: 专注于涨停预测
class LimitUpModule(BaseModule):
    def register_routes(self):
        @self.router.get("/predictions")
        async def get_predictions():
            ...

# Bad: 混杂多个功能
class MixedModule(BaseModule):
    def register_routes(self):
        @self.router.get("/limit-up")      # 涨停
        @self.router.get("/anomaly")       # 异动
        @self.router.get("/market-scan")   # 扫描
```

✅ **依赖注入**
```python
from modules.shared import get_cache_manager, get_data_source

class LimitUpModule(BaseModule):
    def __init__(self):
        super().__init__(...)
        self.cache = get_cache_manager()   # 通过依赖注入获取
        self.data_source = get_data_source()
```

✅ **清晰的API路径**
```python
# Good: 模块统一前缀
/api/limit-up/predictions
/api/limit-up/tracking
/api/limit-up/statistics

# Bad: 路径混乱
/limit-up-predictions
/track-limit-up
/get-limit-up-stats
```

### 2. 共享资源管理

```python
# modules/shared/dependencies.py
def get_database():
    """所有模块共享同一个数据库连接池"""
    return db_pool

def get_cache():
    """所有模块共享同一个缓存实例"""
    return cache_instance
```

### 3. 模块间通信

```python
# 方式1：直接函数调用（推荐，同进程）
from modules.stocks import StocksModule

class LimitUpModule(BaseModule):
    def __init__(self):
        super().__init__(...)
        self.stocks_module = StocksModule()

    async def predict(self):
        stock_data = await self.stocks_module.get_realtime_data()
        # 使用数据进行预测

# 方式2：通过共享服务（解耦）
from modules.shared import get_data_service

class LimitUpModule(BaseModule):
    def __init__(self):
        super().__init__(...)
        self.data_service = get_data_service()  # 共享服务
```

---

## 🔄 迁移一个API示例

### 原来的代码（Legacy）

```python
# backend/api/limit_up_routes.py
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["limit_up"])

@router.get("/limit-up/predictions")
async def get_predictions():
    # 业务逻辑混在路由文件里
    data = calculate_predictions()
    return {"predictions": data}

def calculate_predictions():
    # 100行业务逻辑代码
    ...
```

### 迁移后的代码（Modular）

```python
# backend/modules/limit_up/module.py
from modules.shared import BaseModule
from .service import LimitUpService  # 业务逻辑分离

class LimitUpModule(BaseModule):
    def __init__(self):
        super().__init__(
            name="limit_up",
            prefix="/api/limit-up",
            tags=["涨停预测"]
        )
        self.service = LimitUpService()  # 服务层

    def register_routes(self):
        @self.router.get("/predictions")
        async def get_predictions():
            # 路由只负责HTTP层，业务逻辑在service
            predictions = await self.service.calculate_predictions()
            return {"predictions": predictions}

# backend/modules/limit_up/service.py
class LimitUpService:
    """业务逻辑层，可独立测试"""

    async def calculate_predictions(self):
        # 100行业务逻辑代码
        ...
```

**优势**：
- ✅ 路由层和业务逻辑分离
- ✅ 业务逻辑可独立单元测试
- ✅ 代码结构清晰

---

## 🧪 测试

### 测试模块独立性

```python
# tests/test_limit_up_module.py
import pytest
from modules.limit_up import LimitUpModule

def test_module_initialization():
    module = LimitUpModule()
    assert module.name == "limit_up"
    assert module.prefix == "/api/limit-up"

async def test_module_routes():
    module = LimitUpModule()
    # 测试路由注册
    assert len(module.router.routes) > 0
```

### 测试API端点

```bash
# 自动化测试
curl http://localhost:9000/api/limit-up/health
curl http://localhost:9000/api/limit-up/info
```

---

## 🚢 未来：拆分为微服务

当需要时，模块可以**零修改**拆分为独立微服务：

```python
# services/limit-up-service/main.py
from modules.limit_up import LimitUpModule

app = FastAPI()
module = LimitUpModule()
app.include_router(module.router)

# 就这么简单！现在是独立微服务了
uvicorn.run(app, port=9003)
```

---

## 📊 当前状态

### ✅ 已完成
- 模块化框架搭建
- BaseModule基类
- 共享组件层
- 3个示例模块
- main_modular.py主程序

### 🔄 进行中
- 逐步迁移36个API文件到对应模块

### ⏳ 计划中
- 完成所有模块迁移
- 添加单元测试
- 性能优化
- 文档完善

---

## 🎓 学习资源

- [FastAPI依赖注入](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [模块化单体模式](https://www.kamilgrzybek.com/design/modular-monolith-primer/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

---

## 🆘 常见问题

**Q: 模块化单体和Legacy单体有什么区别？**
A: 代码组织更清晰，但仍然是单进程。就像把乱放的衣服整理到不同的抽屉。

**Q: 什么时候应该拆分为微服务？**
A: 当某个模块负载特别高，或需要独立扩展时。现阶段不需要。

**Q: 如何在模块间共享数据？**
A: 使用共享服务（如数据库、缓存），或直接函数调用（同进程）。

**Q: 会影响性能吗？**
A: 不会。仍然是单进程，函数直接调用，性能和Legacy一样。

---

**最后更新**: 2025-10-02
**版本**: 2.0.0-modular
**状态**: ✅ 可用于开发
