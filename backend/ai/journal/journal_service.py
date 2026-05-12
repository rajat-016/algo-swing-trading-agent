from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Optional

from loguru import logger

from core.config import get_settings


class TradeJournalService:
    def __init__(self):
        self._settings = get_settings()
        self._semantic_retriever = None
        self._analytics_db = None
        self._duckdb_analytics = None
        self._regime_service = None
        self._trade_intelligence_service = None
        self._initialized = False

    async def initialize(self):
        if self._initialized:
            return
        try:
            await self._get_semantic_retriever()
            self._initialized = True
            logger.info("TradeJournalService initialized")
        except Exception as e:
            logger.warning(f"TradeJournalService init failed (non-critical): {e}")

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

    def _get_analytics_db(self):
        if self._analytics_db is not None:
            return self._analytics_db
        try:
            from core.analytics_db import AnalyticsDB
            self._analytics_db = AnalyticsDB()
        except Exception as e:
            logger.warning(f"AnalyticsDB not available: {e}")
        return self._analytics_db

    def _get_duckdb(self):
        if self._duckdb_analytics is not None:
            return self._duckdb_analytics
        try:
            from ai.inference.duckdb_setup import DuckDBAnalytics
            self._duckdb_analytics = DuckDBAnalytics()
        except Exception as e:
            logger.warning(f"DuckDBAnalytics not available: {e}")
        return self._duckdb_analytics

    def _get_regime_service(self):
        if self._regime_service is not None:
            return self._regime_service
        try:
            from intelligence.market_regime.service import RegimeService
            self._regime_service = RegimeService()
        except Exception as e:
            logger.debug(f"RegimeService not available: {e}")
        return self._regime_service

    def _get_trade_intelligence_service(self):
        if self._trade_intelligence_service is not None:
            return self._trade_intelligence_service
        try:
            from intelligence.trade_analysis.service import TradeIntelligenceService
            self._trade_intelligence_service = TradeIntelligenceService()
        except Exception as e:
            logger.debug(f"TradeIntelligenceService not available: {e}")
        return self._trade_intelligence_service

    @property
    def enabled(self) -> bool:
        return self._settings.ai_copilot_enabled

    def _get_current_regime(self) -> Optional[str]:
        regime_svc = self._get_regime_service()
        if regime_svc is None:
            return None
        try:
            current = regime_svc.get_current_regime()
            if current:
                return current.regime.value if hasattr(current.regime, "value") else str(current.regime)
        except Exception as e:
            logger.debug(f"Failed to get current regime: {e}")
        return None

    def _build_portfolio_state(self, db=None) -> Optional[dict]:
        try:
            from models.stock import Stock, StockStatus
            if db is None:
                return None
            stocks = db.query(Stock).filter(
                Stock.status == StockStatus.ENTERED
            ).all()
            total_exposure = 0.0
            positions = []
            for s in stocks:
                exposure = (s.entry_price or 0) * (s.remaining_quantity or s.entry_quantity or 0)
                total_exposure += exposure
                positions.append({
                    "symbol": s.symbol,
                    "entry_price": s.entry_price,
                    "quantity": s.remaining_quantity or s.entry_quantity,
                    "exposure": exposure,
                    "current_tier": s.current_tier,
                })
            return {
                "positions_count": len(positions),
                "total_exposure": total_exposure,
                "positions": positions,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.debug(f"Failed to build portfolio state: {e}")
            return None

    async def journal_entry(
        self,
        trade_data: dict,
        db=None,
    ):
        if not self.enabled:
            return
        start = time.monotonic()
        try:
            retriever = await self._get_semantic_retriever()
            if retriever is None:
                return

            from memory.schemas.memory_schemas import TradeMemory

            regime = trade_data.get("market_regime") or self._get_current_regime()
            portfolio = trade_data.get("portfolio_state") or self._build_portfolio_state(db)
            timestamp = trade_data.get("timestamp") or datetime.now(timezone.utc).isoformat()

            trade = TradeMemory(
                trade_id=str(trade_data["trade_id"]),
                ticker=trade_data["symbol"],
                timestamp=timestamp,
                market_regime=regime,
                feature_snapshot=trade_data.get("feature_snapshot"),
                prediction=trade_data.get("prediction", "BUY"),
                confidence=trade_data.get("confidence"),
                reasoning=trade_data.get("reasoning", "Trade entry"),
                outcome="OPEN",
                portfolio_state=portfolio,
            )
            await retriever.store_trade(trade)

            self._store_to_duckdb(trade_data, regime, portfolio)

            logger.debug(
                f"Journaled entry: {trade_data['symbol']} ({trade_data.get('trade_id')}) "
                f"in {time.monotonic() - start:.3f}s"
            )
        except Exception as e:
            logger.warning(f"Trade journal entry failed (non-critical): {e}")

    async def journal_exit(
        self,
        trade_data: dict,
        db=None,
    ):
        if not self.enabled:
            return
        try:
            outcome = "WIN" if trade_data.get("pnl", 0) >= 0 else "LOSS"
            trade_id = str(trade_data["trade_id"])

            self._backfill_chromadb_outcome(trade_id, outcome, trade_data)
            self._backfill_duckdb_outcome(trade_id, outcome, trade_data)

            await self._journal_post_trade_summary(trade_data, outcome, db)

            logger.debug(f"Journaled exit: {trade_data.get('symbol')} ({trade_id}) -> {outcome}")
        except Exception as e:
            logger.warning(f"Trade journal exit failed (non-critical): {e}")

    async def journal_partial_exit(
        self,
        trade_data: dict,
    ):
        if not self.enabled:
            return
        try:
            trade_id = str(trade_data["trade_id"])
            tier = trade_data.get("tier", 1)
            remaining = trade_data.get("remaining_quantity", 0)

            self._append_partial_exit_to_notes(trade_id, trade_data)

            logger.debug(f"Journaled partial exit: {trade_data.get('symbol')} tier={tier} remaining={remaining}")
        except Exception as e:
            logger.warning(f"Trade journal partial exit failed (non-critical): {e}")

    def _store_to_duckdb(self, trade_data: dict, regime: Optional[str], portfolio: Optional[dict]):
        try:
            trade_row = {
                "trade_id": str(trade_data["trade_id"]),
                "symbol": trade_data["symbol"],
                "timestamp": trade_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "market_regime": regime,
                "feature_snapshot": json.dumps(trade_data.get("feature_snapshot") or {}),
                "prediction": trade_data.get("prediction", "BUY"),
                "confidence": trade_data.get("confidence"),
                "reasoning": trade_data.get("reasoning", ""),
                "outcome": "OPEN",
                "portfolio_state": json.dumps(portfolio) if portfolio else None,
                "schema_version": "1.0",
            }
            duck = self._get_duckdb()
            if duck and duck.is_ready:
                duck.insert_trade_memory(trade_row)
            else:
                analytics = self._get_analytics_db()
                if analytics:
                    analytics.insert_trade_memory(trade_row)
        except Exception as e:
            logger.debug(f"DuckDB store failed: {e}")

    def _backfill_chromadb_outcome(self, trade_id: str, outcome: str, trade_data: dict):
        try:
            from memory.chromadb.collection_manager import MemoryCollectionManager
            from memory.schemas.memory_schemas import MemoryType

            cm = MemoryCollectionManager()
            collection_name = cm.COLLECTION_NAMES[MemoryType.TRADE]
            doc_id = f"trade_{trade_id}_{trade_data.get('symbol', '')}"

            cm._client.update_metadatas(
                collection_name=collection_name,
                ids=[doc_id],
                metadatas=[{
                    "outcome": outcome,
                    "closed_at": datetime.now(timezone.utc).isoformat(),
                }],
            )
        except Exception as e:
            logger.debug(f"ChromaDB backfill failed: {e}")

    def _backfill_duckdb_outcome(self, trade_id: str, outcome: str, trade_data: dict):
        try:
            duck = self._get_duckdb()
            if duck and duck.is_ready:
                duck.execute(
                    """UPDATE trade_memory SET outcome = ?, pnl = ?, pnl_pct = ?, exit_price = ?, exit_reason = ?, closed_at = ? WHERE trade_id = ?""",
                    [
                        outcome,
                        trade_data.get("pnl"),
                        trade_data.get("pnl_pct"),
                        trade_data.get("exit_price"),
                        str(trade_data.get("exit_reason", "")),
                        datetime.now(timezone.utc).isoformat(),
                        trade_id,
                    ],
                )
        except Exception as e:
            logger.debug(f"DuckDB backfill failed: {e}")

    def _append_partial_exit_to_notes(self, trade_id: str, trade_data: dict):
        try:
            duck = self._get_duckdb()
            if duck and duck.is_ready:
                existing = duck.fetch_one(
                    "SELECT reflection_notes FROM trade_memory WHERE trade_id = ?",
                    [trade_id],
                )
                notes = existing[0] if existing and existing[0] else ""
                tier_entry = (
                    f"[Tier {trade_data.get('tier')}] "
                    f"Partial exit at Rs.{trade_data.get('exit_price', 0):.2f} "
                    f"qty={trade_data.get('quantity', 0)} "
                    f"pnl={trade_data.get('pnl', 0):.2f} | "
                )
                new_notes = (notes + tier_entry) if notes else tier_entry
                duck.execute(
                    "UPDATE trade_memory SET reflection_notes = ? WHERE trade_id = ?",
                    [new_notes, trade_id],
                )
        except Exception as e:
            logger.debug(f"Partial exit notes append failed: {e}")

    async def _journal_post_trade_summary(self, trade_data: dict, outcome: str, db=None):
        try:
            retriever = await self._get_semantic_retriever()
            if retriever is None:
                return

            trade_id = str(trade_data["trade_id"])
            symbol = trade_data.get("symbol", "")

            summary_text = (
                f"Trade {trade_id}: {symbol} closed with {outcome}. "
                f"P&L: {trade_data.get('pnl', 0):.2f} "
                f"({trade_data.get('pnl_pct', 0):.2f}%). "
            )

            pnl = trade_data.get("pnl", 0)
            pnl_pct = trade_data.get("pnl_pct", 0)
            exit_reason = trade_data.get("exit_reason", "")
            if pnl > 0:
                summary_text += f"Profitable exit via {exit_reason.value if hasattr(exit_reason, 'value') else exit_reason}."
            else:
                summary_text += f"Loss closed via {exit_reason.value if hasattr(exit_reason, 'value') else exit_reason}."

            trade_intel = self._get_trade_intelligence_service()
            intelligence = None
            if trade_intel is not None and db is not None:
                try:
                    result = trade_intel.get_reasoning(
                        db=db,
                        symbol=symbol,
                        trade_id=trade_id,
                    )
                    if result.get("status") == "ok":
                        reasoning = result.get("reasoning", {})
                        r = reasoning
                        intelligence = r.get("summary", "") if isinstance(r, dict) else str(r)
                except Exception as e:
                    logger.debug(f"Post-trade intelligence failed: {e}")

            notes_parts = [summary_text]
            if intelligence:
                notes_parts.append(f"Analysis: {intelligence}")
            reflection_notes = " | ".join(notes_parts)

            from memory.schemas.memory_schemas import TradeMemory
            trade = TradeMemory(
                trade_id=trade_id,
                ticker=symbol,
                timestamp=datetime.now(timezone.utc).isoformat(),
                reasoning=summary_text,
                outcome=outcome,
                reflection_notes=reflection_notes,
            )
            await retriever.store_trade(trade)

            duck = self._get_duckdb()
            if duck and duck.is_ready:
                duck.execute(
                    "UPDATE trade_memory SET reflection_notes = ? WHERE trade_id = ?",
                    [reflection_notes, trade_id],
                )

            logger.debug(f"Post-trade summary stored for {trade_id}")
        except Exception as e:
            logger.debug(f"Post-trade summary failed: {e}")

    async def search_trades(
        self,
        query: str,
        ticker: Optional[str] = None,
        outcome: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict]:
        if not self.enabled:
            return []
        try:
            retriever = await self._get_semantic_retriever()
            if retriever is None:
                return []

            from memory.schemas.memory_schemas import MemoryFilter, MemoryType
            mf = MemoryFilter(
                memory_type=MemoryType.TRADE,
                ticker=ticker,
                outcome=outcome,
                max_results=limit,
            )
            results = await retriever.search(query, memory_filter=mf, n_results=limit)
            return [
                {
                    "id": r.id,
                    "text": r.text[:500],
                    "metadata": r.metadata,
                    "relevance": r.relevance_score,
                }
                for r in results
            ]
        except Exception as e:
            logger.warning(f"Trade search failed: {e}")
            return []

    def get_recent_duckdb_trades(self, limit: int = 50) -> list[dict]:
        try:
            duck = self._get_duckdb()
            if duck and duck.is_ready:
                rows = duck.get_recent_trades(limit)
                columns = [
                    "trade_id", "symbol", "timestamp", "market_regime",
                    "feature_snapshot", "prediction", "confidence", "reasoning",
                    "outcome", "portfolio_state", "reflection_notes",
                    "schema_version", "created_at",
                ]
                result = []
                for row in rows:
                    d = dict(zip(columns, row))
                    d["id"] = d["trade_id"]
                    result.append(d)
                return result
            analytics = self._get_analytics_db()
            if analytics:
                rows = analytics.get_recent_trades(limit)
                columns = [
                    "trade_id", "symbol", "timestamp", "market_regime",
                    "feature_snapshot", "prediction", "confidence", "reasoning",
                    "outcome", "portfolio_state", "reflection_notes",
                    "schema_version", "created_at",
                ]
                result = []
                for row in rows:
                    d = dict(zip(columns[:len(row)], row))
                    d["id"] = d["trade_id"]
                    result.append(d)
                return result
        except Exception as e:
            logger.debug(f"Failed to get recent trades: {e}")
        return []

    def get_trade_by_id(self, trade_id: str) -> Optional[dict]:
        try:
            duck = self._get_duckdb()
            if duck and duck.is_ready:
                row = duck.fetch_one(
                    "SELECT * FROM trade_memory WHERE trade_id = ?",
                    [trade_id],
                )
                if row:
                    columns = [
                        "trade_id", "symbol", "timestamp", "market_regime",
                        "feature_snapshot", "prediction", "confidence", "reasoning",
                        "outcome", "portfolio_state", "reflection_notes",
                        "schema_version", "created_at",
                    ]
                    d = dict(zip(columns, row))
                    d["id"] = d["trade_id"]
                    return d
        except Exception as e:
            logger.debug(f"Failed to get trade by id: {e}")
        return None

    async def get_journal_stats(self) -> dict:
        stats = {"enabled": self.enabled}
        try:
            retriever = await self._get_semantic_retriever()
            if retriever:
                mem_stats = await retriever.get_memory_stats()
                stats["chromadb"] = {
                    "trade_memory_count": mem_stats.get("trade_memory", {}).get("count", 0),
                }
        except Exception:
            stats["chromadb"] = {"error": "unavailable"}
        try:
            duck = self._get_duckdb()
            if duck and duck.is_ready:
                count = duck.fetch_one("SELECT COUNT(*) FROM trade_memory")
                stats["duckdb_trade_count"] = count[0] if count else 0
            else:
                stats["duckdb"] = "unavailable"
        except Exception:
            stats["duckdb"] = "unavailable"
        return stats
