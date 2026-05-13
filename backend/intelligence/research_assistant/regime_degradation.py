from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field
from loguru import logger


class RegimePerformance(BaseModel):
    regime: str
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: Optional[float] = None
    avg_return: float = 0.0
    max_drawdown: float = 0.0
    trade_frequency: float = 0.0


class RegimeDegradationReport(BaseModel):
    regime_performances: list[RegimePerformance] = Field(default_factory=list)
    worst_regime: Optional[str] = None
    best_regime: Optional[str] = None
    degraded_regimes: list[RegimePerformance] = Field(default_factory=list)
    regime_stability: dict[str, str] = Field(default_factory=dict)
    transition_impact: list[dict] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    summary: str = ""


class RegimeDegradationAnalyzer:
    def __init__(self, regime_service=None, analytics_db=None):
        self._regime_service = regime_service
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

    async def analyze_regime_degradation(
        self,
        trades: Optional[list[dict]] = None,
        min_trades_per_regime: int = 3,
    ) -> RegimeDegradationReport:
        regime_trades = await self._group_trades_by_regime(trades)
        if not regime_trades:
            return RegimeDegradationReport(summary="No regime-tagged trade data available")

        performances = []
        for regime_name, regime_trade_list in regime_trades.items():
            if len(regime_trade_list) < min_trades_per_regime:
                continue
            perf = self._compute_regime_performance(regime_name, regime_trade_list)
            performances.append(perf)

        if not performances:
            return RegimeDegradationReport(summary="Insufficient trades per regime for analysis")

        sorted_by_wr = sorted(performances, key=lambda p: p.win_rate, reverse=True)
        best_regime = sorted_by_wr[0].regime if sorted_by_wr else None
        worst_regime = sorted_by_wr[-1].regime if len(sorted_by_wr) > 1 else None

        degraded = [p for p in performances if p.win_rate < 0.4]

        regime_stability = {}
        for p in performances:
            if p.win_rate >= 0.6:
                regime_stability[p.regime] = "favorable"
            elif p.win_rate >= 0.4:
                regime_stability[p.regime] = "neutral"
            else:
                regime_stability[p.regime] = "unfavorable"

        transition_impact = self._analyze_transition_impact(performances)

        summary_parts = []
        if best_regime:
            best_perf = next(p for p in performances if p.regime == best_regime)
            summary_parts.append(f"Best: {best_regime} (WR={best_perf.win_rate:.1%})")
        if worst_regime:
            worst_perf = next(p for p in performances if p.regime == worst_regime)
            summary_parts.append(f"Worst: {worst_regime} (WR={worst_perf.win_rate:.1%})")
        if degraded:
            summary_parts.append(f"{len(degraded)} degraded regimes (WR<40%)")
        summary_parts.append(f"{len(performances)} regimes analyzed")

        return RegimeDegradationReport(
            regime_performances=performances,
            worst_regime=worst_regime,
            best_regime=best_regime,
            degraded_regimes=degraded,
            regime_stability=regime_stability,
            transition_impact=transition_impact,
            summary=" | ".join(summary_parts),
        )

    async def _group_trades_by_regime(self, trades: Optional[list[dict]]) -> dict[str, list[dict]]:
        if trades is not None:
            grouped: dict[str, list[dict]] = {}
            for t in trades:
                regime = t.get("market_regime") or t.get("regime", "unknown")
                if regime not in grouped:
                    grouped[regime] = []
                grouped[regime].append(t)
            return grouped

        db = self._get_db()
        if db is None:
            return {}
        try:
            rows = db.fetch_all(
                "SELECT market_regime, outcome, pnl, pnl_pct FROM trade_memory WHERE market_regime IS NOT NULL"
            )
            grouped = {}
            for r in rows:
                d = dict(zip([col[0] for col in (db.description or [])], r))
                regime = d.get("market_regime", "unknown")
                if regime not in grouped:
                    grouped[regime] = []
                grouped[regime].append(d)
            return grouped
        except Exception as e:
            logger.debug(f"Failed to group trades by regime: {e}")
            return {}

    def _compute_regime_performance(self, regime: str, trades: list[dict]) -> RegimePerformance:
        total = len(trades)
        if total == 0:
            return RegimePerformance(regime=regime)

        wins = [t for t in trades if t.get("outcome") in ("WIN", "success", "target_hit")]
        losses = [t for t in trades if t.get("outcome") in ("LOSS", "failed", "stop_loss_hit")]
        win_count = len(wins)
        loss_count = len(losses)

        win_rate = win_count / total if total > 0 else 0.0
        avg_win = sum(abs(t.get("pnl", 0)) for t in wins) / win_count if win_count > 0 else 0.0
        avg_loss = sum(abs(t.get("pnl", 0)) for t in losses) / loss_count if loss_count > 0 else 0.0
        profit_factor = (avg_win * win_count) / (avg_loss * loss_count) if loss_count > 0 and avg_loss > 0 else None if win_count > 0 else None

        returns = [t.get("pnl_pct", 0) or t.get("pnl", 0) for t in trades if t.get("pnl_pct") is not None or t.get("pnl") is not None]
        avg_return = sum(returns) / len(returns) if returns else 0.0

        return RegimePerformance(
            regime=regime,
            total_trades=total,
            win_rate=round(win_rate, 4),
            profit_factor=round(profit_factor, 4) if profit_factor is not None and profit_factor != float("inf") else profit_factor,
            avg_return=round(avg_return, 4),
            trade_frequency=round(total, 2),
        )

    def _analyze_transition_impact(self, performances: list[RegimePerformance]) -> list[dict]:
        if len(performances) < 2:
            return []
        impacts = []
        for i in range(len(performances) - 1):
            curr = performances[i]
            next_p = performances[i + 1]
            if curr.win_rate > 0 and next_p.win_rate > 0:
                wr_change = ((next_p.win_rate - curr.win_rate) / curr.win_rate) * 100
                impacts.append({
                    "from_regime": curr.regime,
                    "to_regime": next_p.regime,
                    "win_rate_change_pct": round(wr_change, 2),
                    "direction": "improving" if wr_change > 0 else "deteriorating",
                })
        return impacts
