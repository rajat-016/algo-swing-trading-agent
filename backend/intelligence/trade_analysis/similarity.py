import asyncio
import re
from dataclasses import dataclass, field
from typing import Any, Optional
from core.logging import logger
from intelligence.trade_analysis.sector_map import get_sector, are_related_sectors


REGIME_CATEGORIES: dict[str, str] = {
    "bull_trend": "bullish",
    "breakout": "bullish",
    "low_volatility": "bullish",
    "bear_trend": "bearish",
    "high_volatility": "bearish",
    "event_driven": "bearish",
    "sideways": "neutral",
    "mean_reversion": "neutral",
    "unstable": "neutral",
}

REGIME_RISK_LEVELS: dict[str, str] = {
    "bull_trend": "low",
    "breakout": "medium",
    "low_volatility": "low",
    "bear_trend": "high",
    "high_volatility": "high",
    "event_driven": "high",
    "sideways": "medium",
    "mean_reversion": "medium",
    "unstable": "high",
}

VOLATILITY_LEVELS: dict[str, str] = {
    "high_volatility": "high",
    "low_volatility": "low",
    "bull_trend": "medium",
    "bear_trend": "medium",
    "sideways": "low",
    "breakout": "medium",
    "event_driven": "high",
    "mean_reversion": "medium",
}

FACTOR_WEIGHTS: dict[str, float] = {
    "regime_similarity": 0.25,
    "volatility_match": 0.20,
    "feature_similarity": 0.25,
    "sector_alignment": 0.15,
    "breakout_structure": 0.15,
}

BREAKOUT_FEATURE_KEYWORDS: list[str] = [
    "breakout", "break_out", "breakout_proximity",
    "volatility_compression", "relative_strength",
    "momentum", "volume_expansion", "price_expansion",
    "atr_expansion", "pullback", "retest",
]


@dataclass
class SimilarityMatchFactors:
    regime_similarity: float = 0.0
    volatility_match: float = 0.0
    feature_similarity: float = 0.0
    sector_alignment: float = 0.0
    breakout_structure: float = 0.0
    composite_score: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class EnhancedSimilarityResult:
    trade_id: str
    ticker: str
    outcome: str | None
    confidence: float | None
    regime: str | None
    relevance_score: float
    factors: SimilarityMatchFactors


BREAKOUT_PREDICTION_DIRECTION = frozenset({"BUY", "STRONG_BUY"})
PULLBACK_PREDICTION_DIRECTION = frozenset({"SELL", "STRONG_SELL"})


class SimilarTradeRetriever:
    def __init__(self):
        self._retriever = None

    def _get_retriever(self):
        if self._retriever is not None:
            return self._retriever
        try:
            from memory.retrieval.semantic_retriever import SemanticRetriever
            retriever = SemanticRetriever()
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

    def find_similar_by_outcome(self, symbol: str, outcome: str,
                                 max_results: int = 5) -> Optional[dict]:
        retriever = self._get_retriever()
        if retriever is None:
            return None

        try:
            from memory.schemas.memory_schemas import MemoryFilter, MemoryType
            query = f"trade {symbol} {outcome}"
            memory_filter = MemoryFilter(
                memory_type=MemoryType.TRADE,
                ticker=symbol,
                outcomes=[outcome] if outcome else None,
                max_results=max_results,
            )
            return self._execute_search(retriever, query, memory_filter, max_results)
        except Exception as e:
            logger.warning(f"Similar by outcome search failed: {e}")
            return None

    def find_similar_by_regime(self, regime: str, symbol: Optional[str] = None,
                                max_results: int = 5) -> Optional[dict]:
        retriever = self._get_retriever()
        if retriever is None:
            return None

        try:
            from memory.schemas.memory_schemas import MemoryFilter, MemoryType
            query = f"trade regime {regime}"
            if symbol:
                query = f"{symbol} {query}"
            memory_filter = MemoryFilter(
                memory_type=MemoryType.TRADE,
                market_regime=regime,
                ticker=symbol,
                max_results=max_results,
            )
            return self._execute_search(retriever, query, memory_filter, max_results)
        except Exception as e:
            logger.warning(f"Similar by regime search failed: {e}")
            return None

    def find_similar_by_features(self, feature_names: list[str],
                                  symbol: Optional[str] = None,
                                  max_results: int = 5) -> Optional[dict]:
        retriever = self._get_retriever()
        if retriever is None:
            return None

        try:
            from memory.schemas.memory_schemas import MemoryFilter, MemoryType
            query = f"trade features {' '.join(feature_names[:5])}"
            if symbol:
                query = f"{symbol} {query}"
            memory_filter = MemoryFilter(
                memory_type=MemoryType.TRADE,
                ticker=symbol,
                max_results=max_results,
            )
            return self._execute_search(retriever, query, memory_filter, max_results)
        except Exception as e:
            logger.warning(f"Similar by features search failed: {e}")
            return None

    def find_all_similar(self, symbol: str, regime: Optional[str] = None,
                          outcome: Optional[str] = None,
                          feature_names: Optional[list] = None,
                          max_results: int = 5) -> dict:
        all_trades = {}
        seen_ids = set()
        queries_run = 0

        if outcome:
            result = self.find_similar_by_outcome(symbol, outcome, max_results)
            if result:
                for t in result.get("similar_trades", []):
                    tid = t.get("trade_id")
                    if tid and tid not in seen_ids:
                        seen_ids.add(tid)
                        all_trades[tid] = t
                queries_run += 1

        if regime:
            result = self.find_similar_by_regime(regime, symbol, max_results)
            if result:
                for t in result.get("similar_trades", []):
                    tid = t.get("trade_id")
                    if tid and tid not in seen_ids:
                        seen_ids.add(tid)
                        all_trades[tid] = t
                queries_run += 1

        if feature_names:
            result = self.find_similar_by_features(feature_names, symbol, max_results)
            if result:
                for t in result.get("similar_trades", []):
                    tid = t.get("trade_id")
                    if tid and tid not in seen_ids:
                        seen_ids.add(tid)
                        all_trades[tid] = t
                queries_run += 1

        sorted_trades = sorted(
            all_trades.values(),
            key=lambda x: x.get("relevance_score", 0),
            reverse=True,
        )[:max_results]

        return {
            "similar_trades_found": len(sorted_trades),
            "similar_trades": sorted_trades,
            "queries_run": queries_run,
        }

    def find_similar_enhanced(
        self,
        symbol: str,
        regime: Optional[str] = None,
        outcome: Optional[str] = None,
        feature_names: Optional[list[str]] = None,
        volatility_context: Optional[dict] = None,
        prediction: Optional[str] = None,
        max_results: int = 5,
    ) -> dict:
        raw_results = self.find_all_similar(
            symbol=symbol,
            regime=regime,
            outcome=outcome,
            feature_names=feature_names,
            max_results=max_results * 2,
        )
        base_trades = raw_results.get("similar_trades", [])
        if not base_trades:
            return {
                "similar_trades_found": 0,
                "similar_trades": [],
                "queries_run": raw_results.get("queries_run", 0),
                "scoring_enabled": True,
                "factor_weights": dict(FACTOR_WEIGHTS),
            }

        target_sector = get_sector(symbol)
        target_regime = regime
        target_vol = _resolve_volatility(regime, volatility_context)
        target_prediction = prediction
        target_features = feature_names or []
        scored: list[EnhancedSimilarityResult] = []

        for t in base_trades:
            candidate_regime = t.get("regime")
            candidate_text = t.get("_embedding_text", "")
            candidate_ticker = t.get("ticker", "")
            candidate_prediction = t.get("prediction")

            factors = SimilarityMatchFactors(
                regime_similarity=_score_regime_similarity(target_regime, candidate_regime),
                volatility_match=_score_volatility_match(target_vol, candidate_regime),
                feature_similarity=_score_feature_similarity(target_features, candidate_text),
                sector_alignment=_score_sector_alignment(target_sector, candidate_ticker),
                breakout_structure=_score_breakout_structure(target_prediction, candidate_prediction, target_features, candidate_text),
            )
            factors.composite_score = _compute_composite(factors)
            factors.details = {
                "target_regime": target_regime,
                "candidate_regime": candidate_regime,
                "target_volatility": target_vol,
                "target_sector": target_sector,
                "candidate_sector": get_sector(candidate_ticker),
                "target_prediction": target_prediction,
                "candidate_prediction": candidate_prediction,
                "feature_overlap": _get_feature_overlap(target_features, candidate_text),
            }

            scored.append(EnhancedSimilarityResult(
                trade_id=t.get("trade_id", ""),
                ticker=candidate_ticker,
                outcome=t.get("outcome"),
                confidence=t.get("confidence"),
                regime=candidate_regime,
                relevance_score=t.get("relevance_score", 0),
                factors=factors,
            ))

        scored.sort(key=lambda r: r.factors.composite_score, reverse=True)
        top = scored[:max_results]

        return {
            "similar_trades_found": len(top),
            "similar_trades": [_result_to_dict(r) for r in top],
            "queries_run": raw_results.get("queries_run", 0),
            "scoring_enabled": True,
            "factor_weights": dict(FACTOR_WEIGHTS),
        }

    def _execute_search(self, retriever, query: str, memory_filter,
                         max_results: int) -> dict:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    retriever.search(query, memory_filter=memory_filter, n_results=max_results),
                    loop,
                )
                results = future.result(timeout=5)
            else:
                results = loop.run_until_complete(
                    retriever.search(query, memory_filter=memory_filter, n_results=max_results)
                )
        except RuntimeError:
            results = asyncio.run(
                retriever.search(query, memory_filter=memory_filter, n_results=max_results)
            )

        if not results:
            return {"similar_trades_found": 0, "similar_trades": []}

        trades = []
        for r in results:
            meta = r.metadata or {}
            trades.append({
                "trade_id": meta.get("trade_id", r.id),
                "ticker": meta.get("ticker", "unknown"),
                "outcome": meta.get("outcome", "unknown"),
                "confidence": meta.get("confidence"),
                "regime": meta.get("market_regime"),
                "prediction": meta.get("prediction"),
                "relevance_score": round(r.relevance_score, 4),
                "_embedding_text": r.text,
            })

        trades.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return {
            "similar_trades_found": len(trades),
            "similar_trades": trades[:max_results],
        }


def _score_regime_similarity(target_regime: str | None, candidate_regime: str | None) -> float:
    if not target_regime or not candidate_regime:
        return 0.0
    if target_regime == candidate_regime:
        return 1.0
    target_cat = REGIME_CATEGORIES.get(target_regime, "unknown")
    candidate_cat = REGIME_CATEGORIES.get(candidate_regime, "unknown")
    if target_cat == candidate_cat:
        return 0.6
    return 0.0


def _resolve_volatility(regime: str | None, volatility_context: Optional[dict]) -> str | None:
    if volatility_context:
        vol = volatility_context.get("volatility_level") or volatility_context.get("atr_percentile")
        if vol:
            return str(vol)
        regime_from_ctx = volatility_context.get("regime", "")
        vol_level = VOLATILITY_LEVELS.get(regime_from_ctx)
        if vol_level:
            return vol_level
    if regime:
        return VOLATILITY_LEVELS.get(regime)
    return None


def _score_volatility_match(target_vol: str | None, candidate_regime: str | None) -> float:
    if not target_vol or not candidate_regime:
        return 0.0
    candidate_vol = VOLATILITY_LEVELS.get(candidate_regime, "medium")
    if target_vol == candidate_vol:
        return 1.0
    vol_rank = {"low": 0, "medium": 1, "high": 2}
    tv = vol_rank.get(target_vol, 1)
    cv = vol_rank.get(candidate_vol, 1)
    if abs(tv - cv) == 1:
        return 0.4
    return 0.0


def _score_feature_similarity(target_features: list[str], candidate_text: str) -> float:
    if not target_features or not candidate_text:
        return 0.0
    text_lower = candidate_text.lower()
    matched = sum(1 for f in target_features if f.lower().replace(" ", "_") in text_lower)
    if matched == 0:
        return 0.0
    return round(matched / len(target_features), 4)


def _score_sector_alignment(target_sector: str | None, candidate_ticker: str) -> float:
    if not target_sector or not candidate_ticker:
        return 0.0
    candidate_sector = get_sector(candidate_ticker)
    if not candidate_sector:
        return 0.0
    if target_sector == candidate_sector:
        return 1.0
    if are_related_sectors(target_sector, candidate_sector):
        return 0.5
    return 0.0


def _score_breakout_structure(
    target_prediction: str | None,
    candidate_prediction: str | None,
    target_features: list[str],
    candidate_text: str,
) -> float:
    direction_score = 0.0
    structure_score = 0.0

    if target_prediction and candidate_prediction:
        target_dir = _get_prediction_direction(target_prediction)
        candidate_dir = _get_prediction_direction(candidate_prediction)
        if target_dir is not None and candidate_dir is not None:
            if target_dir == candidate_dir:
                direction_score = 0.6

    if target_features or candidate_text:
        target_breakout = any(
            any(kw in f.lower().replace(" ", "_") for kw in BREAKOUT_FEATURE_KEYWORDS)
            for f in target_features
        )
        text_lower = candidate_text.lower()
        candidate_breakout = any(kw in text_lower for kw in BREAKOUT_FEATURE_KEYWORDS)
        if target_breakout and candidate_breakout:
            structure_score = 0.4
        elif not target_breakout and not candidate_breakout:
            structure_score = 0.2

    return round(direction_score + structure_score, 4)


def _get_prediction_direction(prediction: str | None) -> str | None:
    if not prediction:
        return None
    p = prediction.upper().strip()
    if p in ("BUY", "STRONG_BUY"):
        return "BUY"
    if p in ("SELL", "STRONG_SELL"):
        return "SELL"
    if p == "HOLD":
        return "HOLD"
    return None


def _get_feature_overlap(target_features: list[str], candidate_text: str) -> list[str]:
    if not target_features or not candidate_text:
        return []
    text_lower = candidate_text.lower()
    return [f for f in target_features if f.lower().replace(" ", "_") in text_lower]


def _compute_composite(factors: SimilarityMatchFactors) -> float:
    score = (
        factors.regime_similarity * FACTOR_WEIGHTS["regime_similarity"]
        + factors.volatility_match * FACTOR_WEIGHTS["volatility_match"]
        + factors.feature_similarity * FACTOR_WEIGHTS["feature_similarity"]
        + factors.sector_alignment * FACTOR_WEIGHTS["sector_alignment"]
        + factors.breakout_structure * FACTOR_WEIGHTS["breakout_structure"]
    )
    return round(score, 4)


def _result_to_dict(r: EnhancedSimilarityResult) -> dict:
    return {
        "trade_id": r.trade_id,
        "ticker": r.ticker,
        "outcome": r.outcome,
        "confidence": r.confidence,
        "regime": r.regime,
        "relevance_score": r.relevance_score,
        "match_factors": {
            "regime_similarity": r.factors.regime_similarity,
            "volatility_match": r.factors.volatility_match,
            "feature_similarity": r.factors.feature_similarity,
            "sector_alignment": r.factors.sector_alignment,
            "breakout_structure": r.factors.breakout_structure,
            "composite_score": r.factors.composite_score,
        },
        "match_details": r.factors.details,
    }
