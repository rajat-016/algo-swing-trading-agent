import time
from typing import Any, Optional

from sqlalchemy.orm import Session

from core.logging import logger


class TradeIntelligenceService:
    def __init__(self):
        self._explainer = None
        self._reasoning_engine = None
        self._failure_analyzer = None
        self._similarity = None
        self._pattern_analyzer = None

    def _get_explainer(self):
        if self._explainer is not None:
            return self._explainer
        try:
            from intelligence.trade_analysis.trade_explainer import TradeExplainer
            self._explainer = TradeExplainer()
            return self._explainer
        except Exception as e:
            logger.warning(f"TradeExplainer not available: {e}")
            return None

    def _get_reasoning_engine(self):
        if self._reasoning_engine is None:
            from intelligence.trade_analysis.reasoning import ReasoningEngine
            self._reasoning_engine = ReasoningEngine()
        return self._reasoning_engine

    def _get_failure_analyzer(self):
        if self._failure_analyzer is None:
            from intelligence.trade_analysis.failure_analyzer import FailureAnalyzer
            self._failure_analyzer = FailureAnalyzer()
        return self._failure_analyzer

    def _get_similarity(self):
        if self._similarity is None:
            from intelligence.trade_analysis.similarity import SimilarTradeRetriever
            self._similarity = SimilarTradeRetriever()
        return self._similarity

    def _get_pattern_analyzer(self):
        if self._pattern_analyzer is None:
            from intelligence.trade_analysis.failure_patterns import FailurePatternAnalyzer
            self._pattern_analyzer = FailurePatternAnalyzer()
        return self._pattern_analyzer

    def analyze_trade(self, db: Session, symbol: str,
                       prediction_id: Optional[int] = None,
                       trade_id: Optional[str] = None) -> dict:
        start = time.monotonic()
        result = {"symbol": symbol, "status": "ok"}

        explainer = self._get_explainer()
        if explainer is None:
            return {"symbol": symbol, "status": "error", "message": "TradeExplainer not available"}

        explanation = explainer.explain(db, symbol, prediction_id, trade_id)
        if explanation.status == "not_found":
            return {
                "symbol": symbol,
                "status": "not_found",
                "message": explanation.message,
            }

        result["explanation"] = explanation.to_dict()

        stock_data = self._get_stock_data(db, symbol, explanation.trade_id)

        reasoning_engine = self._get_reasoning_engine()
        result["reasoning"] = reasoning_engine.generate_trade_reasoning(
            prediction=explanation.prediction,
            top_positive=explanation.top_positive_features,
            top_negative=explanation.top_negative_features,
            regime_context=explanation.regime_context,
            stock_data=stock_data,
            outcome=stock_data.get("actual_outcome") if stock_data else None,
        )

        outcome = stock_data.get("actual_outcome") if stock_data else None
        if outcome == "LOSS" or (stock_data and stock_data.get("pnl_percentage", 0) < 0):
            failure_analyzer = self._get_failure_analyzer()
            result["failure_analysis"] = failure_analyzer.analyze_failure(
                prediction=explanation.prediction,
                top_positive=explanation.top_positive_features,
                top_negative=explanation.top_negative_features,
                regime_context=explanation.regime_context,
                stock_data=stock_data,
            )

        similarity = self._get_similarity()
        top_features = [f.get("feature", "") for f in (explanation.top_positive_features or [])]
        result["similar_trades"] = similarity.find_similar_enhanced(
            symbol=symbol,
            regime=explanation.regime_context.get("regime") if explanation.regime_context else None,
            outcome=outcome,
            feature_names=top_features[:5] if top_features else None,
            volatility_context=explanation.regime_context,
            prediction=explanation.prediction.get("decision") if explanation.prediction else None,
        )

        result["latency_ms"] = round((time.monotonic() - start) * 1000, 2)
        return result

    def analyze_failure(self, db: Session, symbol: str,
                         prediction_id: Optional[int] = None,
                         trade_id: Optional[str] = None) -> dict:
        start = time.monotonic()

        explainer = self._get_explainer()
        if explainer is None:
            return {"symbol": symbol, "status": "error", "message": "TradeExplainer not available"}

        explanation = explainer.explain(db, symbol, prediction_id, trade_id)
        if explanation.status == "not_found":
            return {"symbol": symbol, "status": "not_found", "message": explanation.message}

        stock_data = self._get_stock_data(db, symbol, explanation.trade_id)

        failure_analyzer = self._get_failure_analyzer()
        analysis = failure_analyzer.analyze_failure(
            prediction=explanation.prediction,
            top_positive=explanation.top_positive_features,
            top_negative=explanation.top_negative_features,
            regime_context=explanation.regime_context,
            stock_data=stock_data,
        )

        reasoning_engine = self._get_reasoning_engine()
        reasoning = reasoning_engine.generate_trade_reasoning(
            prediction=explanation.prediction,
            top_positive=explanation.top_positive_features,
            top_negative=explanation.top_negative_features,
            regime_context=explanation.regime_context,
            stock_data=stock_data,
            outcome="LOSS",
        )

        result = {
            "symbol": symbol,
            "status": "ok",
            "explanation": explanation.to_dict(),
            "failure_analysis": analysis,
            "reasoning": reasoning,
            "latency_ms": round((time.monotonic() - start) * 1000, 2),
        }
        return result

    def generate_post_trade_analysis(self, db: Session, symbol: str,
                                      prediction_id: Optional[int] = None,
                                      trade_id: Optional[str] = None) -> dict:
        start = time.monotonic()

        explainer = self._get_explainer()
        if explainer is None:
            return {"symbol": symbol, "status": "error", "message": "TradeExplainer not available"}

        explanation = explainer.explain(db, symbol, prediction_id, trade_id)
        if explanation.status == "not_found":
            return {"symbol": symbol, "status": "not_found", "message": explanation.message}

        stock_data = self._get_stock_data(db, symbol, explanation.trade_id)
        outcome = stock_data.get("actual_outcome") if stock_data else None

        reasoning_engine = self._get_reasoning_engine()
        reasoning = reasoning_engine.generate_trade_reasoning(
            prediction=explanation.prediction,
            top_positive=explanation.top_positive_features,
            top_negative=explanation.top_negative_features,
            regime_context=explanation.regime_context,
            stock_data=stock_data,
            outcome=outcome,
        )

        failure_analyzer = self._get_failure_analyzer()
        failure_analysis = failure_analyzer.analyze_failure(
            prediction=explanation.prediction,
            top_positive=explanation.top_positive_features,
            top_negative=explanation.top_negative_features,
            regime_context=explanation.regime_context,
            stock_data=stock_data,
        )

        pattern_analyzer = self._get_pattern_analyzer()
        patterns = pattern_analyzer.analyze_patterns(symbol=symbol)

        top_features = [f.get("feature", "") for f in (explanation.top_positive_features or [])]
        similarity = self._get_similarity()
        similar_trades = similarity.find_similar_enhanced(
            symbol=symbol,
            regime=explanation.regime_context.get("regime") if explanation.regime_context else None,
            outcome=outcome,
            feature_names=top_features[:5] if top_features else None,
            volatility_context=explanation.regime_context,
            prediction=explanation.prediction.get("decision") if explanation.prediction else None,
        )

        return {
            "symbol": symbol,
            "status": "ok",
            "trade_summary": {
                "trade_id": explanation.trade_id,
                "symbol": explanation.symbol,
                "timestamp": explanation.timestamp,
                "decision": explanation.prediction.get("decision") if explanation.prediction else None,
                "outcome": outcome,
            },
            "reasoning": reasoning,
            "failure_analysis": failure_analysis,
            "failure_patterns": patterns,
            "similar_trades": similar_trades,
            "latency_ms": round((time.monotonic() - start) * 1000, 2),
        }

    def get_reasoning(self, db: Session, symbol: str,
                       prediction_id: Optional[int] = None,
                       trade_id: Optional[str] = None) -> dict:
        start = time.monotonic()

        explainer = self._get_explainer()
        if explainer is None:
            return {"symbol": symbol, "status": "error", "message": "TradeExplainer not available"}

        explanation = explainer.explain(db, symbol, prediction_id, trade_id)
        if explanation.status == "not_found":
            return {"symbol": symbol, "status": "not_found", "message": explanation.message}

        stock_data = self._get_stock_data(db, symbol, explanation.trade_id)

        reasoning_engine = self._get_reasoning_engine()
        reasoning = reasoning_engine.generate_trade_reasoning(
            prediction=explanation.prediction,
            top_positive=explanation.top_positive_features,
            top_negative=explanation.top_negative_features,
            regime_context=explanation.regime_context,
            stock_data=stock_data,
            outcome=stock_data.get("actual_outcome") if stock_data else None,
        )

        result = {
            "symbol": symbol,
            "status": "ok",
            "reasoning": reasoning,
            "latency_ms": round((time.monotonic() - start) * 1000, 2),
        }
        return result

    def _get_stock_data(self, db: Session, symbol: str,
                         trade_id: Optional[str] = None) -> Optional[dict]:
        try:
            from models.stock import Stock
            from models.prediction_log import PredictionLog

            stock = db.query(Stock).filter(Stock.symbol == symbol).first()
            if stock is None:
                return None

            pred = (
                db.query(PredictionLog)
                .filter(PredictionLog.symbol == symbol)
                .order_by(PredictionLog.timestamp.desc())
                .first()
            )

            data = stock.to_dict() if hasattr(stock, "to_dict") else {}
            if pred:
                data["actual_outcome"] = pred.actual_outcome
                data["actual_return"] = pred.actual_return
                data["closed_at"] = pred.closed_at.isoformat() if pred.closed_at else None

            return data
        except Exception as e:
            logger.warning(f"Failed to get stock data: {e}")
            return None
