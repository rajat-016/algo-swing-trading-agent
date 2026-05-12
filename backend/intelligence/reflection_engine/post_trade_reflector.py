from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from loguru import logger


class PostTradeReflection(BaseModel):
    trade_id: str = Field(description="Unique trade identifier")
    symbol: str = Field(description="Stock ticker symbol")
    setup_quality: str = Field(description="Assessment of entry setup technical soundness")
    execution_quality: str = Field(description="Assessment of trade execution timing and sizing")
    regime_alignment: str = Field(description="How well the trade aligned with market regime")
    volatility_context: str = Field(description="How volatility was factored into the trade")
    feature_confirmation_quality: str = Field(description="Whether model features confirmed the trade direction")
    overall_assessment: str = Field(description="Overall trade assessment summary")
    lessons_learned: list[str] = Field(default_factory=list, description="Key lessons for future trades")
    reflection_type: str = Field(default="post_trade", description="Type of reflection")


class PostTradeReflector:
    def __init__(self, orchestration_engine=None):
        self._orchestration_engine = orchestration_engine
        self._semantic_retriever = None

    async def _get_orchestration_engine(self):
        if self._orchestration_engine is not None:
            return self._orchestration_engine
        try:
            from ai.orchestration.engine import OrchestrationEngine
            self._orchestration_engine = OrchestrationEngine()
        except Exception as e:
            logger.warning(f"OrchestrationEngine not available: {e}")
        return self._orchestration_engine

    async def _get_semantic_retriever(self):
        if self._semantic_retriever is not None:
            return self._semantic_retriever
        try:
            from memory.retrieval.semantic_retriever import SemanticRetriever
            self._semantic_retriever = SemanticRetriever()
            await self._semantic_retriever.initialize()
        except Exception as e:
            logger.warning(f"SemanticRetriever not available: {e}")
        return self._semantic_retriever

    async def reflect(
        self,
        trade_data: dict,
    ) -> Optional[PostTradeReflection]:
        try:
            engine = await self._get_orchestration_engine()
            if engine is None:
                return None

            trade_id = str(trade_data.get("trade_id", ""))
            symbol = trade_data.get("symbol", "")

            raw = await engine.generate_post_trade_reflection(
                symbol=symbol,
                trade_id=trade_id,
                entry_price=trade_data.get("entry_price"),
                exit_price=trade_data.get("exit_price"),
                direction=trade_data.get("prediction", "BUY"),
                confidence=trade_data.get("confidence"),
                regime=trade_data.get("market_regime") or "",
                outcome="WIN" if trade_data.get("pnl", 0) >= 0 else "LOSS",
                pnl=trade_data.get("pnl", 0),
                pnl_pct=trade_data.get("pnl_pct", 0),
                exit_reason=str(trade_data.get("exit_reason", "")),
                feature_snapshot=json.dumps(trade_data.get("feature_snapshot", {})),
                portfolio_state=json.dumps(trade_data.get("portfolio_state", {})),
            )

            parsed = self._parse_reflection(raw, trade_id, symbol)
            if parsed:
                await self._store_reflection_to_semantic_memory(parsed)
            return parsed

        except Exception as e:
            logger.warning(f"Post-trade reflection failed for {trade_data.get('trade_id', 'unknown')}: {e}")
            return None

    def _parse_reflection(self, raw_text: str, trade_id: str, symbol: str) -> Optional[PostTradeReflection]:
        try:
            from ai.llm.models import ResponseParser
            data = ResponseParser.extract_json(raw_text)
            return PostTradeReflection(
                trade_id=trade_id,
                symbol=symbol,
                setup_quality=data.get("setup_quality", ""),
                execution_quality=data.get("execution_quality", ""),
                regime_alignment=data.get("regime_alignment", ""),
                volatility_context=data.get("volatility_context", ""),
                feature_confirmation_quality=data.get("feature_confirmation_quality", ""),
                overall_assessment=data.get("overall_assessment", ""),
                lessons_learned=data.get("lessons_learned", []),
                reflection_type="post_trade",
            )
        except Exception as e:
            logger.warning(f"Failed to parse reflection JSON: {e}")
            return PostTradeReflection(
                trade_id=trade_id,
                symbol=symbol,
                setup_quality=raw_text[:500],
                execution_quality="",
                regime_alignment="",
                volatility_context="",
                feature_confirmation_quality="",
                overall_assessment="",
                lessons_learned=[],
                reflection_type="post_trade",
            )

    async def _store_reflection_to_semantic_memory(self, reflection: PostTradeReflection):
        try:
            retriever = await self._get_semantic_retriever()
            if retriever is None:
                return

            from memory.schemas.memory_schemas import TradeMemory

            trade = TradeMemory(
                trade_id=reflection.trade_id,
                ticker=reflection.symbol,
                timestamp=datetime.now(timezone.utc).isoformat(),
                reasoning=reflection.overall_assessment,
                reflection_notes=reflection.model_dump_json(indent=2),
            )
            await retriever.store_trade(trade)
            logger.debug(f"Stored reflection for trade {reflection.trade_id} to semantic memory")
        except Exception as e:
            logger.debug(f"Failed to store reflection to semantic memory: {e}")

    def to_dict(self, reflection: PostTradeReflection) -> dict[str, Any]:
        return reflection.model_dump()

    def to_json(self, reflection: PostTradeReflection, indent: int = 2) -> str:
        return reflection.model_dump_json(indent=indent)
