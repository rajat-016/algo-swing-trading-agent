from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base


class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    symbol = Column(String(20), index=True)
    predicted_class = Column(Integer)  # 0=SELL, 1=HOLD, 2=BUY
    p_buy = Column(Float)
    p_hold = Column(Float)
    p_sell = Column(Float)
    confidence = Column(Float)
    decision = Column(String(20))  # BUY, NO_TRADE, SELL
    model_version = Column(String(50))

    # Link to stock if prediction led to a trade
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=True)
    stock = relationship("Stock", back_populates="predictions", foreign_keys=[stock_id])

    # Outcome fields (filled when trade exits)
    actual_outcome = Column(String(20), nullable=True)  # WIN, LOSS
    actual_return = Column(Float, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<PredictionLog {self.symbol} - {self.decision}>"
