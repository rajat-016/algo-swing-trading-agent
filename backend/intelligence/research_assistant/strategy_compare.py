from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field
from loguru import logger


class StrategyMetrics(BaseModel):
    strategy_name: str
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: Optional[float] = None
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: Optional[float] = None
    expectancy: float = 0.0
    win_loss_ratio: float = 0.0


class StrategyComparisonResult(BaseModel):
    strategies: list[StrategyMetrics] = Field(default_factory=list)
    best_strategy: Optional[str] = None
    worst_strategy: Optional[str] = None
    rank_by: str = "win_rate"
    rankings: list[dict] = Field(default_factory=list)
    gap_analysis: list[dict] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    summary: str = ""


class StrategyComparator:
    def __init__(self, analytics_db=None):
        self._analytics_db = analytics_db

    def _get_db(self):
        if self._analytics_db is not None:
            return self._analytics_db
        try:
            from core.analytics_db import AnalyticsDB
            self._analytics_db = AnalyticsDB()
            return self._analytics_db
        except Exception:
            return None

    async def compare_strategies(
        self,
        strategies: list[str],
        trades: Optional[list[dict]] = None,
        metric: str = "win_rate",
    ) -> StrategyComparisonResult:
        metrics_list = []
        for strategy in strategies:
            strategy_trades = await self._filter_trades(trades, strategy)
            if not strategy_trades:
                metrics_list.append(StrategyMetrics(strategy_name=strategy))
                continue
            m = self._compute_metrics(strategy, strategy_trades)
            metrics_list.append(m)

        if not metrics_list:
            return StrategyComparisonResult(summary="No strategy data available")

        valid = [m for m in metrics_list if m.total_trades > 0]
        if not valid:
            return StrategyComparisonResult(
                strategies=metrics_list,
                summary="No strategies with trade data",
            )

        sorted_metrics = sorted(valid, key=lambda m: getattr(m, metric, 0), reverse=True)
        rankings = []
        for rank, m in enumerate(sorted_metrics, 1):
            rankings.append({"rank": rank, "strategy": m.strategy_name, metric: getattr(m, metric, 0)})

        best = sorted_metrics[0].strategy_name if sorted_metrics else None
        worst = sorted_metrics[-1].strategy_name if len(sorted_metrics) > 1 else None

        gaps = []
        if len(sorted_metrics) >= 2:
            best_val = getattr(sorted_metrics[0], metric, 0)
            for m in sorted_metrics[1:]:
                val = getattr(m, metric, 0)
                gap_pct = ((best_val - val) / best_val * 100) if best_val != 0 else 0
                gaps.append({
                    "strategy": m.strategy_name,
                    f"{metric}_gap_pct": round(gap_pct, 2),
                    f"improvement_to_match_{sorted_metrics[0].strategy_name}": round(best_val - val, 4),
                })

        summary = f"Best: {best} ({metric}={getattr(sorted_metrics[0], metric, 0):.3f}) | "
        if worst:
            summary += f"Worst: {worst} ({metric}={getattr(sorted_metrics[-1], metric, 0):.3f}) | "
        summary += f"{len(valid)}/{len(strategies)} strategies with trades"

        return StrategyComparisonResult(
            strategies=metrics_list,
            best_strategy=best,
            worst_strategy=worst,
            rank_by=metric,
            rankings=rankings,
            gap_analysis=gaps,
            summary=summary,
        )

    async def _filter_trades(self, trades: Optional[list[dict]], strategy: str) -> list[dict]:
        if trades is not None:
            return [t for t in trades if str(t.get("strategy", "")).lower() == strategy.lower()]
        db = self._get_db()
        if db is None:
            return []
        try:
            rows = db.fetch_all(
                "SELECT * FROM trade_memory WHERE strategy = ? ORDER BY created_at DESC",
                [strategy],
            )
            return [dict(zip([col[0] for col in (db.description or [])], row)) for row in rows]
        except Exception as e:
            logger.debug(f"Failed to query trades for strategy '{strategy}': {e}")
            return []

    def _compute_metrics(self, name: str, trades: list[dict]) -> StrategyMetrics:
        total = len(trades)
        if total == 0:
            return StrategyMetrics(strategy_name=name)

        wins = [t for t in trades if t.get("outcome") in ("WIN", "success", "target_hit")]
        losses = [t for t in trades if t.get("outcome") in ("LOSS", "failed", "stop_loss_hit")]
        win_count = len(wins)
        loss_count = len(losses)

        win_rate = win_count / total if total > 0 else 0.0
        avg_win = sum(abs(t.get("pnl", 0)) for t in wins) / win_count if win_count > 0 else 0.0
        avg_loss = sum(abs(t.get("pnl", 0)) for t in losses) / loss_count if loss_count > 0 else 0.0
        profit_factor = (avg_win * win_count) / (avg_loss * loss_count) if loss_count > 0 and avg_loss > 0 else None if win_count > 0 else None
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss) if total > 0 else 0.0
        win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0

        return StrategyMetrics(
            strategy_name=name,
            total_trades=total,
            win_rate=round(win_rate, 4),
            profit_factor=round(profit_factor, 4) if profit_factor is not None and profit_factor != float("inf") else profit_factor,
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            max_drawdown=round(max(abs(t.get("max_drawdown", 0)) for t in trades), 4) if trades else 0.0,
            expectancy=round(expectancy, 4),
            win_loss_ratio=round(win_loss_ratio, 4),
        )
