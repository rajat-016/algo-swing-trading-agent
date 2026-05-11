from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session
from core.logging import logger
from models.prediction_log import PredictionLog


class PredictionMonitor:
    def __init__(self, db_session=None):
        self.db = db_session

    def set_db(self, db_session):
        self.db = db_session

    def log_prediction(
        self,
        symbol: str,
        predicted_class: int,
        p_buy: float,
        p_hold: float,
        p_sell: float,
        confidence: float,
        decision: str,
        model_version: str = "latest",
        stock_id: Optional[int] = None,
        feature_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        if self.db is None:
            logger.warning("No DB session - skipping prediction log")
            return None

        try:
            log = PredictionLog(
                timestamp=datetime.utcnow(),
                symbol=symbol,
                predicted_class=predicted_class,
                p_buy=p_buy,
                p_hold=p_hold,
                p_sell=p_sell,
                confidence=confidence,
                decision=decision,
                model_version=model_version,
                stock_id=stock_id,
                feature_version=feature_snapshot.get("feature_version") if feature_snapshot else None,
                feature_hash=feature_snapshot.get("feature_hash") if feature_snapshot else None,
            )
            self.db.add(log)
            self.db.commit()
            logger.debug(f"Logged prediction for {symbol}: {decision} (conf={confidence:.2%})")
            if feature_snapshot:
                logger.debug(f"  feature_version={feature_snapshot.get('feature_version')}, "
                             f"feature_hash={feature_snapshot.get('feature_hash')}")
            return log.id
        except Exception as e:
            logger.error(f"Failed to log prediction: {e}")
            self.db.rollback()
            return None

    def update_outcome(
        self,
        prediction_id: int,
        actual_outcome: str,
        actual_return: float,
    ) -> bool:
        if self.db is None:
            return False

        try:
            log = self.db.query(PredictionLog).filter(PredictionLog.id == prediction_id).first()
            if log:
                log.actual_outcome = actual_outcome
                log.actual_return = actual_return
                log.closed_at = datetime.utcnow()
                self.db.commit()
                logger.debug(f"Updated outcome for prediction {prediction_id}: {actual_outcome}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update outcome: {e}")
            self.db.rollback()
            return False

    def update_outcome_by_stock(
        self,
        stock_id: int,
        actual_outcome: str,
        actual_return: float,
    ) -> bool:
        if self.db is None:
            return False

        try:
            log = (
                self.db.query(PredictionLog)
                .filter(
                    PredictionLog.stock_id == stock_id,
                    PredictionLog.actual_outcome.is_(None),
                )
                .order_by(PredictionLog.timestamp.desc())
                .first()
            )
            if log:
                log.actual_outcome = actual_outcome
                log.actual_return = actual_return
                log.closed_at = datetime.utcnow()
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update outcome by stock: {e}")
            self.db.rollback()
            return False

    def get_live_accuracy(self, lookback_days: int = 30) -> Dict:
        if self.db is None:
            return {"accuracy": 0, "total": 0}

        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        logs = (
            self.db.query(PredictionLog)
            .filter(
                PredictionLog.timestamp >= cutoff,
                PredictionLog.actual_outcome.isnot(None),
            )
            .all()
        )

        if not logs:
            return {"accuracy": 0, "total": 0, "wins": 0, "losses": 0}

        wins = sum(1 for l in logs if l.actual_outcome == "WIN")
        total = len(logs)
        return {
            "accuracy": wins / total if total > 0 else 0,
            "total": total,
            "wins": wins,
            "losses": total - wins,
        }

    def get_confidence_calibration(self, lookback_days: int = 30) -> Dict:
        if self.db is None:
            return {}

        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        logs = (
            self.db.query(PredictionLog)
            .filter(
                PredictionLog.timestamp >= cutoff,
                PredictionLog.actual_outcome.isnot(None),
            )
            .all()
        )

        buckets = {
            "low": {"count": 0, "wins": 0},
            "medium": {"count": 0, "wins": 0},
            "high": {"count": 0, "wins": 0},
        }

        for log in logs:
            if log.confidence < 0.50:
                bucket = "low"
            elif log.confidence < 0.65:
                bucket = "medium"
            else:
                bucket = "high"

            buckets[bucket]["count"] += 1
            if log.actual_outcome == "WIN":
                buckets[bucket]["wins"] += 1

        result = {}
        for bucket, data in buckets.items():
            if data["count"] > 0:
                result[bucket] = {
                    "count": data["count"],
                    "win_rate": data["wins"] / data["count"],
                }
        return result

    def get_recent_predictions(self, limit: int = 50) -> List[Dict]:
        if self.db is None:
            return []

        logs = (
            self.db.query(PredictionLog)
            .order_by(PredictionLog.timestamp.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": l.id,
                "timestamp": l.timestamp.isoformat(),
                "symbol": l.symbol,
                "decision": l.decision,
                "confidence": l.confidence,
                "p_buy": l.p_buy,
                "p_hold": l.p_hold,
                "p_sell": l.p_sell,
                "actual_outcome": l.actual_outcome,
                "actual_return": l.actual_return,
            }
            for l in logs
        ]
