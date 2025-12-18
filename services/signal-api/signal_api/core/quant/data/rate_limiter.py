"""
AI Quant Platform - Rate Limiter
Token bucket rate limiter for Tushare API calls.

Configuration based on 5120 积分 = 500 requests/min limit.
Using 400/min (80% of limit) for safety margin.
"""

import asyncio
import time
import logging
import threading
from dataclasses import dataclass
from typing import Optional
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_minute: int = 400  # 80% of 500 limit
    min_interval_ms: int = 150      # 60000 / 400
    burst_limit: int = 10           # Allow burst of 10 requests
    retry_on_429: bool = True
    retry_delay_seconds: float = 5.0
    max_retries: int = 3


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for API calls.
    
    Features:
    - Token bucket algorithm with burst support
    - Async-safe with lock
    - Automatic token refill
    - Request waiting when bucket empty
    
    Usage:
        limiter = TokenBucketRateLimiter(config)
        await limiter.acquire()  # Wait for token
        # Make API call
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        
        # Token bucket
        self.tokens = float(self.config.burst_limit)
        self.max_tokens = float(self.config.burst_limit)
        self.refill_rate = self.config.requests_per_minute / 60.0  # tokens per second
        self.last_refill = time.monotonic()
        
        # Async lock
        self._lock = asyncio.Lock()
        
        # Stats
        self._total_requests = 0
        self._total_waits = 0
        self._total_wait_time = 0.0
        
        logger.info(
            f"RateLimiter initialized: {self.config.requests_per_minute}/min, "
            f"burst={self.config.burst_limit}, interval={self.config.min_interval_ms}ms"
        )
    
    def _refill_tokens(self):
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + new_tokens)
        self.last_refill = now
    
    async def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire a token, waiting if necessary.
        
        Args:
            timeout: Maximum seconds to wait. None = wait forever.
        
        Returns:
            True if token acquired, False if timeout.
        """
        start_time = time.monotonic()
        
        while True:
            wait_time = 0.0
            
            async with self._lock:
                self._refill_tokens()
                
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    self._total_requests += 1
                    return True
                
                # Calculate wait time (but don't sleep inside lock)
                tokens_needed = 1.0 - self.tokens
                wait_time = tokens_needed / self.refill_rate
                
                # Check timeout
                if timeout is not None:
                    elapsed = time.monotonic() - start_time
                    if elapsed + wait_time > timeout:
                        logger.warning(f"Rate limit timeout after {elapsed:.2f}s")
                        return False
                
                self._total_waits += 1
                self._total_wait_time += wait_time
            
            # Sleep OUTSIDE the lock to not block other coroutines
            logger.debug(f"Rate limit: waiting {wait_time:.3f}s for token")
            await asyncio.sleep(wait_time)
    
    async def acquire_sync(self) -> bool:
        """Synchronous-compatible acquire (for use in sync code via asyncio.run)."""
        return await self.acquire()
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        return {
            "total_requests": self._total_requests,
            "total_waits": self._total_waits,
            "total_wait_time_seconds": round(self._total_wait_time, 2),
            "current_tokens": round(self.tokens, 2),
            "requests_per_minute": self.config.requests_per_minute,
        }
    
    def reset(self):
        """Reset the rate limiter."""
        self.tokens = float(self.config.burst_limit)
        self.last_refill = time.monotonic()
        self._total_requests = 0
        self._total_waits = 0
        self._total_wait_time = 0.0


# Global rate limiter instance (singleton with double-check locking)
_global_limiter: Optional[TokenBucketRateLimiter] = None
_singleton_lock = threading.Lock()


def get_rate_limiter(config: Optional[RateLimitConfig] = None) -> TokenBucketRateLimiter:
    """Get or create the global rate limiter instance (thread-safe)."""
    global _global_limiter
    if _global_limiter is None:
        with _singleton_lock:
            # Double-check after acquiring lock
            if _global_limiter is None:
                _global_limiter = TokenBucketRateLimiter(config)
    return _global_limiter


def rate_limited(func):
    """
    Decorator to rate limit async function calls.
    
    Usage:
        @rate_limited
        async def call_tushare_api():
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        limiter = get_rate_limiter()
        await limiter.acquire()
        return await func(*args, **kwargs)
    return wrapper


def rate_limited_sync(func):
    """
    Decorator to rate limit sync function calls.
    Converts sync function to run rate limiting synchronously.
    
    Usage:
        @rate_limited_sync
        def call_tushare_api():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        limiter = get_rate_limiter()
        # For sync calls, we use a simple sleep-based approach
        min_interval = limiter.config.min_interval_ms / 1000.0
        time.sleep(min_interval)
        return func(*args, **kwargs)
    return wrapper
