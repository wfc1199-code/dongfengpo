# Phase 5 Week 2 实现方案审查报告

**审查日期**: 2025-01-XX  
**审查范围**: 定时任务实现方案 + 前端联调方案  
**审查维度**: 架构设计、集成兼容性、错误处理、可维护性

---

## 📋 审查概览

| 模块 | 设计完整性 | 技术可行性 | 集成兼容性 | 总体评分 |
|------|-----------|-----------|-----------|----------|
| 定时任务 (APScheduler) | ⚠️ 需补充 | ✅ 可行 | ⚠️ 需验证 | ⚠️ 需改进 |
| 前端联调方案 | ⚠️ 未提供 | ✅ 可行 | ✅ 良好 | ⚠️ 需补充 |

**总体评估**: ⚠️ **需补充细节** - 核心思路正确，但需要完善实现细节和前端联调方案

---

## 🔍 详细审查

### 1. 定时任务实现方案

#### 当前方案分析

**提供的代码片段**:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

# 16:30 - 同步分钟线
scheduler.add_job(
    sync_today_minute,
    CronTrigger(hour=16, minute=30),
    id="sync_minute",
    replace_existing=True,
    misfire_grace_time=300,
    max_instances=1
)

# 16:35 - 同步日线
scheduler.add_job(
    sync_today_daily,
    CronTrigger(hour=16, minute=35),
    id="sync_daily"
)

# 16:40 - 数据校验
scheduler.add_job(
    validate_today_data,
    CronTrigger(hour=16, minute=40),
    id="validate_data"
)
```

#### 审查意见

**优点**:
- ✅ **时区配置正确**: 使用 `Asia/Shanghai` 时区
- ✅ **任务时间合理**: 16:30/16:35/16:40 分步执行，避免冲突
- ✅ **容错机制**: `misfire_grace_time=300` 允许 5 分钟容错
- ✅ **并发控制**: `max_instances=1` 防止重复执行

**问题**:
- ❌ **函数未定义**: `sync_today_minute`、`sync_today_daily`、`validate_today_data` 函数未实现
- ❌ **缺少 DataManager 集成**: 没有调用 Week 1 实现的 `DataManager`
- ❌ **缺少错误处理**: 没有重试机制和异常处理
- ❌ **缺少任务依赖**: 16:35 的日线同步应该依赖 16:30 的分钟线完成
- ❌ **缺少任务监控**: 没有任务执行状态记录和告警
- ❌ **缺少生命周期管理**: 没有在 `app.py` 中启动和关闭调度器

**修复建议**:

1. **完整的调度器实现**:
```python
# services/signal-api/signal_api/core/quant/scheduler.py

import asyncio
import logging
from datetime import datetime, date
from typing import Dict, Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, JobExecutionEvent
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from tenacity import retry, stop_after_attempt, wait_fixed

from .data.manager import DataManager, DataManagerConfig

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None
_data_manager: Optional[DataManager] = None


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(
            timezone="Asia/Shanghai",
            jobstores={'default': MemoryJobStore()},
            executors={'default': AsyncIOExecutor()}
        )
    return _scheduler


def get_data_manager() -> DataManager:
    """Get or create the global DataManager instance."""
    global _data_manager
    if _data_manager is None:
        config = DataManagerConfig()
        _data_manager = DataManager(config)
    return _data_manager


# ==================== Scheduled Tasks ====================

@retry(stop=stop_after_attempt(3), wait=wait_fixed(60))
async def sync_today_minute():
    """
    Sync today's minute-level data for all tracked symbols.
    
    Scheduled at 16:30 (after market close).
    """
    logger.info("Starting minute data sync at 16:30")
    start_time = datetime.now()
    
    try:
        dm = get_data_manager()
        result = await dm.sync_today()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Minute data sync completed: {result['synced']} success, "
            f"{result['failed']} failed in {elapsed:.1f}s"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Minute data sync failed: {e}", exc_info=True)
        raise


@retry(stop=stop_after_attempt(3), wait=wait_fixed(60))
async def sync_today_daily():
    """
    Sync today's daily data for all tracked symbols.
    
    Scheduled at 16:35 (after minute sync).
    Depends on minute sync completion.
    """
    logger.info("Starting daily data sync at 16:35")
    start_time = datetime.now()
    
    try:
        # Check if minute sync completed (optional check)
        # In production, you might want to check a status flag
        
        dm = get_data_manager()
        today = datetime.now().date()
        
        # Get stock list
        stocks = dm.tushare.get_stock_list()
        symbols = stocks["ts_code"].tolist()[:50]  # Limit for safety
        
        synced = 0
        failed = 0
        
        for ts_code in symbols:
            try:
                # Fetch daily data
                await dm.rate_limiter.acquire()
                daily_df = dm.tushare.pro.daily(
                    ts_code=ts_code,
                    start_date=today.strftime("%Y%m%d"),
                    end_date=today.strftime("%Y%m%d")
                )
                
                if daily_df is not None and not daily_df.empty:
                    daily_df["ts_code"] = ts_code
                    dm.duckdb.upsert_daily(daily_df)
                    synced += 1
                else:
                    logger.warning(f"No daily data for {ts_code} on {today}")
                    failed += 1
                    
            except Exception as e:
                logger.error(f"Failed to sync daily {ts_code}: {e}")
                failed += 1
            
            # Rate limit between symbols
            await asyncio.sleep(0.2)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Daily data sync completed: {synced} success, "
            f"{failed} failed in {elapsed:.1f}s"
        )
        
        return {"synced": synced, "failed": failed}
        
    except Exception as e:
        logger.error(f"Daily data sync failed: {e}", exc_info=True)
        raise


@retry(stop=stop_after_attempt(2), wait=wait_fixed(30))
async def validate_today_data():
    """
    Validate today's data completeness for all synced symbols.
    
    Scheduled at 16:40 (after both syncs complete).
    Checks for 240 K-lines completeness (>= 95%).
    """
    logger.info("Starting data validation at 16:40")
    start_time = datetime.now()
    
    try:
        dm = get_data_manager()
        result = await dm.validate_today()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        if result["failed"] > 0:
            logger.warning(
                f"Data validation completed: {result['passed']} passed, "
                f"{result['failed']} failed in {elapsed:.1f}s. "
                f"Failed symbols: {result['failed_symbols']}"
            )
            # TODO: Send alert notification
        else:
            logger.info(
                f"Data validation passed: {result['passed']} symbols "
                f"in {elapsed:.1f}s"
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Data validation failed: {e}", exc_info=True)
        raise


# ==================== Scheduler Setup ====================

def setup_scheduler():
    """Setup and configure the scheduler with all jobs."""
    scheduler = get_scheduler()
    
    # 16:30 - Sync minute data
    scheduler.add_job(
        sync_today_minute,
        CronTrigger(hour=16, minute=30, timezone="Asia/Shanghai"),
        id="sync_minute",
        replace_existing=True,
        misfire_grace_time=300,  # 5 minutes
        max_instances=1,
        coalesce=True,  # Combine multiple pending executions
        name="Sync Minute Data"
    )
    
    # 16:35 - Sync daily data
    scheduler.add_job(
        sync_today_daily,
        CronTrigger(hour=16, minute=35, timezone="Asia/Shanghai"),
        id="sync_daily",
        replace_existing=True,
        misfire_grace_time=300,
        max_instances=1,
        coalesce=True,
        name="Sync Daily Data"
    )
    
    # 16:40 - Validate data
    scheduler.add_job(
        validate_today_data,
        CronTrigger(hour=16, minute=40, timezone="Asia/Shanghai"),
        id="validate_data",
        replace_existing=True,
        misfire_grace_time=300,
        max_instances=1,
        coalesce=True,
        name="Validate Data"
    )
    
    # Add job event listeners
    def job_listener(event: JobExecutionEvent):
        if event.exception:
            logger.error(
                f"Job {event.job_id} ({event.jobstore_alias}) failed: {event.exception}",
                exc_info=event.exception
            )
            # TODO: Send alert notification
        else:
            logger.info(f"Job {event.job_id} completed successfully")
    
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    
    logger.info("Scheduler configured with 3 jobs: sync_minute, sync_daily, validate_data")
    
    return scheduler


def start_scheduler():
    """Start the scheduler."""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("Quant scheduler started")
    else:
        logger.warning("Scheduler is already running")


def stop_scheduler():
    """Stop the scheduler gracefully."""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Quant scheduler stopped")
    else:
        logger.warning("Scheduler is not running")
```

2. **在 app.py 中集成调度器**:
```python
# services/signal-api/signal_api/app.py

from contextlib import asynccontextmanager
from .core.quant.scheduler import setup_scheduler, start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Signal API application")
    
    # Setup and start scheduler
    setup_scheduler()
    start_scheduler()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Signal API application")
    stop_scheduler()

def create_app(lifespan=lifespan) -> FastAPI:
    """Create FastAPI app with optional lifespan."""
    app = FastAPI(
        title="Opportunity Signal API", 
        version="1.0.0",
        lifespan=lifespan
    )
    # ... rest of the code
```

3. **添加任务状态查询 API**:
```python
# services/signal-api/signal_api/routers/quant.py

@router.get("/scheduler/status")
async def get_scheduler_status():
    """Get scheduler and job status."""
    from ..core.quant.scheduler import get_scheduler
    
    scheduler = get_scheduler()
    jobs = []
    
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    return {
        "scheduler_running": scheduler.running,
        "jobs": jobs
    }
```

---

### 2. 前端联调方案

#### 当前状态
**问题**: 用户未提供完整的前端联调方案

#### 审查意见

基于 Week 1 的 API 设计和现有的 `QuantDashboard.tsx`，建议以下联调方案：

**1. API 集成**:
```typescript
// frontend/src/services/quantApi.ts

const API_BASE = 'http://localhost:8000/api/quant';

export interface EngineStatus {
  engine_running: boolean;
  mode: string;
  capital: number;
  position_count: number;
  daily_pnl: number;
  daily_pnl_pct: number;
  max_drawdown: number;
  strategies: string[];
  last_signal: string | null;
  data_status: {
    last_sync: string | null;
    symbols_synced: number;
    validation_passed: boolean;
  };
}

export const quantApi = {
  // GET /api/quant/status
  async getStatus(): Promise<EngineStatus> {
    const response = await fetch(`${API_BASE}/status`);
    if (!response.ok) throw new Error('Failed to get status');
    return response.json();
  },
  
  // POST /api/quant/start
  async startEngine(symbols: string[], strategies: string[], mode: string) {
    const response = await fetch(`${API_BASE}/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbols, strategies, mode })
    });
    if (!response.ok) throw new Error('Failed to start engine');
    return response.json();
  },
  
  // POST /api/quant/stop
  async stopEngine() {
    const response = await fetch(`${API_BASE}/stop`, {
      method: 'POST'
    });
    if (!response.ok) throw new Error('Failed to stop engine');
    return response.json();
  },
  
  // GET /api/quant/positions
  async getPositions() {
    const response = await fetch(`${API_BASE}/positions`);
    if (!response.ok) throw new Error('Failed to get positions');
    return response.json();
  },
  
  // POST /api/quant/sync
  async syncData(symbol?: string) {
    const response = await fetch(`${API_BASE}/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol })
    });
    if (!response.ok) throw new Error('Failed to sync data');
    return response.json();
  }
};
```

**2. WebSocket 集成**:
```typescript
// frontend/src/hooks/useQuantWebSocket.ts

import { useEffect, useRef, useState } from 'react';

export interface QuantSignal {
  type: 'quant_signal';
  payload: {
    symbol: string;
    signal_type: 'buy' | 'sell' | 'hold';
    confidence: number;
    price: number;
    strategy: string;
    reason: string;
    timestamp: number;
  };
  timestamp: string;
}

export function useQuantWebSocket(enabled: boolean) {
  const [signals, setSignals] = useState<QuantSignal[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  
  useEffect(() => {
    if (!enabled) {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setConnected(false);
      return;
    }
    
    const ws = new WebSocket('ws://localhost:8000/api/quant/signals');
    wsRef.current = ws;
    
    ws.onopen = () => {
      setConnected(true);
      console.log('Quant WebSocket connected');
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'quant_signal') {
          setSignals(prev => [data, ...prev].slice(0, 50));
        } else if (data.type === 'heartbeat') {
          // Handle heartbeat
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
      setConnected(false);
      console.log('Quant WebSocket disconnected');
    };
    
    return () => {
      ws.close();
    };
  }, [enabled]);
  
  return { signals, connected };
}
```

**3. 更新 QuantDashboard 组件**:
```typescript
// frontend/src/components/QuantDashboard.tsx

import { quantApi, EngineStatus } from '../services/quantApi';
import { useQuantWebSocket } from '../hooks/useQuantWebSocket';

const QuantDashboard: React.FC<QuantDashboardProps> = ({ onStockSelect }) => {
  const [status, setStatus] = useState<EngineStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const { signals, connected } = useQuantWebSocket(isRunning);
  
  // Fetch status on mount and periodically
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await quantApi.getStatus();
        setStatus(data);
        setIsRunning(data.engine_running);
        setIsSimulation(data.mode === 'simulation');
      } catch (e) {
        console.error('Failed to fetch status:', e);
      }
    };
    
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000); // Poll every 5s
    
    return () => clearInterval(interval);
  }, []);
  
  // Update signals from WebSocket
  useEffect(() => {
    if (signals.length > 0) {
      const latest = signals[0];
      setSignals(prev => {
        // Convert WebSocket signal to SignalData format
        const signalData: SignalData = {
          id: `sig_${latest.payload.timestamp}`,
          symbol: latest.payload.symbol,
          signal_type: latest.payload.signal_type,
          confidence: latest.payload.confidence,
          price: latest.payload.price,
          time: new Date(latest.payload.timestamp * 1000).toLocaleTimeString(),
          reason: latest.payload.reason,
          strategy: latest.payload.strategy
        };
        return [signalData, ...prev].slice(0, 20);
      });
    }
  }, [signals]);
  
  // Update connection status
  useEffect(() => {
    setConnectionStatus(connected ? 'connected' : 'disconnected');
  }, [connected]);
  
  // Toggle engine
  const toggleEngine = useCallback(async () => {
    setLoading(true);
    try {
      if (isRunning) {
        await quantApi.stopEngine();
      } else {
        await quantApi.startEngine(
          ['000001', '600000'],
          ['Ambush'],
          isSimulation ? 'simulation' : 'live'
        );
      }
      // Status will be updated by polling
    } catch (e) {
      console.error('Failed to toggle engine:', e);
    } finally {
      setLoading(false);
    }
  }, [isRunning, isSimulation]);
  
  // ... rest of the component
};
```

---

## 📊 总体建议

### 1. 立即补充 (P0)
1. ✅ **实现调度器函数**: `sync_today_minute`、`sync_today_daily`、`validate_today_data`
2. ✅ **集成 DataManager**: 调用 Week 1 实现的 `DataManager.sync_today()` 和 `validate_today()`
3. ✅ **添加生命周期管理**: 在 `app.py` 中启动和关闭调度器
4. ✅ **添加错误处理**: 重试机制和异常处理

### 2. 尽快完善 (P1)
1. ⚠️ **添加任务依赖检查**: 16:35 任务检查 16:30 任务是否完成
2. ⚠️ **添加任务监控**: 任务执行状态记录和告警
3. ⚠️ **前端 API 集成**: 实现 `quantApi.ts` 和 `useQuantWebSocket.ts`
4. ⚠️ **更新 QuantDashboard**: 集成真实 API 调用

### 3. 计划优化 (P2)
1. ℹ️ **任务状态 API**: 添加 `/api/quant/scheduler/status` 端点
2. ℹ️ **前端错误处理**: 添加错误提示和重试逻辑
3. ℹ️ **性能优化**: 减少不必要的 API 调用

---

## ✅ 符合项（优点）

1. **技术选型合理**: APScheduler 是成熟的异步任务调度库
2. **时区配置正确**: 使用 `Asia/Shanghai` 时区
3. **任务时间合理**: 分步执行避免冲突
4. **容错机制**: `misfire_grace_time` 和 `max_instances` 配置合理

---

## 🎯 实施建议

### Week 2 Day 1-2: 定时任务实现
1. 创建 `scheduler.py` 文件
2. 实现三个定时任务函数
3. 集成 DataManager
4. 在 `app.py` 中添加生命周期管理
5. 测试任务执行

### Week 2 Day 3-4: 前端 API 集成
1. 创建 `quantApi.ts` 服务
2. 创建 `useQuantWebSocket.ts` hook
3. 更新 `QuantDashboard.tsx` 组件
4. 测试 API 调用和 WebSocket 连接

### Week 2 Day 5: 联调和测试
1. 端到端测试
2. 错误处理测试
3. 性能测试
4. 文档更新

---

## 📝 总结

Phase 5 Week 2 实现方案的**核心思路正确**，但需要**补充实现细节**。主要问题：

1. **函数未实现**: 需要实现三个定时任务函数
2. **缺少集成**: 需要集成 Week 1 的 DataManager
3. **前端方案缺失**: 需要提供完整的前端联调方案

建议按照实施建议逐步实现，重点关注与 Week 1 的集成和错误处理。

---

**审查完成时间**: 2025-01-XX  
**下次审查建议**: 实现完成后进行代码审查



