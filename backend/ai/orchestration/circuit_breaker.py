import time
from enum import Enum
from loguru import logger


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class AICircuitBreaker:
    def __init__(self, threshold: int = 5, reset_seconds: int = 60):
        self.threshold = threshold
        self.reset_seconds = reset_seconds
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._state = CircuitState.CLOSED
        self._success_count = 0

    @property
    def state(self) -> str:
        return self._state.value

    def allow_request(self) -> bool:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.reset_seconds:
                self._state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker: OPEN -> HALF_OPEN")
                return True
            return False
        return True

    def record_success(self):
        self._failure_count = 0
        self._success_count += 1
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            logger.info("Circuit breaker: HALF_OPEN -> CLOSED")

    def record_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker: CLOSED -> OPEN "
                f"({self._failure_count} failures)"
            )

    def reset(self):
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._state = CircuitState.CLOSED
        self._success_count = 0
        logger.info("Circuit breaker reset")
