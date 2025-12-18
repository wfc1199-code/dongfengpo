
import asyncio
import logging
from functools import wraps
from typing import Callable, Type, Tuple, Union

logger = logging.getLogger(__name__)

def async_retry(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    异步重试装饰器
    
    Args:
        retries: 最大重试次数
        delay: 初始延迟秒数
        backoff: 延迟倍数
        exceptions: 需要重试的异常类型
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < retries:
                        logger.warning(
                            f"Execution of {func.__name__} failed ({e}). "
                            f"Retrying in {current_delay}s... (Attempt {attempt + 1}/{retries})"
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"Execution of {func.__name__} failed after {retries} retries.")
            
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator
