from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field
from loguru import logger


class DegradationSignal(BaseModel):
    metric: str = Field(description="Metric being tracked")
    current_value: float = Field(description="Current period value")
    baseline_value: float = Field(description="Baseline period value")
    change_pct: float = Field(description="Percent change from baseline")
    threshold_exceeded: bool = Field(description="Whether degradation threshold exceeded")
    direction: str = Field(description="deteriorating/improving/stable")


class StrategyDegradationReport(BaseModel):
    strategy_label: str = Field(description="Strategy or overall label")
    degradation_score: float = Field(description="Composite degradation score 0-1")
    severity: str = Field(description="none/low/medium/high/critical")
    signals: list[DegradationSignal] = Field(default_factory=list)
    recent_trades_count: int = Field(default=0)
    baseline_trades_count: int = Field(default=0)
    recent_win_rate: Optional[float] = Field(default=None)
    baseline_win_rate: Optional[float] = Field(default=None)
    recent_profit_factor: Optional[float] = Field(default=None)
    baseline_profit_factor: Optional[float] = Field(default=None)
    recent_avg_drawdown: Optional[float] = Field(default=None)
    baseline_avg_drawdown: Optional[float] = Field(default=None)
    investigation_needed: bool = Field(default=False)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class StrategyDegradationAnalyzer:
    def __init__(self, analytics_db=None):
        self._analytics_db = analytics_db
        self._baseline_days: int = 60
        self._recent_days: int = 30
        self._min_trades_for_analysis: int = 10

    def _get_analytics_db(self):
        if self._analytics_db is not None:
            return self._analytics_db
        try:
            from core.analytics_db import AnalyticsDB
            self._analytics_db = AnalyticsDB()
            return self._analytics_db
        except Exception:
            return None

    def configure(self, baseline_days: int = 60, recent_days: int = 30, min_trades: int = 10):
        self._baseline_days = baseline_days
        self._recent_days = recent_days
        self._min_trades_for_analysis = min_trades

    def analyze(self, trades: Optional[list[dict]] = None) -> StrategyDegradationReport:
        if trades is None:
            trades = self._load_trades_from_db()

        if not trades:
            return StrategyDegradationReport(
                strategy_label="overall",
                degradation_score=0.0,
                severity="none",
            )

        now = datetime.now(timezone.utc)
        recent_cut = now - timedelta(days=self._recent_days)
        baseline_cut = now - timedelta(days=self._baseline_days)

        recent_trades = [t for t in trades if self._parse_timestamp(t) >= recent_cut]
        baseline_trades = [
            t for t in trades
            if baseline_cut <= self._parse_timestamp(t) < recent_cut
        ]

        if len(recent_trades) < self._min_trades_for_analysis:
            return StrategyDegradationReport(
                strategy_label="overall",
                degradation_score=0.0,
                severity="none",
                recent_trades_count=len(recent_trades),
                baseline_trades_count=len(baseline_trades),
                investigation_needed=len(recent_trades) < 3 and len(trades) >= self._min_trades_for_analysis,
            )

        recent_metrics = self._compute_metrics(recent_trades)
        baseline_metrics = self._compute_metrics(baseline_trades) if baseline_trades else None

        signals = []
        degradation_score = 0.0
        signal_count = 0

        if baseline_metrics:
            sig = self._compare_metric("win_rate", recent_metrics["win_rate"],
                                        baseline_metrics["win_rate"], higher_is_better=True)
            if sig.threshold_exceeded:
                signals.append(sig)
                degradation_score += abs(sig.change_pct) * 0.30
                signal_count += 1

            sig = self._compare_metric("profit_factor", recent_metrics["profit_factor"],
                                        baseline_metrics["profit_factor"], higher_is_better=True)
            if sig.threshold_exceeded:
                signals.append(sig)
                degradation_score += abs(sig.change_pct) * 0.25
                signal_count += 1

            sig = self._compare_metric("avg_drawdown", recent_metrics["avg_drawdown"],
                                        baseline_metrics["avg_drawdown"], higher_is_better=False)
            if sig.threshold_exceeded:
                signals.append(sig)
                degradation_score += abs(sig.change_pct) * 0.20
                signal_count += 1

            sig = self._compare_metric("avg_win_pct", recent_metrics["avg_win_pct"],
                                        baseline_metrics["avg_win_pct"], higher_is_better=True)
            if sig.threshold_exceeded:
                signals.append(sig)
                degradation_score += abs(sig.change_pct) * 0.15
                signal_count += 1

            sig = self._compare_metric("trade_frequency", recent_metrics["trade_frequency"],
                                        baseline_metrics["trade_frequency"], higher_is_better=True,
                                        threshold_pct=0.50)
            if sig.threshold_exceeded:
                signals.append(sig)
                degradation_score += abs(sig.change_pct) * 0.10
                signal_count += 1

        degradation_score = min(degradation_score / max(signal_count, 1), 1.0)

        if degradation_score >= 0.7:
            severity = "critical"
        elif degradation_score >= 0.5:
            severity = "high"
        elif degradation_score >= 0.3:
            severity = "medium"
        elif degradation_score >= 0.1:
            severity = "low"
        else:
            severity = "none"

        return StrategyDegradationReport(
            strategy_label="overall",
            degradation_score=round(degradation_score, 4),
            severity=severity,
            signals=signals,
            recent_trades_count=len(recent_trades),
            baseline_trades_count=len(baseline_trades),
            recent_win_rate=round(recent_metrics["win_rate"], 4),
            baseline_win_rate=round(baseline_metrics["win_rate"], 4) if baseline_metrics else None,
            recent_profit_factor=round(recent_metrics["profit_factor"], 4),
            baseline_profit_factor=round(baseline_metrics["profit_factor"], 4) if baseline_metrics else None,
            recent_avg_drawdown=round(recent_metrics["avg_drawdown"], 4),
            baseline_avg_drawdown=round(baseline_metrics["avg_drawdown"], 4) if baseline_metrics else None,
            investigation_needed=severity in ("high", "critical"),
        )

    def _load_trades_from_db(self) -> list[dict]:
        db = self._get_analytics_db()
        if db is None:
            return []
        try:
            rows = db.fetch_all(
                "SELECT * FROM trade_memory ORDER BY created_at DESC LIMIT 1000"
            )
            columns = ["trade_id", "symbol", "timestamp", "market_regime",
                        "feature_snapshot", "prediction", "confidence", "reasoning",
                        "outcome", "portfolio_state", "reflection_notes", "schema_version", "created_at"]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to load trades for degradation analysis: {e}")
            return []

    def _parse_timestamp(self, trade: dict) -> datetime:
        ts = trade.get("timestamp") or trade.get("created_at") or ""
        if isinstance(ts, datetime):
            return ts
        try:
            return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

    def _compute_metrics(self, trades: list[dict]) -> dict:
        if not trades:
            return {"win_rate": 0, "profit_factor": 0, "avg_drawdown": 0, "avg_win_pct": 0, "trade_frequency": 0}

        total = len(trades)
        wins = sum(1 for t in trades if self._is_win(t))
        losses = total - wins
        win_rate = wins / total if total > 0 else 0

        pnl_values = [float(t.get("pnl", 0) or 0) for t in trades]
        gross_profit = sum(p for p in pnl_values if p > 0)
        gross_loss = abs(sum(p for p in pnl_values if p < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (999 if gross_profit > 0 else 0)

        running_max = 0
        max_dd = 0
        cumulative = 0
        for v in pnl_values:
            cumulative += v
            running_max = max(running_max, cumulative)
            dd = running_max - cumulative
            max_dd = max(max_dd, dd)

        win_pnls = [float(t.get("pnl_pct", 0) or 0) for t in trades if self._is_win(t)]
        avg_win_pct = sum(win_pnls) / len(win_pnls) if win_pnls else 0

        timestamps = [self._parse_timestamp(t) for t in trades]
        if timestamps:
            date_range = (max(timestamps) - min(timestamps)).days or 1
            trade_frequency = total / date_range
        else:
            trade_frequency = 0

        return {
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "avg_drawdown": max_dd,
            "avg_win_pct": avg_win_pct,
            "trade_frequency": trade_frequency,
        }

    def _is_win(self, trade: dict) -> bool:
        outcome = trade.get("outcome", "")
        if isinstance(outcome, str) and outcome.lower() in ("win", "target_hit", "profit"):
            return True
        pnl = float(trade.get("pnl", 0) or 0)
        return pnl >= 0

    def _compare_metric(self, metric: str, current: float, baseline: float,
                         higher_is_better: bool = True, threshold_pct: float = 0.20) -> DegradationSignal:
        if baseline == 0:
            change_pct = 0
            threshold_exceeded = False
        else:
            change_pct = (current - baseline) / abs(baseline)

        if higher_is_better:
            threshold_exceeded = change_pct < -threshold_pct
            direction = "deteriorating" if change_pct < -threshold_pct else (
                "improving" if change_pct > threshold_pct else "stable"
            )
        else:
            threshold_exceeded = change_pct > threshold_pct
            direction = "deteriorating" if change_pct > threshold_pct else (
                "improving" if change_pct < -threshold_pct else "stable"
            )

        return DegradationSignal(
            metric=metric,
            current_value=round(current, 4),
            baseline_value=round(baseline, 4),
            change_pct=round(change_pct, 4),
            threshold_exceeded=threshold_exceeded,
            direction=direction,
        )
