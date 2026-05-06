"""
Circuit breaker pattern implementation to prevent cascading failures.
Useful for protecting external services like Zerodha API.
"""

import time
import logging
from enum import Enum
from typing import Callable, Any, Optional
from core.exceptions import CircuitBreakerError

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failing, reject calls
    HALF_OPEN = "HALF_OPEN"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit is tripped, requests fail fast
    - HALF_OPEN: After timeout, allows one request to test recovery
    
    Usage:
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        
        try:
            result = breaker.call(risky_function, *args, **kwargs)
        except CircuitBreakerError:
            # Handle circuit open
            pass
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception,
        name: Optional[str] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type that triggers the breaker
            name: Optional name for logging
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name or "CircuitBreaker"
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._success_count = 0
        
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)."""
        return self._state == CircuitState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try resetting."""
        if self._last_failure_time is None:
            return False
        return (time.time() - self._last_failure_time) >= self.recovery_timeout
    
    def _record_success(self):
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= 1:  # Can configure threshold
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                logger.info(f"{self.name}: Circuit recovered, state -> CLOSED")
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0
    
    def _record_failure(self):
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._success_count = 0
            logger.warning(f"{self.name}: Recovery failed, state -> OPEN")
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.error(
                    f"{self.name}: Failure threshold reached ({self._failure_count}), "
                    f"state -> OPEN. Will retry after {self.recovery_timeout}s"
                )
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call a function with circuit breaker protection.
        
        Args:
            func: Function to call
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Result of function call
            
        Raises:
            CircuitBreakerError: If circuit is open
            Original exception: If function fails and circuit is closed/half-open
        """
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                logger.info(f"{self.name}: Attempting recovery, state -> HALF_OPEN")
            else:
                raise CircuitBreakerError(
                    f"{self.name}: Circuit is OPEN. "
                    f"Last failure: {time.time() - self._last_failure_time:.0f}s ago"
                )
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exception as e:
            self._record_failure()
            raise
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Async version of call method."""
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                logger.info(f"{self.name}: Attempting recovery, state -> HALF_OPEN")
            else:
                raise CircuitBreakerError(
                    f"{self.name}: Circuit is OPEN. "
                    f"Last failure: {time.time() - self._last_failure_time:.0f}s ago"
                )
        
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exception as e:
            self._record_failure()
            raise
    
    def reset(self):
        """Manually reset the circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        logger.info(f"{self.name}: Manually reset, state -> CLOSED")
