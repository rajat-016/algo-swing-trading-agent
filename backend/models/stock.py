from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
import enum

from core.database import Base


class StockStatus(str, enum.Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    TRIGGER_PENDING = "TRIGGER_PENDING"
    ENTERED = "ENTERED"
    EXITED = "EXITED"


class OrderVariety(str, enum.Enum):
    REGULAR = "regular"
    AMO = "amo"
    CO = "co"
    ICEBERG = "iceberg"


class OrderType(str, enum.Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"


class ExitReason(str, enum.Enum):
    TARGET = "TARGET"
    SL = "SL"
    MANUAL = "MANUAL"
    TIME_BASED = "TIME_BASED"
    ORDER_FAILED = "ORDER_FAILED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_FILLED = "ORDER_FILLED"
    DUPLICATE = "DUPLICATE"
    ML_SIGNAL = "ML_SIGNAL"
    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"
    TIER_4 = "TIER_4"


class SLBreachSeverity(str, enum.Enum):
    SAFE = "SAFE"
    YELLOW = "YELLOW"
    ORANGE = "ORANGE"
    RED = "RED"
    CRITICAL = "CRITICAL"


class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    instrument_token = Column(String(20), nullable=True)
    exchange = Column(String(10), default="NSE")
    status = Column(SQLEnum(StockStatus), default=StockStatus.PENDING)

    entry_price = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)

    entry_quantity = Column(Integer, default=0)
    entry_date = Column(DateTime, nullable=True)
    exit_date = Column(DateTime, nullable=True)
    exit_reason = Column(SQLEnum(ExitReason), nullable=True)

    pnl = Column(Float, default=0.0)
    pnl_percentage = Column(Float, default=0.0)

    entry_reason = Column(String(500), nullable=True)
    ai_confidence = Column(Float, default=0.0)

    broker_order_id = Column(String(50), nullable=True)
    broker_status = Column(String(50), nullable=True)
    exit_order_id = Column(String(50), nullable=True)

    current_price = Column(Float, nullable=True)
    average_price = Column(Float, nullable=True)
    realized_pnl = Column(Float, default=0.0)

    prediction_id = Column(Integer, ForeignKey("prediction_logs.id"), nullable=True)

    # Tiered exit tracking
    original_quantity = Column(Integer, default=0)
    remaining_quantity = Column(Integer, default=0)
    current_tier = Column(Integer, default=1)
    trailing_sl = Column(Float, nullable=True)
    sl_breach_severity = Column(SQLEnum(SLBreachSeverity), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to PredictionLog - one Stock has many PredictionLogs (historical)
    # Use PredictionLog.stock_id as the foreign key (in PredictionLog table)
    predictions = relationship("PredictionLog", back_populates="stock", foreign_keys="PredictionLog.stock_id")
    # Relationship to entry PredictionLog - one Stock has one entry_prediction
    entry_prediction = relationship("PredictionLog", foreign_keys=[prediction_id], post_update=True, overlaps="predictions")
    # Relationship to ExitLog - one Stock has many ExitLogs (tier exits)
    exit_logs = relationship("ExitLog", back_populates="stock", order_by="ExitLog.exit_date", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Stock {self.symbol} - {self.status.value}>"

    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "instrument_token": self.instrument_token,
            "exchange": self.exchange,
            "status": self.status.value if self.status else None,
            "entry_price": self.entry_price,
            "target_price": self.target_price,
            "stop_loss": self.stop_loss,
            "entry_quantity": self.entry_quantity,
            "entry_date": self.entry_date.isoformat() if self.entry_date else None,
            "exit_date": self.exit_date.isoformat() if self.exit_date else None,
            "exit_reason": self.exit_reason.value if self.exit_reason else None,
            "pnl": self.pnl,
            "pnl_percentage": self.pnl_percentage,
            "entry_reason": self.entry_reason,
            "ai_confidence": self.ai_confidence,
            "broker_order_id": self.broker_order_id,
            "broker_status": self.broker_status,
            "current_price": self.current_price,
            "average_price": self.average_price,
            "realized_pnl": self.realized_pnl,
            "original_quantity": self.original_quantity,
            "remaining_quantity": self.remaining_quantity,
            "current_tier": self.current_tier,
            "trailing_sl": self.trailing_sl,
            "sl_breach_severity": self.sl_breach_severity.value if self.sl_breach_severity else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ExitLog(Base):
    __tablename__ = "exit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)
    tier = Column(Integer, nullable=False)
    exit_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    exit_date = Column(DateTime, default=datetime.utcnow)
    exit_reason = Column(SQLEnum(ExitReason), nullable=False)
    pnl = Column(Float, nullable=False)
    pnl_percentage = Column(Float, nullable=False)

    stock = relationship("Stock", back_populates="exit_logs", foreign_keys=[stock_id])

    def to_dict(self):
        return {
            "id": self.id,
            "stock_id": self.stock_id,
            "tier": self.tier,
            "exit_price": self.exit_price,
            "quantity": self.quantity,
            "exit_date": self.exit_date.isoformat() if self.exit_date else None,
            "exit_reason": self.exit_reason.value if self.exit_reason else None,
            "pnl": self.pnl,
            "pnl_percentage": self.pnl_percentage,
        }
