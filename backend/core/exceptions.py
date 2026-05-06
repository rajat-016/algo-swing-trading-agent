"""
Custom exception classes for the trading system.
Provides specific error types for better error handling and debugging.
"""

from typing import Optional, Dict, Any


class TradingSystemError(Exception):
    """Base exception for all trading system errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class BrokerError(TradingSystemError):
    """Base exception for broker-related errors."""
    pass


class ZerodhaError(BrokerError):
    """Zerodha API specific errors."""
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 error_type: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.error_code = error_code
        self.error_type = error_type
        super().__init__(message, details)


class IPRestrictionError(ZerodhaError):
    """IP not allowed to place orders."""
    def __init__(self, message: str = "IP not allowed to place orders", 
                 ip_address: Optional[str] = None):
        details = {"ip_address": ip_address} if ip_address else {}
        super().__init__(message, error_code="403", error_type="IP_RESTRICTION", details=details)


class AuthenticationError(ZerodhaError):
    """Authentication/authorization failed."""
    def __init__(self, message: str = "Authentication failed", 
                 error_code: Optional[str] = None):
        super().__init__(message, error_code=error_code, error_type="AUTH_FAILED")


class RateLimitError(ZerodhaError):
    """API rate limit exceeded."""
    def __init__(self, message: str = "Rate limit exceeded", 
                 retry_after: Optional[int] = None):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(message, error_code="429", error_type="RATE_LIMIT", details=details)


class OrderError(ZerodhaError):
    """Order placement or management failed."""
    def __init__(self, message: str, order_id: Optional[str] = None, 
                 rejection_reason: Optional[str] = None):
        details = {}
        if order_id:
            details["order_id"] = order_id
        if rejection_reason:
            details["rejection_reason"] = rejection_reason
        super().__init__(message, error_type="ORDER_FAILED", details=details)


class InsufficientFundsError(OrderError):
    """Insufficient funds to place order."""
    def __init__(self, message: str = "Insufficient funds", 
                 available: Optional[float] = None, required: Optional[float] = None):
        super().__init__(message)
        if available is not None:
            self.details["available"] = available
        if required is not None:
            self.details["required"] = required


class DataFetchError(TradingSystemError):
    """Failed to fetch market data."""
    pass


class ModelError(TradingSystemError):
    """ML model related errors."""
    pass


class ModelLoadError(ModelError):
    """Failed to load ML model."""
    pass


class PredictionError(ModelError):
    """Failed to make prediction."""
    pass


class ConfigurationError(TradingSystemError):
    """Configuration validation failed."""
    pass


class DatabaseError(TradingSystemError):
    """Database operation failed."""
    pass


class ValidationError(TradingSystemError):
    """Input validation failed."""
    pass


class TradingLoopError(TradingSystemError):
    """Trading loop execution error."""
    pass


class CircuitBreakerError(TradingSystemError):
    """Circuit breaker triggered."""
    def __init__(self, message: str = "Circuit breaker triggered", 
                 failure_count: Optional[int] = None):
        details = {"failure_count": failure_count} if failure_count else {}
        super().__init__(message, details=details)
