# 期权模块集成指南

## 📋 概述

基于之前的研究和测试，本指南展示如何在现有系统中集成实时期权数据模块，确保数据延迟最小（目标：小于2分钟）。

## 🎯 核心设计

### 1. 架构选择
- **模块化设计**：独立的期权模块，可插拔
- **多数据源支持**：东方财富（主）+ 腾讯/新浪（备）
- **智能缓存**：分级缓存策略，平衡性能和实时性
- **WebSocket推送**：实时数据推送，减少API轮询

### 2. 实时性保障
- 数据源延迟：15-30秒（免费）或 5秒（付费）
- 缓存时间：期权价格5秒，分时数据10秒
- 推送频率：2秒/次（交易时间）

## 🔧 实施步骤

### 第1步：创建期权模块

#### 1.1 目录结构
```
backend/modules/options/
├── __init__.py
├── module.py          # 模块入口
├── service.py         # 业务逻辑
├── routes.py          # API路由
├── models.py          # 数据模型
└── websocket.py       # WebSocket处理
```

#### 1.2 创建模块文件

```python
# backend/modules/options/__init__.py
from .module import OptionsModule

__all__ = ['OptionsModule']
```

```python
# backend/modules/options/module.py
from typing import Dict, Any
from ..base import BaseModule
from .service import OptionService
from .routes import setup_routes

class OptionsModule(BaseModule):
    """期权数据模块"""

    def __init__(self):
        super().__init__()
        self.service: OptionService = None

    async def initialize(self, app):
        """初始化模块"""
        self.service = OptionService()
        await self.service.initialize()

        # 注册路由
        setup_routes(app, self.service)

        # 注册WebSocket处理
        from .websocket import setup_websocket
        setup_websocket(app, self.service.websocket_manager)

        self.logger.info("期权模块初始化完成")

    async def cleanup(self):
        """清理模块"""
        if self.service:
            await self.service.cleanup()
        self.logger.info("期权模块已清理")
```

### 第2步：实现核心服务

#### 2.1 创建服务类

```python
# backend/modules/options/service.py
import asyncio
from typing import List, Dict, Optional
from ...services.real_option_data_fetcher import RealOptionDataFetcher
from ...services.option_websocket_service import OptionWebSocketManager

class OptionService:
    """期权数据服务"""

    def __init__(self):
        self.data_fetcher: RealOptionDataFetcher = None
        self.websocket_manager: OptionWebSocketManager = None

    async def initialize(self):
        """初始化服务"""
        self.data_fetcher = RealOptionDataFetcher()
        await self.data_fetcher.__aenter__()

        self.websocket_manager = OptionWebSocketManager()
        self.websocket_manager.data_fetcher = self.data_fetcher

    async def cleanup(self):
        """清理服务"""
        if self.websocket_manager:
            await self.websocket_manager.cleanup()
        if self.data_fetcher:
            await self.data_fetcher.__aexit__(None, None, None)

    async def search_options(self, query: str, limit: int = 10):
        """搜索期权"""
        return await self.data_fetcher.search_options(query, limit)

    async def get_option_info(self, option_code: str):
        """获取期权信息"""
        options = await self.data_fetcher.search_options(option_code, limit=1)
        return options[0] if options else None

    async def get_option_minute_data(self, option_code: str):
        """获取分时数据"""
        return await self.data_fetcher.get_option_minute_data(option_code)
```

#### 2.2 创建API路由

```python
# backend/modules/options/routes.py
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
import uuid

router = APIRouter(prefix="/api/options", tags=["options"])

def setup_routes(app, option_service):
    """设置路由"""

    @router.get("/search")
    async def search_options(
        q: str = Query(..., description="搜索关键词"),
        limit: int = Query(10, ge=1, le=50, description="返回数量")
    ):
        """搜索期权"""
        results = await option_service.search_options(q, limit)
        return {
            "status": "success",
            "data": results,
            "total": len(results)
        }

    @router.get("/{option_code}/info")
    async def get_option_info(option_code: str):
        """获取期权基本信息"""
        info = await option_service.get_option_info(option_code)
        if not info:
            return {"status": "error", "message": "期权不存在"}

        return {
            "status": "success",
            "data": info
        }

    @router.get("/{option_code}/minute")
    async def get_option_minute_data(option_code: str):
        """获取期权分时数据"""
        data = await option_service.get_option_minute_data(option_code)

        return {
            "status": "success",
            "code": option_code,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }

    app.include_router(router)
```

### 第3步：集成WebSocket

#### 3.1 WebSocket路由

```python
# backend/modules/options/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
import json
import uuid
from ...services.option_websocket_service import handle_websocket_connection

def setup_websocket(app, websocket_manager):
    """设置WebSocket路由"""

    @app.websocket("/ws/options/{client_id}")
    async def websocket_endpoint(websocket: WebSocket, client_id: str):
        """期权数据WebSocket端点"""
        await handle_websocket_connection(websocket, client_id)
```

### 第4步：注册模块

#### 4.1 修改主模块

```python
# backend/main_modular.py
from modules.options import OptionsModule

async def create_app():
    """创建应用"""
    app = FastAPI(title="东风破交易系统")

    # ... 其他模块初始化 ...

    # 注册期权模块
    options_module = OptionsModule()
    await options_module.initialize(app)
    app.state.options_module = options_module

    return app
```

### 第5步：前端集成

#### 5.1 创建期权服务

```typescript
// frontend/src/services/option.service.ts
export class OptionService {
  private ws: WebSocket | null = null;
  private subscriptions: Set<string> = new Set();

  // 搜索期权
  async searchOptions(query: string, limit = 10) {
    return fetch(`/api/options/search?q=${query}&limit=${limit}`)
      .then(res => res.json());
  }

  // 获取期权信息
  async getOptionInfo(code: string) {
    return fetch(`/api/options/${code}/info`)
      .then(res => res.json());
  }

  // 获取分时数据
  async getMinuteData(code: string) {
    return fetch(`/api/options/${code}/minute`)
      .then(res => res.json());
  }

  // WebSocket连接
  connectWebSocket() {
    const clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    this.ws = new WebSocket(`ws://localhost:9000/ws/options/${clientId}`);

    this.ws.onopen = () => {
      console.log('期权WebSocket连接成功');
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };

    return this.ws;
  }

  // 订阅期权
  subscribe(optionCodes: string[]) {
    if (!this.ws) this.connectWebSocket();

    optionCodes.forEach(code => this.subscriptions.add(code));

    this.ws.send(JSON.stringify({
      type: 'subscribe',
      options: optionCodes
    }));
  }

  // 处理消息
  private handleMessage(data: any) {
    switch (data.type) {
      case 'option_realtime':
        // 更新期权价格
        this.updateOptionPrice(data);
        break;
      case 'subscription_confirmed':
        console.log('订阅成功:', data.subscribed_options);
        break;
    }
  }

  // 更新UI
  private updateOptionPrice(data: any) {
    // 触发价格更新事件
    window.dispatchEvent(new CustomEvent('optionPriceUpdate', {
      detail: data
    }));
  }
}

export const optionService = new OptionService();
```

#### 5.2 创建期权组件

```typescript
// frontend/src/components/OptionCard.tsx
import React, { useState, useEffect } from 'react';
import { optionService } from '../services/option.service';

interface OptionCardProps {
  optionCode: string;
}

export const OptionCard: React.FC<OptionCardProps> = ({ optionCode }) => {
  const [option, setOption] = useState<any>(null);
  const [price, setPrice] = useState<number>(0);
  const [change, setChange] = useState<number>(0);

  useEffect(() => {
    // 获取期权信息
    optionService.getOptionInfo(optionCode).then(res => {
      if (res.status === 'success') {
        setOption(res.data);
        setPrice(res.data.current_price);
        setChange(res.data.change_percent);
      }
    });

    // 订阅实时数据
    optionService.subscribe([optionCode]);

    // 监听价格更新
    const handlePriceUpdate = (event: CustomEvent) => {
      const data = event.detail;
      if (data.code === optionCode) {
        setPrice(data.current_price);
        setChange(data.change_percent);
      }
    };

    window.addEventListener('optionPriceUpdate', handlePriceUpdate as any);

    return () => {
      window.removeEventListener('optionPriceUpdate', handlePriceUpdate as any);
    };
  }, [optionCode]);

  if (!option) return <div>加载中...</div>;

  return (
    <div className="option-card">
      <h3>{option.name}</h3>
      <div className="price-info">
        <span className="price">¥{price.toFixed(4)}</span>
        <span className={`change ${change >= 0 ? 'positive' : 'negative'}`}>
          {change >= 0 ? '+' : ''}{change.toFixed(2)}%
        </span>
      </div>
      <div className="option-details">
        <p>标的: {option.underlying}</p>
        <p>行权价: ¥{option.strike_price}</p>
        <p>到期: {option.expiry}</p>
        <p>类型: {option.type === 'call' ? '看涨' : '看跌'}</p>
      </div>
    </div>
  );
};
```

### 第6步：配置优化

#### 6.1 缓存配置

```python
# backend/core/cache_config.py
OPTION_CACHE_CONFIG = {
    # 期权价格变化快，缓存时间短
    'option_price': 5,

    # 分时数据量大，缓存时间适中
    'minute_data': 10,

    # 基本信息稳定，缓存时间长
    'basic_info': 300,

    # 搜索结果缓存
    'search_results': 30
}
```

#### 6.2 监控配置

```python
# backend/monitoring/option_monitor.py
import time
from datetime import datetime

class OptionMonitor:
    """期权数据监控"""

    def __init__(self):
        self.metrics = {
            'api_response_times': [],
            'data_delays': [],
            'cache_hit_rates': {},
            'error_counts': {}
        }

    def record_api_call(self, endpoint: str, response_time: float):
        """记录API调用"""
        self.metrics['api_response_times'].append({
            'endpoint': endpoint,
            'time': response_time,
            'timestamp': datetime.now()
        })

    def record_data_delay(self, option_code: str, delay_minutes: float):
        """记录数据延迟"""
        self.metrics['data_delays'].append({
            'option': option_code,
            'delay': delay_minutes,
            'timestamp': datetime.now()
        })

    def get_summary(self) -> dict:
        """获取监控摘要"""
        # 计算平均响应时间
        avg_response_time = sum(
            m['time'] for m in self.metrics['api_response_times'][-100:]
        ) / min(100, len(self.metrics['api_response_times']))

        # 计算平均数据延迟
        avg_delay = sum(
            m['delay'] for m in self.metrics['data_delays'][-100:]
        ) / min(100, len(self.metrics['data_delays']))

        return {
            'avg_response_time_ms': avg_response_time * 1000,
            'avg_data_delay_minutes': avg_delay,
            'total_api_calls': len(self.metrics['api_response_times']),
            'status': 'good' if avg_delay < 2 else 'warning'
        }
```

## 📊 性能指标

### 目标指标
- **API响应时间**: < 100ms
- **数据延迟**: < 2分钟
- **缓存命中率**: > 80%
- **WebSocket推送延迟**: < 500ms
- **系统可用性**: 99.9%

### 监控要点
1. 实时数据延迟监控
2. API响应时间分布
3. 缓存效率统计
4. WebSocket连接数
5. 错误率统计

## ⚠️ 注意事项

### 1. 数据源限制
- 免费数据源有频率限制
- 建议添加请求间隔：100ms
- 实现指数退避重试机制

### 2. 交易时间
```python
def is_trading_hours():
    """判断是否在交易时间"""
    now = datetime.now()
    weekday = now.weekday()

    # 周末不交易
    if weekday >= 5:
        return False

    hour, minute = now.hour, now.minute

    # 上午: 9:30-11:30
    if (hour == 9 and minute >= 30) or (10 <= hour < 11) or \
       (hour == 11 and minute <= 30):
        return True

    # 下午: 13:00-15:00
    if (hour == 13) or (hour == 14) or (hour == 15 and minute == 0):
        return True

    return False
```

### 3. 内存管理
- 定期清理过期缓存
- 使用弱引用管理WebSocket连接
- 限制订阅数量

### 4. 错误处理
- 数据源自动切换
- 优雅降级机制
- 详细的错误日志

## 🚀 部署建议

### 1. 开发环境
```bash
# 安装依赖
pip install aiohttp fastapi websockets

# 启动开发服务器
uvicorn main_modular:app --reload --port 9000
```

### 2. 生产环境
- 使用Gunicorn + Uvicorn
- 配置Nginx反向代理
- 设置Redis缓存
- 配置监控告警

### 3. 扩展方案
- 接入付费数据源（Tushare Pro）
- 实现Level-2行情数据
- 添加期权定价模型
- 集成风险管理模块

## 📝 测试验证

### 1. 功能测试
```bash
# 运行测试脚本
python test_real_option_fetcher.py
python test_option_latency.html
```

### 2. 压力测试
- 模拟100个并发连接
- 测试高频订阅/取消订阅
- 验证内存使用情况

### 3. 延迟测试
- 实时监控数据延迟
- 对比多个数据源
- 验证缓存效果

## 🎉 总结

通过以上步骤，您可以成功集成实时期权数据模块，实现：

1. ✅ **实时数据获取**：多数据源保障，延迟小于2分钟
2. ✅ **WebSocket推送**：2秒级的实时价格推送
3. ✅ **智能缓存**：分级缓存策略，优化性能
4. ✅ **模块化设计**：独立模块，易于维护和扩展
5. ✅ **完善的监控**：实时监控系统健康状态

这个方案平衡了成本和性能，可以满足期权交易的实时性需求。根据实际使用情况，可以逐步升级到付费数据源以获得更好的实时性。