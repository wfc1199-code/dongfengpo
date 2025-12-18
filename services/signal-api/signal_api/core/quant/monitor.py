"""
性能监控模块 (Performance Monitor)

P2改进：添加性能监控和错误告警
- 请求计时
- 错误追踪
- 缓存命中率
- 告警阈值
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import deque
import time
import logging
import threading

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """单个指标点"""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlertConfig:
    """告警配置"""
    # 响应时间告警阈值（秒）
    slow_response_threshold: float = 5.0
    
    # 错误率告警阈值（%）
    error_rate_threshold: float = 10.0
    
    # 缓存命中率告警阈值（%）
    cache_hit_rate_min: float = 50.0
    
    # 告警静默期（秒）
    alert_cooldown: float = 300.0


class PerformanceMonitor:
    """
    性能监控器
    
    Usage:
        monitor = PerformanceMonitor()
        
        with monitor.track("scoring"):
            result = scorer.score(metrics)
        
        monitor.record_error("ai_review", error)
        stats = monitor.get_stats()
    """
    
    def __init__(
        self,
        alert_config: Optional[AlertConfig] = None,
        max_history: int = 1000
    ):
        """初始化监控器"""
        self.config = alert_config or AlertConfig()
        self.max_history = max_history
        
        # 指标存储
        self._timings: Dict[str, deque] = {}
        self._errors: Dict[str, deque] = {}
        self._counters: Dict[str, int] = {}
        
        # 告警状态
        self._last_alert_time: Dict[str, float] = {}
        
        # 线程安全锁
        self._lock = threading.Lock()
        
        logger.info("PerformanceMonitor initialized")
    
    class Tracker:
        """计时追踪器上下文管理器"""
        def __init__(self, monitor: 'PerformanceMonitor', name: str):
            self.monitor = monitor
            self.name = name
            self.start_time = None
        
        def __enter__(self):
            self.start_time = time.time()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = time.time() - self.start_time
            self.monitor._record_timing(self.name, duration)
            
            if exc_type:
                self.monitor.record_error(self.name, str(exc_val))
            
            return False  # 不吞掉异常
    
    def track(self, name: str) -> Tracker:
        """创建计时追踪器"""
        return self.Tracker(self, name)
    
    def _record_timing(self, name: str, duration: float):
        """记录执行时间"""
        with self._lock:
            if name not in self._timings:
                self._timings[name] = deque(maxlen=self.max_history)
            
            self._timings[name].append(MetricPoint(
                name=name,
                value=duration,
                tags={"type": "timing"}
            ))
            
            # 增加计数器
            self._counters[f"{name}_count"] = self._counters.get(f"{name}_count", 0) + 1
        
        # 检查慢响应告警
        if duration > self.config.slow_response_threshold:
            self._trigger_alert(
                f"slow_{name}",
                f"慢响应告警: {name} 耗时 {duration:.2f}s 超过阈值 {self.config.slow_response_threshold}s"
            )
    
    def record_error(self, name: str, error: str):
        """记录错误"""
        with self._lock:
            if name not in self._errors:
                self._errors[name] = deque(maxlen=self.max_history)
            
            self._errors[name].append(MetricPoint(
                name=name,
                value=1.0,
                tags={"type": "error", "message": error[:100]}
            ))
            
            self._counters[f"{name}_errors"] = self._counters.get(f"{name}_errors", 0) + 1
        
        logger.error(f"[Monitor] Error in {name}: {error}")
    
    def record_cache(self, name: str, hits: int, misses: int):
        """记录缓存命中率"""
        total = hits + misses
        if total == 0:
            return
        
        hit_rate = (hits / total) * 100
        
        with self._lock:
            self._counters[f"{name}_cache_hits"] = hits
            self._counters[f"{name}_cache_misses"] = misses
            self._counters[f"{name}_cache_hit_rate"] = hit_rate
        
        # 检查低命中率告警
        if hit_rate < self.config.cache_hit_rate_min and total > 100:
            self._trigger_alert(
                f"low_cache_{name}",
                f"缓存命中率告警: {name} 命中率 {hit_rate:.1f}% 低于阈值 {self.config.cache_hit_rate_min}%"
            )
    
    def _trigger_alert(self, alert_id: str, message: str):
        """触发告警（带静默期）"""
        now = time.time()
        
        with self._lock:
            last_time = self._last_alert_time.get(alert_id, 0)
            
            if now - last_time >= self.config.alert_cooldown:
                self._last_alert_time[alert_id] = now
                logger.warning(f"[ALERT] {message}")
                # 这里可以扩展：发送钉钉、邮件等通知
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        with self._lock:
            stats = {
                "counters": dict(self._counters),
                "timings": {},
                "errors": {},
            }
            
            # 计算各操作的平均/最大耗时
            for name, timings in self._timings.items():
                if timings:
                    values = [p.value for p in timings]
                    stats["timings"][name] = {
                        "count": len(values),
                        "avg_ms": round(sum(values) / len(values) * 1000, 2),
                        "max_ms": round(max(values) * 1000, 2),
                        "min_ms": round(min(values) * 1000, 2),
                    }
            
            # 计算错误率
            for name, errors in self._errors.items():
                total_count = self._counters.get(f"{name}_count", 0)
                error_count = len(errors)
                error_rate = (error_count / total_count * 100) if total_count > 0 else 0
                
                stats["errors"][name] = {
                    "count": error_count,
                    "rate": round(error_rate, 2),
                }
            
            return stats
    
    def reset(self):
        """重置所有指标"""
        with self._lock:
            self._timings.clear()
            self._errors.clear()
            self._counters.clear()
            self._last_alert_time.clear()
        logger.info("PerformanceMonitor reset")


# 全局监控器实例
_monitor: Optional[PerformanceMonitor] = None


def get_monitor() -> PerformanceMonitor:
    """获取全局监控器实例"""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor
