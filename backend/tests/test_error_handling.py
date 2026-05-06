"""
Unit tests for the error handling system including custom exceptions,
retry decorator, and circuit breaker.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import pytest
from core.exceptions import (
    TradingSystemError, BrokerError, ZerodhaError,
    IPRestrictionError, AuthenticationError, RateLimitError,
    OrderError, InsufficientFundsError, DataFetchError,
    ModelError, ModelLoadError, PredictionError,
    ConfigurationError, DatabaseError, ValidationError,
    TradingLoopError, CircuitBreakerError
)
from core.retry import retry_with_backoff, retry_async_with_backoff
from core.circuit_breaker import CircuitBreaker, CircuitState


class TestCustomExceptions:
    """Test custom exception classes."""
    
    def test_trading_system_error_basic(self):
        error = TradingSystemError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details == {}
    
    def test_trading_system_error_with_details(self):
        details = {"code": 123, "source": "test"}
        error = TradingSystemError("Test error", details)
        assert error.details == details
    
    def test_zerodha_error(self):
        error = ZerodhaError("Zerodha error", error_code="500", error_type="SERVER_ERROR")
        assert error.error_code == "500"
        assert error.error_type == "SERVER_ERROR"
    
    def test_ip_restriction_error(self):
        error = IPRestrictionError("IP not allowed", ip_address="192.168.1.1")
        assert "IP not allowed" in error.message
        assert error.details["ip_address"] == "192.168.1.1"
        assert isinstance(error, ZerodhaError)
    
    def test_authentication_error(self):
        error = AuthenticationError("Auth failed", error_code="401")
        assert error.error_code == "401"
        assert isinstance(error, ZerodhaError)
    
    def test_rate_limit_error(self):
        error = RateLimitError("Rate limited", retry_after=60)
        assert error.details["retry_after"] == 60
        assert isinstance(error, ZerodhaError)
    
    def test_order_error(self):
        error = OrderError("Order failed", order_id="12345", rejection_reason="INSUFFICIENT_FUNDS")
        assert error.details["order_id"] == "12345"
        assert error.details["rejection_reason"] == "INSUFFICIENT_FUNDS"
    
    def test_insufficient_funds_error(self):
        error = InsufficientFundsError("Not enough funds", available=1000, required=5000)
        assert error.details["available"] == 1000
        assert error.details["required"] == 5000
        assert isinstance(error, OrderError)
    
    def test_circuit_breaker_error(self):
        error = CircuitBreakerError("Circuit open", failure_count=5)
        assert error.details["failure_count"] == 5


class TestRetryDecorator:
    """Test retry decorator with backoff."""
    
    def test_retry_success_first_attempt(self):
        call_count = 0
        
        @retry_with_backoff(max_retries=3)
        def success_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = success_function()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_success_after_failures(self):
        call_count = 0
        
        @retry_with_backoff(max_retries=3, backoff_factor=0.1, max_backoff=1)
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = failing_function()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_exhausted(self):
        call_count = 0
        
        @retry_with_backoff(max_retries=3, backoff_factor=0.1, max_backoff=1)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError):
            always_fails()
        assert call_count == 4  # Initial + 3 retries
    
    def test_retry_specific_exceptions(self):
        call_count = 0
        
        @retry_with_backoff(max_retries=2, exceptions=(ValueError,), backoff_factor=0.1, max_backoff=1)
        def specific_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Specific error")
        
        with pytest.raises(ValueError):
            specific_error()
        assert call_count == 3
    
    def test_retry_does_not_catch_unrelated_exceptions(self):
        @retry_with_backoff(max_retries=2, exceptions=(ValueError,), backoff_factor=0.1, max_backoff=1)
        def type_error():
            raise TypeError("Wrong type")
        
        with pytest.raises(TypeError):
            type_error()


class TestCircuitBreaker:
    """Test circuit breaker pattern."""
    
    def test_initial_state_closed(self):
        breaker = CircuitBreaker()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed
        assert not breaker.is_open
    
    def test_successful_calls_keep_circuit_closed(self):
        breaker = CircuitBreaker()
        
        def success_func():
            return "success"
        
        for _ in range(10):
            result = breaker.call(success_func)
            assert result == "success"
        
        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0
    
    def test_failures_open_circuit(self):
        breaker = CircuitBreaker(failure_threshold=3)
        
        def failing_func():
            raise ValueError("Error")
        
        # First 3 failures should open the circuit
        for i in range(3):
            with pytest.raises(ValueError):
                breaker.call(failing_func)
        
        assert breaker.state == CircuitState.OPEN
        
        # Next call should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            breaker.call(failing_func)
    
    def test_circuit_half_open_recovery(self):
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.5)
        
        def failing_func():
            raise ValueError("Error")
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(1)
        
        # Now circuit should be half-open and allow one test call
        def success_func():
            return "recovered"
        
        result = breaker.call(success_func)
        assert result == "recovered"
        assert breaker.state == CircuitState.CLOSED
    
    def test_circuit_reset(self):
        breaker = CircuitBreaker(failure_threshold=2)
        
        def failing_func():
            raise ValueError("Error")
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)
        
        assert breaker.state == CircuitState.OPEN
        
        # Reset manually
        breaker.reset()
        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0


class TestExceptionInheritance:
    """Test that exception inheritance is correct."""
    
    def test_hierarchy(self):
        assert issubclass(ZerodhaError, BrokerError)
        assert issubclass(ZerodhaError, TradingSystemError)
        assert issubclass(IPRestrictionError, ZerodhaError)
        assert issubclass(AuthenticationError, ZerodhaError)
        assert issubclass(RateLimitError, ZerodhaError)
        assert issubclass(OrderError, ZerodhaError)
        assert issubclass(InsufficientFundsError, OrderError)
        assert issubclass(ModelLoadError, ModelError)
        assert issubclass(PredictionError, ModelError)
        assert issubclass(CircuitBreakerError, TradingSystemError)
