# 前端集成指南

**版本**: v2.0-data-pipeline
**更新日期**: 2025-09-30
**适用范围**: Phase 3 前端开发

---

## 📋 概述

本指南说明前端如何接入 Phase 2 完成后的新架构，通过 **API Gateway** 统一访问所有后端服务。

---

## 🌐 API 端点配置

### 统一网关入口

所有API请求都通过 **API Gateway** (http://localhost:8888)

```javascript
// frontend/src/config/api.js
export const API_CONFIG = {
  // 统一网关地址
  baseURL: process.env.REACT_APP_API_GATEWAY || 'http://localhost:8888',

  // API端点
  endpoints: {
    // 健康检查
    health: '/health',
    gatewayHealth: '/gateway/health',

    // 信号与机会
    opportunities: '/opportunities',
    signals: '/api/v2/signals',

    // 回测
    backtests: '/backtests',
    backtestDetail: (id) => `/backtests/${id}`,

    // Legacy端点（通过网关转发）
    stocks: '/api/stocks',
    anomaly: '/api/anomaly',
    limitUp: '/api/limit-up',
  },

  // WebSocket（直连，不通过网关）
  websocket: {
    opportunities: process.env.REACT_APP_WS_URL || 'ws://localhost:8100/ws/opportunities',
  },

  // 请求配置
  timeout: 10000,
  retries: 3,
}
```

---

## 🔌 API 调用示例

### 1. Axios 配置

```javascript
// frontend/src/utils/api.js
import axios from 'axios'
import { API_CONFIG } from '../config/api'

// 创建 Axios 实例
const apiClient = axios.create({
  baseURL: API_CONFIG.baseURL,
  timeout: API_CONFIG.timeout,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 添加认证token（如果需要）
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    console.error('API Error:', error)

    // 统一错误处理
    if (error.response) {
      switch (error.response.status) {
        case 401:
          // 未授权，跳转登录
          window.location.href = '/login'
          break
        case 404:
          // 资源不存在
          console.warn('Resource not found:', error.config.url)
          break
        case 500:
          // 服务器错误
          console.error('Server error:', error.response.data)
          break
      }
    } else if (error.request) {
      // 网络错误
      console.error('Network error:', error.message)
    }

    return Promise.reject(error)
  }
)

export default apiClient
```

### 2. API 服务类

```javascript
// frontend/src/services/opportunityService.js
import apiClient from '../utils/api'
import { API_CONFIG } from '../config/api'

class OpportunityService {
  /**
   * 获取所有机会
   * @param {Object} params - 查询参数
   * @returns {Promise<Array>}
   */
  async getOpportunities(params = {}) {
    try {
      const response = await apiClient.get(API_CONFIG.endpoints.opportunities, { params })
      return response
    } catch (error) {
      console.error('Failed to fetch opportunities:', error)
      return []
    }
  }

  /**
   * 获取单个机会详情
   * @param {string} symbol - 股票代码
   * @returns {Promise<Object>}
   */
  async getOpportunityDetail(symbol) {
    try {
      const response = await apiClient.get(`${API_CONFIG.endpoints.opportunities}/${symbol}`)
      return response
    } catch (error) {
      console.error(`Failed to fetch opportunity for ${symbol}:`, error)
      return null
    }
  }
}

export default new OpportunityService()
```

### 3. React Hook 使用

```javascript
// frontend/src/hooks/useOpportunities.js
import { useState, useEffect } from 'react'
import opportunityService from '../services/opportunityService'

export const useOpportunities = (refreshInterval = 5000) => {
  const [opportunities, setOpportunities] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchOpportunities = async () => {
    try {
      setLoading(true)
      const data = await opportunityService.getOpportunities()
      setOpportunities(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchOpportunities()

    // 定期刷新
    const interval = setInterval(fetchOpportunities, refreshInterval)

    return () => clearInterval(interval)
  }, [refreshInterval])

  return { opportunities, loading, error, refresh: fetchOpportunities }
}
```

### 4. 组件使用

```javascript
// frontend/src/components/OpportunityList.jsx
import React from 'react'
import { useOpportunities } from '../hooks/useOpportunities'

const OpportunityList = () => {
  const { opportunities, loading, error, refresh } = useOpportunities(5000)

  if (loading) return <div>加载中...</div>
  if (error) return <div>错误: {error}</div>

  return (
    <div className="opportunity-list">
      <div className="header">
        <h2>交易机会 ({opportunities.length})</h2>
        <button onClick={refresh}>刷新</button>
      </div>

      <div className="list">
        {opportunities.length === 0 ? (
          <p>暂无机会</p>
        ) : (
          opportunities.map((opp) => (
            <div key={opp.symbol} className="opportunity-card">
              <h3>{opp.symbol}</h3>
              <p>类型: {opp.signal_type}</p>
              <p>置信度: {(opp.confidence * 100).toFixed(1)}%</p>
              <p>时间: {new Date(opp.triggered_at).toLocaleString()}</p>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default OpportunityList
```

---

## 🔄 WebSocket 实时推送

### 1. WebSocket 客户端

```javascript
// frontend/src/utils/websocket.js
import { API_CONFIG } from '../config/api'

class WebSocketClient {
  constructor() {
    this.ws = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000
    this.listeners = new Map()
  }

  /**
   * 连接 WebSocket
   */
  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.warn('WebSocket already connected')
      return
    }

    try {
      this.ws = new WebSocket(API_CONFIG.websocket.opportunities)

      this.ws.onopen = () => {
        console.log('✅ WebSocket connected')
        this.reconnectAttempts = 0
        this.emit('connected')
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.emit('message', data)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error)
        this.emit('error', error)
      }

      this.ws.onclose = () => {
        console.log('WebSocket disconnected')
        this.emit('disconnected')
        this.reconnect()
      }
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
    }
  }

  /**
   * 重连
   */
  reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnect attempts reached')
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * this.reconnectAttempts

    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})...`)

    setTimeout(() => {
      this.connect()
    }, delay)
  }

  /**
   * 断开连接
   */
  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /**
   * 监听事件
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event).push(callback)
  }

  /**
   * 移除监听
   */
  off(event, callback) {
    if (!this.listeners.has(event)) return

    const callbacks = this.listeners.get(event)
    const index = callbacks.indexOf(callback)
    if (index > -1) {
      callbacks.splice(index, 1)
    }
  }

  /**
   * 触发事件
   */
  emit(event, data) {
    if (!this.listeners.has(event)) return

    this.listeners.get(event).forEach((callback) => {
      callback(data)
    })
  }
}

export default new WebSocketClient()
```

### 2. React Hook

```javascript
// frontend/src/hooks/useWebSocket.js
import { useEffect, useState } from 'react'
import wsClient from '../utils/websocket'

export const useWebSocket = () => {
  const [connected, setConnected] = useState(false)
  const [messages, setMessages] = useState([])

  useEffect(() => {
    // 连接
    wsClient.connect()

    // 监听事件
    const handleConnected = () => setConnected(true)
    const handleDisconnected = () => setConnected(false)
    const handleMessage = (data) => {
      setMessages((prev) => [data, ...prev].slice(0, 100)) // 保留最近100条
    }

    wsClient.on('connected', handleConnected)
    wsClient.on('disconnected', handleDisconnected)
    wsClient.on('message', handleMessage)

    // 清理
    return () => {
      wsClient.off('connected', handleConnected)
      wsClient.off('disconnected', handleDisconnected)
      wsClient.off('message', handleMessage)
    }
  }, [])

  return { connected, messages }
}
```

### 3. 组件使用

```javascript
// frontend/src/components/RealtimeOpportunities.jsx
import React from 'react'
import { useWebSocket } from '../hooks/useWebSocket'

const RealtimeOpportunities = () => {
  const { connected, messages } = useWebSocket()

  return (
    <div className="realtime-opportunities">
      <div className="header">
        <h2>实时机会</h2>
        <span className={`status ${connected ? 'connected' : 'disconnected'}`}>
          {connected ? '🟢 已连接' : '🔴 未连接'}
        </span>
      </div>

      <div className="messages">
        {messages.length === 0 ? (
          <p>等待实时数据...</p>
        ) : (
          messages.map((msg, index) => (
            <div key={index} className="message">
              <span className="time">{new Date(msg.timestamp).toLocaleTimeString()}</span>
              <span className="symbol">{msg.symbol}</span>
              <span className="type">{msg.signal_type}</span>
              <span className="confidence">{(msg.confidence * 100).toFixed(1)}%</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default RealtimeOpportunities
```

---

## 🧪 测试与调试

### 1. 健康检查

```javascript
// frontend/src/utils/healthCheck.js
import apiClient from './api'
import { API_CONFIG } from '../config/api'

export const healthCheck = async () => {
  try {
    // 检查网关
    const gatewayHealth = await apiClient.get(API_CONFIG.endpoints.gatewayHealth)
    console.log('Gateway Health:', gatewayHealth)

    // 检查各服务
    const serviceHealth = await apiClient.get(API_CONFIG.endpoints.health)
    console.log('Service Health:', serviceHealth)

    return {
      gateway: gatewayHealth,
      service: serviceHealth,
    }
  } catch (error) {
    console.error('Health check failed:', error)
    return null
  }
}
```

### 2. 开发工具

```javascript
// frontend/src/utils/devTools.js
export const devTools = {
  // 测试 API
  async testAPI() {
    const { healthCheck } = await import('./healthCheck')
    const result = await healthCheck()
    console.table(result)
  },

  // 测试 WebSocket
  testWebSocket() {
    const wsClient = require('./websocket').default
    wsClient.on('message', (data) => {
      console.log('📨 Received:', data)
    })
    wsClient.connect()
  },

  // 模拟数据
  mockOpportunities() {
    return [
      {
        symbol: '000001.SZ',
        signal_type: 'rapid_rise',
        confidence: 0.85,
        triggered_at: new Date().toISOString(),
      },
      {
        symbol: '600036.SH',
        signal_type: 'anomaly',
        confidence: 0.72,
        triggered_at: new Date().toISOString(),
      },
    ]
  },
}

// 在浏览器控制台中可用
if (typeof window !== 'undefined') {
  window.devTools = devTools
}
```

---

## 📊 API 端点参考

### 1. 健康检查

```http
GET /health
Response: { "status": "ok" }

GET /gateway/health
Response: {
  "status": "healthy" | "degraded",
  "services": {
    "signal-api": { "status": "healthy", "response_time_ms": 5 },
    "backtest-service": { "status": "healthy", "response_time_ms": 3 }
  }
}
```

### 2. 机会查询

```http
GET /opportunities?limit=20&state=active
Response: [
  {
    "symbol": "000001.SZ",
    "signal_type": "rapid_rise",
    "confidence": 0.85,
    "strength_score": 75.5,
    "triggered_at": "2025-09-30T12:00:00Z",
    "window": "300s",
    "reasons": ["涨幅 7.5%", "量比 3.2倍"],
    "metadata": { ... }
  }
]

GET /opportunities/{symbol}
Response: { ... 单个机会详情 ... }
```

### 3. 回测

```http
POST /backtests
Request: {
  "strategy": "rapid_rise",
  "start_date": "2025-01-01",
  "end_date": "2025-09-30",
  "symbols": ["000001.SZ", "600036.SH"],
  "parameters": { ... }
}
Response: {
  "backtest_id": "bt_xxxxx",
  "status": "running" | "completed",
  "results": { ... }
}

GET /backtests/{id}
Response: { ... 回测结果 ... }
```

---

## 🚀 部署配置

### 环境变量

```bash
# .env.production
REACT_APP_API_GATEWAY=https://api.dongfengpo.com
REACT_APP_WS_URL=wss://ws.dongfengpo.com/opportunities
REACT_APP_ENV=production
```

### Nginx 配置

```nginx
# nginx.conf
server {
    listen 80;
    server_name dongfengpo.com;

    # 前端静态文件
    location / {
        root /var/www/frontend/build;
        try_files $uri /index.html;
    }

    # API 代理
    location /api {
        proxy_pass http://localhost:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket 代理
    location /ws {
        proxy_pass http://localhost:8100;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 📝 最佳实践

1. **错误处理**: 始终处理API错误，提供友好提示
2. **加载状态**: 显示加载动画，提升用户体验
3. **数据缓存**: 使用React Query或SWR缓存数据
4. **请求去重**: 避免重复请求
5. **WebSocket重连**: 实现自动重连机制
6. **性能优化**: 使用虚拟滚动、分页加载
7. **安全性**: HTTPS、token认证、XSS防护

---

**文档版本**: v1.0
**最后更新**: 2025-09-30
**维护者**: Phase 3 Team