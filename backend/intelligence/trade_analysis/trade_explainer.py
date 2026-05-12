import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy.orm import Session

from core.logging import logger
from core.config import get_settings
from core.database import SessionLocal


@dataclass
class TradeExplanation:
    trade_id: Optional[str] = None
    symbol: str = ""
    timestamp: Optional[str] = None
    prediction: Optional[dict] = None
    top_positive_features: list = field(default_factory=list)
    top_negative_features: list = field(default_factory=list)
    regime_context: Optional[dict] = None
    historical_trade_similarity: Optional[dict] = None
    latency_ms: float = 0.0
    status: str = "ok"
    message: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "prediction": self.prediction,
            "top_positive_features": self.top_positive_features,
            "top_negative_features": self.top_negative_features,
            "regime_context": self.regime_context,
            "historical_trade_similarity": self.historical_trade_similarity,
            "latency_ms": round(self.latency_ms, 2),
            "status": self.status,
        }
        if self.message:
            d["message"] = self.message
        return d


class TradeExplainer:
    def __init__(self):
        self._shap_service = None
        self._regime_service = None
        self._retriever = None

    def _get_shap_service(self):
        if self._shap_service is not None:
            return self._shap_service
        try:
            from intelligence.explainability.shap_service import SHAPService
            from core.model.registry import ModelRegistry
            registry = ModelRegistry()
            model_data = registry.load()
            model = model_data.get("model")
            feature_names = model_data.get("feature_names", [])
            background = model_data.get("background_samples")
            self._shap_service = SHAPService(
                model=model,
                feature_names=feature_names,
                background_samples=background,
            )
            return self._shap_service
        except Exception as e:
            logger.warning(f"SHAPService not available: {e}")
            return None

    def _get_regime_service(self):
        if self._regime_service is not None:
            return self._regime_service
        try:
            from intelligence.market_regime.service import RegimeService
            from intelligence.market_regime.config import RegimeConfig
            from core.analytics_db import AnalyticsDB

            settings = get_settings()
            config = RegimeConfig(
                enabled=settings.regime_engine_enabled,
                ema_short=settings.regime_ema_short,
                ema_long=settings.regime_ema_long,
                sideways_threshold_pct=settings.regime_sideways_threshold_pct,
                adx_trend_threshold=settings.regime_adx_trend_threshold,
                high_vol_atr_pct=settings.regime_high_vol_atr_pct,
                low_vol_atr_pct=settings.regime_low_vol_atr_pct,
                breakout_volume_ratio=settings.regime_breakout_volume_ratio,
                event_volume_spike_ratio=settings.regime_event_volume_spike_ratio,
                stability_lookback=settings.regime_stability_lookback,
            )

            db = AnalyticsDB()
            service = RegimeService(config=config, db=db)
            service.initialize(db)
            self._regime_service = service
            return self._regime_service
        except Exception as e:
            logger.warning(f"RegimeService not available: {e}")
            return None

    def _get_retriever(self):
        if self._retriever is not None:
            return self._retriever
        try:
            from memory.retrieval.semantic_retriever import SemanticRetriever
            retriever = SemanticRetriever()
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(retriever.initialize())
                else:
                    loop.run_until_complete(retriever.initialize())
            except RuntimeError:
                asyncio.run(retriever.initialize())
            self._retriever = retriever
            return self._retriever
        except Exception as e:
            logger.warning(f"SemanticRetriever not available: {e}")
            return None

    def _find_prediction(self, db: Session, symbol: str, prediction_id: Optional[int] = None,
                         trade_id: Optional[str] = None) -> Optional[Any]:
        from models.prediction_log import PredictionLog

        if prediction_id is not None:
            return db.query(PredictionLog).filter(PredictionLog.id == prediction_id).first()

        if trade_id is not None:
            from models.stock import Stock
            stock = db.query(Stock).filter(Stock.symbol == symbol).first()
            if stock is not None:
                pred = db.query(PredictionLog).filter(
                    PredictionLog.stock_id == stock.id
                ).order_by(PredictionLog.timestamp.desc()).first()
                if pred is not None:
                    return pred

        return db.query(PredictionLog).filter(
            PredictionLog.symbol == symbol
        ).order_by(PredictionLog.timestamp.desc()).first()

    def _get_prediction_confidence(self, pred: Any) -> dict:
        from models.prediction_log import PredictionLog
        probs = {
            "buy": pred.p_buy or 0.0,
            "hold": pred.p_hold or 0.0,
            "sell": pred.p_sell or 0.0,
        }
        import numpy as np
        max_prob = max(probs["buy"], probs["hold"], probs["sell"])
        sorted_probs = sorted([probs["buy"], probs["hold"], probs["sell"]])
        margin = max_prob - sorted_probs[-2] if len(sorted_probs) >= 2 else 0.0
        entropy = 0.0
        for p in [probs["buy"], probs["hold"], probs["sell"]]:
            if p > 0:
                entropy -= p * np.log2(p)

        return {
            "decision": pred.decision,
            "confidence": pred.confidence,
            "probabilities": probs,
            "confidence_level": "high" if max_prob >= 0.65 else "medium" if max_prob >= 0.50 else "low",
            "margin_over_second": round(margin, 4),
            "entropy": round(float(entropy), 4),
            "predicted_class": pred.predicted_class,
            "model_version": pred.model_version,
            "feature_version": pred.feature_version,
        }

    def _get_top_features(self, pred: Any) -> tuple[list, list]:
        if not pred.top_features:
            service = self._get_shap_service()
            if service is not None:
                with SessionLocal() as session:
                    try:
                        service.generate_and_persist(session, pred.id)
                        session.refresh(pred)
                    except Exception as e:
                        logger.warning(f"SHAP generation on-the-fly failed: {e}")
            if not pred.top_features:
                return [], []

        try:
            top = json.loads(pred.top_features) if isinstance(pred.top_features, str) else pred.top_features
        except (json.JSONDecodeError, TypeError):
            return [], []

        positive = [
            {"feature": f["feature"], "shap_value": f.get("shap_value", 0), "contribution_pct": f.get("contribution_pct", 0)}
            for f in top.get("positive", [])
        ]
        negative = [
            {"feature": f["feature"], "shap_value": f.get("shap_value", 0), "contribution_pct": f.get("contribution_pct", 0)}
            for f in top.get("negative", [])
        ]
        return positive, negative

    def _get_regime_context(self, timestamp: Optional[str] = None) -> Optional[dict]:
        service = self._get_regime_service()
        if service is None:
            return None

        try:
            current = service.get_current_regime()
            if current is None:
                return None
            base = {
                "regime": current.regime.value if hasattr(current.regime, "value") else str(current.regime),
                "confidence": current.confidence,
                "risk_level": current.risk_level,
                "stability": current.stability,
                "suggested_behavior": current.suggested_behavior,
            }
            if hasattr(current, "signal_breakdown") and current.signal_breakdown:
                base["signal_breakdown"] = current.signal_breakdown
            if current.volatility_context is not None:
                base["volatility_context"] = {
                    k: v for k, v in current.volatility_context.__dict__.items() if v is not None
                }
            if current.trend_context is not None:
                base["trend_context"] = {
                    k: v for k, v in current.trend_context.__dict__.items() if v is not None
                }
            if hasattr(current, "transition_data") and current.transition_data:
                base["transition_data"] = {
                    k: v for k, v in current.transition_data.items()
                    if k in ("is_unstable", "is_transitioning", "most_likely_next_regime",
                            "most_likely_next_probability", "vol_spike_detected",
                            "confidence_degraded", "transition_alert")
                }
            return base
        except Exception as e:
            logger.warning(f"Failed to get regime context: {e}")
            return None

    def _get_historical_similarity(self, symbol: str, decision: Optional[str] = None,
                                    confidence: Optional[float] = None) -> Optional[dict]:
        retriever = self._get_retriever()
        if retriever is None:
            return None

        try:
            from memory.schemas.memory_schemas import MemoryFilter, MemoryType
            query_parts = [f"trade {symbol}"]
            if decision:
                query_parts.append(f"{decision}")
            query = " ".join(query_parts)

            memory_filter = MemoryFilter(
                memory_type=MemoryType.TRADE,
                ticker=symbol,
                max_results=5,
            )

            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(
                        retriever.search(query, memory_filter=memory_filter, n_results=5),
                        loop,
                    )
                    results = future.result(timeout=5)
                else:
                    results = loop.run_until_complete(
                        retriever.search(query, memory_filter=memory_filter, n_results=5)
                    )
            except RuntimeError:
                results = asyncio.run(
                    retriever.search(query, memory_filter=memory_filter, n_results=5)
                )

            if not results:
                return {"similar_trades_found": 0, "similar_trades": []}

            trades = []
            for r in results:
                meta = r.metadata or {}
                trades.append({
                    "trade_id": meta.get("trade_id", r.id),
                    "ticker": meta.get("ticker", symbol),
                    "outcome": meta.get("outcome", "unknown"),
                    "confidence": meta.get("confidence"),
                    "relevance_score": round(r.relevance_score, 4),
                })

            return {
                "similar_trades_found": len(trades),
                "similar_trades": trades,
            }
        except Exception as e:
            logger.warning(f"Historical similarity search failed: {e}")
            return {"similar_trades_found": 0, "similar_trades": [], "error": str(e)}

    def explain(self, db: Session, symbol: str,
                prediction_id: Optional[int] = None,
                trade_id: Optional[str] = None) -> TradeExplanation:
        start = time.monotonic()
        explanation = TradeExplanation(symbol=symbol)

        pred = self._find_prediction(db, symbol, prediction_id, trade_id)
        if pred is None:
            explanation.status = "not_found"
            explanation.message = f"No prediction found for symbol={symbol}"
            explanation.latency_ms = (time.monotonic() - start) * 1000
            return explanation

        explanation.trade_id = trade_id or f"pred_{pred.id}"
        explanation.symbol = pred.symbol
        explanation.timestamp = pred.timestamp.isoformat() if hasattr(pred.timestamp, "isoformat") else str(pred.timestamp)

        explanation.prediction = self._get_prediction_confidence(pred)

        positive, negative = self._get_top_features(pred)
        explanation.top_positive_features = positive
        explanation.top_negative_features = negative

        explanation.regime_context = self._get_regime_context(explanation.timestamp)

        explanation.historical_trade_similarity = self._get_historical_similarity(
            symbol=symbol,
            decision=pred.decision,
            confidence=pred.confidence,
        )

        explanation.latency_ms = (time.monotonic() - start) * 1000
        return explanation
