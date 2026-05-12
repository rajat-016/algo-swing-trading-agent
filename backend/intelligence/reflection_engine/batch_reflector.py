from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from loguru import logger


class BatchReflector:
    def __init__(self, orchestration_engine=None):
        self._orchestration_engine = orchestration_engine

    async def _get_orchestration_engine(self):
        if self._orchestration_engine is not None:
            return self._orchestration_engine
        try:
            from ai.orchestration.engine import OrchestrationEngine
            self._orchestration_engine = OrchestrationEngine()
        except Exception as e:
            logger.warning(f"OrchestrationEngine not available: {e}")
        return self._orchestration_engine

    async def generate_reflection(
        self,
        period: str,
        total_trades: int,
        win_rate: float,
        profit_factor: float,
        avg_win: float,
        avg_loss: float,
        max_drawdown: float,
        regime_breakdown: str,
        feature_stability: str,
        failure_patterns: str,
    ) -> Optional[str]:
        try:
            engine = await self._get_orchestration_engine()
            if engine is None:
                return None
            return await engine.generate_reflection(
                period=period,
                total_trades=total_trades,
                win_rate=win_rate,
                profit_factor=profit_factor,
                avg_win=avg_win,
                avg_loss=avg_loss,
                max_drawdown=max_drawdown,
                regime_breakdown=regime_breakdown,
                feature_stability=feature_stability,
                failure_patterns=failure_patterns,
            )
        except Exception as e:
            logger.warning(f"Batch reflection generation failed: {e}")
            return None

    def store_reflection_log(
        self,
        db,
        period_start: str,
        period_end: str,
        reflection_type: str,
        content: str,
        metrics_snapshot: Optional[dict] = None,
    ):
        try:
            if hasattr(db, "insert_reflection_log"):
                db.execute(
                    """INSERT INTO reflection_log (period_start, period_end, reflection_type, content, metrics_snapshot)
                       VALUES (?, ?, ?, ?, ?)""",
                    [period_start, period_end, reflection_type, content,
                     str(metrics_snapshot) if metrics_snapshot else None],
                )
        except Exception as e:
            logger.warning(f"Failed to store reflection log: {e}")

    async def reflect_on_recent_trades(
        self,
        trades: list[dict],
        period_label: str = "recent",
    ) -> Optional[dict[str, Any]]:
        if not trades:
            return None

        total = len(trades)
        wins = sum(1 for t in trades if t.get("outcome") == "WIN" or t.get("pnl", 0) >= 0)
        losses = total - wins
        win_rate = wins / total if total > 0 else 0.0

        total_pnl = sum(t.get("pnl", 0) for t in trades)
        gross_profit = sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) > 0)
        gross_loss = abs(sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        avg_win = gross_profit / wins if wins > 0 else 0.0
        avg_loss = gross_loss / losses if losses > 0 else 0.0

        pnl_values = [t.get("pnl", 0) for t in trades]
        running_max = 0
        max_dd = 0
        cumulative = 0
        for v in pnl_values:
            cumulative += v
            running_max = max(running_max, cumulative)
            dd = running_max - cumulative
            max_dd = max(max_dd, dd)

        regimes = {}
        for t in trades:
            r = t.get("market_regime", "unknown")
            regimes[r] = regimes.get(r, 0) + 1
        regime_breakdown = ", ".join(f"{k}: {v}" for k, v in regimes.items())

        feature_stability = "Not analyzed"
        failure_patterns = "Not analyzed"

        content = await self.generate_reflection(
            period=period_label,
            total_trades=total,
            win_rate=round(win_rate, 3),
            profit_factor=round(profit_factor, 2),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            max_drawdown=round(max_dd, 2),
            regime_breakdown=regime_breakdown,
            feature_stability=feature_stability,
            failure_patterns=failure_patterns,
        )

        metrics = {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 3),
            "profit_factor": round(profit_factor, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "max_drawdown": round(max_dd, 2),
            "total_pnl": round(total_pnl, 2),
        }

        return {
            "period": period_label,
            "content": content,
            "metrics": metrics,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
