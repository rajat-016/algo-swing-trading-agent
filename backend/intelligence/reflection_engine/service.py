from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from intelligence.reflection_engine.post_trade_reflector import PostTradeReflector, PostTradeReflection
from intelligence.reflection_engine.batch_reflector import BatchReflector


class ReflectionService:
    def __init__(self):
        self._post_trade_reflector: Optional[PostTradeReflector] = None
        self._batch_reflector: Optional[BatchReflector] = None
        self._settings = None

    @property
    def enabled(self) -> bool:
        if self._settings is None:
            try:
                from core.config import get_settings
                self._settings = get_settings()
            except Exception:
                return False
        return getattr(self._settings, "reflection_engine_enabled", False)

    async def get_post_trade_reflector(self) -> Optional[PostTradeReflector]:
        if self._post_trade_reflector is None:
            self._post_trade_reflector = PostTradeReflector()
        return self._post_trade_reflector

    async def get_batch_reflector(self) -> Optional[BatchReflector]:
        if self._batch_reflector is None:
            self._batch_reflector = BatchReflector()
        return self._batch_reflector

    async def reflect_trade(self, trade_data: dict) -> Optional[PostTradeReflection]:
        if not self.enabled:
            return None
        reflector = await self.get_post_trade_reflector()
        if reflector is None:
            return None
        reflection = await reflector.reflect(trade_data)
        if reflection:
            self._store_to_reflection_log(reflection)
        return reflection

    async def batch_reflect(
        self,
        trades: list[dict],
        period_label: str = "recent",
    ) -> Optional[dict[str, Any]]:
        if not self.enabled:
            return None
        reflector = await self.get_batch_reflector()
        if reflector is None:
            return None
        result = await reflector.reflect_on_recent_trades(trades, period_label)
        if result and result.get("content"):
            self._store_batch_reflection_log(result)
        return result

    def _get_db(self):
        from core.analytics_db import AnalyticsDB
        return AnalyticsDB()

    def _store_to_reflection_log(self, reflection: PostTradeReflection):
        try:
            db = self._get_db()
            db.execute(
                """INSERT INTO reflection_log (period_start, period_end, reflection_type, content, metrics_snapshot)
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    None,
                    None,
                    reflection.reflection_type,
                    reflection.model_dump_json(indent=2),
                    None,
                ],
            )
        except Exception as e:
            logger.debug(f"Failed to store reflection to log: {e}")

    def _store_batch_reflection_log(self, result: dict):
        try:
            content = result.get("content", "")
            metrics = result.get("metrics", {})
            period = result.get("period", "recent")
            now = (
                __import__("datetime", fromlist=["datetime"])
                .datetime.now(__import__("datetime", fromlist=["timezone"]).timezone.utc)
                .isoformat()[:10]
            )

            db = self._get_db()
            db.execute(
                """INSERT INTO reflection_log (period_start, period_end, reflection_type, content, metrics_snapshot)
                   VALUES (?, ?, ?, ?, ?)""",
                [now, now, f"batch_{period}", content, str(metrics)],
            )
        except Exception as e:
            logger.debug(f"Failed to store batch reflection log: {e}")

    async def get_reflection_logs(self, limit: int = 50) -> list[dict]:
        try:
            db = self._get_db()
            rows = db.fetch_all(
                "SELECT * FROM reflection_log ORDER BY created_at DESC LIMIT ?",
                [limit],
            )
            columns = ["id", "period_start", "period_end", "reflection_type", "content", "metrics_snapshot", "created_at"]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.debug(f"Failed to get reflection logs: {e}")
        return []
