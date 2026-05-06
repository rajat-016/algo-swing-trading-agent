"""
Retry decorator with exponential backoff for handling transient errors.
Useful for API calls, network operations, and other transient failures.
"""

import time
import logging
from functools import wraps
from typing import Callable, Type, Tuple, Optional, Union
from core.exceptions import RateLimitError, ZerodhaError

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    max_backoff: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Decorator that retries a function with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for backoff (2.0 = double the delay each time)
        max_backoff: Maximum backoff time in seconds
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback called on each retry (exception, attempt_number)
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    # Check if we should retry
                    if attempt < max_retries:
                        # Calculate backoff time
                        backoff_time = min(max_backoff, backoff_factor ** attempt)
                        
                        # If it's a rate limit error, use retry_after if available
                        if isinstance(e, RateLimitError) and 'retry_after' in e.details:
                            backoff_time = min(max_backoff, e.details['retry_after'])
                        
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {backoff_time:.1f}s..."
                        )
                        
                        if on_retry:
                            on_retry(e, attempt + 1)
                        
                        time.sleep(backoff_time)
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {e}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


def retry_async_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    max_backoff: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Async version of retry_with_backoff decorator.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        backoff_time = min(max_backoff, backoff_factor ** attempt)
                        
                        if isinstance(e, RateLimitError) and 'retry_after' in e.details:
                            backoff_time = min(max_backoff, e.details['retry_after'])
                        
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {backoff_time:.1f}s..."
                        )
                        
                        if on_retry:
                            on_retry(e, attempt + 1)
                        
                        import asyncio
                        await asyncio.sleep(backoff_time)
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {e}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator
