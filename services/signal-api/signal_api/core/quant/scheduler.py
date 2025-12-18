"""
AI Quant Platform - Scheduler
Handles scheduled data synchronization and validation tasks.

Tasks:
- 16:30 - Sync today's minute data
- 16:35 - Sync today's daily data
- 16:40 - Validate data completeness
"""

import asyncio
import logging
import threading
import functools
from datetime import datetime
from typing import Optional, Callable, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

logger = logging.getLogger(__name__)

# Thread-safe singleton lock
_scheduler_lock = threading.Lock()
_scheduler: Optional[AsyncIOScheduler] = None

# Shared DataManager instance (created once)
_data_manager = None
_data_manager_lock = threading.Lock()


def get_data_manager():
    """Get or create the shared DataManager instance (thread-safe)."""
    global _data_manager
    if _data_manager is None:
        with _data_manager_lock:
            if _data_manager is None:
                from .data import DataManager
                _data_manager = DataManager()
                logger.info("Shared DataManager created")
    return _data_manager


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the global scheduler instance (thread-safe)."""
    global _scheduler
    if _scheduler is None:
        with _scheduler_lock:
            # Double-check after acquiring lock
            if _scheduler is None:
                _scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
                _setup_event_listeners(_scheduler)
                logger.info("Scheduler instance created")
    return _scheduler


def _setup_event_listeners(scheduler: AsyncIOScheduler):
    """Setup job event listeners for logging and monitoring."""
    
    def job_executed_listener(event):
        logger.info(f"Job executed: {event.job_id}")
    
    def job_error_listener(event):
        logger.error(f"Job failed: {event.job_id}, exception: {event.exception}")
    
    scheduler.add_listener(job_executed_listener, EVENT_JOB_EXECUTED)
    scheduler.add_listener(job_error_listener, EVENT_JOB_ERROR)


# ==================== Retry Decorator ====================

def async_retry(max_retries: int = 3, delay_seconds: float = 60.0, backoff: float = 2.0):
    """
    Decorator for async functions with retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay_seconds: Initial delay between retries
        backoff: Multiplier for delay on each retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            delay = delay_seconds
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {delay:.0f}s..."
                        )
                        await asyncio.sleep(delay)
                        delay *= backoff
                    else:
                        logger.error(f"{func.__name__} failed after {max_retries + 1} attempts: {e}")
            
            # Return error result instead of raising
            return {"synced": 0, "failed": 0, "error": str(last_exception)}
        return wrapper
    return decorator


# ==================== Task Functions ====================

@async_retry(max_retries=3, delay_seconds=60.0)
async def sync_today_minute():
    """
    Sync today's minute data from Tushare to DuckDB.
    Runs at 16:30 daily after market close.
    """
    logger.info("Starting minute data sync task")
    start_time = datetime.now()
    
    try:
        data_manager = get_data_manager()
        result = await data_manager.sync_today()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Minute sync completed in {elapsed:.1f}s: "
            f"synced={result.get('synced', 0)}, failed={result.get('failed', 0)}"
        )
        
        return result
        
    except ImportError as e:
        logger.error(f"DataManager not available: {e}")
        raise  # Let retry handle it


@async_retry(max_retries=3, delay_seconds=60.0)
async def sync_today_daily():
    """
    Sync today's daily data from Tushare to DuckDB.
    Runs at 16:35 daily after market close.
    """
    logger.info("Starting daily data sync task")
    start_time = datetime.now()
    
    try:
        data_manager = get_data_manager()
        
        # Get tracked symbols from engine state or default list
        try:
            from ...routers.quant import get_engine_state
            state = get_engine_state()
            symbols = state.symbols if state.symbols else ["000001", "600000"]
        except ImportError:
            symbols = ["000001", "600000"]
        
        synced = 0
        failed = 0
        
        for symbol in symbols[:50]:  # Limit for safety
            try:
                df = data_manager.get_daily(symbol, days=1)
                if len(df) > 0:
                    synced += 1
                else:
                    failed += 1
            except Exception as e:
                logger.warning(f"Failed to sync daily for {symbol}: {e}")
                failed += 1
            
            # Small delay between requests
            await asyncio.sleep(0.2)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Daily sync completed in {elapsed:.1f}s: synced={synced}, failed={failed}")
        
        return {"synced": synced, "failed": failed}
        
    except ImportError as e:
        logger.error(f"DataManager not available: {e}")
        raise  # Let retry handle it


@async_retry(max_retries=2, delay_seconds=30.0)
async def validate_today_data():
    """
    Validate today's data completeness.
    Runs at 16:40 daily after sync tasks.
    """
    logger.info("Starting data validation task")
    start_time = datetime.now()
    
    try:
        data_manager = get_data_manager()
        result = await data_manager.validate_today()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        if result.get("failed", 0) > 0:
            logger.warning(
                f"Validation completed in {elapsed:.1f}s with issues: "
                f"passed={result.get('passed', 0)}, failed={result.get('failed', 0)}, "
                f"failed_symbols={result.get('failed_symbols', [])[:5]}"
            )
        else:
            logger.info(f"Validation completed in {elapsed:.1f}s: all passed")
        
        # Update engine state with validation result
        try:
            from ...routers.quant import get_engine_state
            state = get_engine_state()
            state.validation_passed = result.get("failed", 0) == 0
            state.last_sync_time = datetime.now().isoformat()
        except ImportError:
            pass
        
        return result
        
    except ImportError as e:
        logger.error(f"DataManager not available: {e}")
        raise  # Let retry handle it


# ==================== Scheduler Setup ====================

def setup_scheduled_jobs(scheduler: AsyncIOScheduler):
    """Configure all scheduled jobs."""
    
    # 16:30 - Sync minute data
    scheduler.add_job(
        sync_today_minute,
        CronTrigger(hour=16, minute=30, timezone="Asia/Shanghai"),
        id="sync_minute",
        name="Sync Today Minute Data",
        replace_existing=True,
        misfire_grace_time=300,  # 5 minutes grace period
        max_instances=1,
        coalesce=True,  # Combine missed executions
    )
    
    # 16:35 - Sync daily data
    scheduler.add_job(
        sync_today_daily,
        CronTrigger(hour=16, minute=35, timezone="Asia/Shanghai"),
        id="sync_daily",
        name="Sync Today Daily Data",
        replace_existing=True,
        misfire_grace_time=300,
        max_instances=1,
        coalesce=True,
    )
    
    # 16:40 - Validate data
    scheduler.add_job(
        validate_today_data,
        CronTrigger(hour=16, minute=40, timezone="Asia/Shanghai"),
        id="validate_data",
        name="Validate Today Data",
        replace_existing=True,
        misfire_grace_time=300,
        max_instances=1,
        coalesce=True,
    )
    
    logger.info("Scheduled jobs configured: sync_minute (16:30), sync_daily (16:35), validate_data (16:40)")


def start_scheduler():
    """Start the scheduler with all configured jobs."""
    scheduler = get_scheduler()
    
    if not scheduler.running:
        setup_scheduled_jobs(scheduler)
        scheduler.start()
        logger.info("Scheduler started")
    else:
        logger.warning("Scheduler already running")


def stop_scheduler():
    """Stop the scheduler gracefully."""
    global _scheduler
    
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")
    
    _scheduler = None


def get_scheduler_status() -> dict:
    """Get scheduler status and job information."""
    scheduler = get_scheduler()
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "pending": job.pending,
        })
    
    return {
        "running": scheduler.running,
        "jobs": jobs,
        "timezone": str(scheduler.timezone),
    }
