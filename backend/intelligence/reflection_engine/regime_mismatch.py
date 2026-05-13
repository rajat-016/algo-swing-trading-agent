from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field
from loguru import logger


REGIME_DIRECTION_MAP: dict[str, str] = {
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

REGIME_RISK_BIAS: dict[str, str] = {
    "bull_trend": "long",
    "breakout": "long",
    "low_volatility": "long",
    "bear_trend": "short",
    "high_volatility": "avoid",
    "event_driven": "avoid",
    "sideways": "neutral",
    "mean_reversion": "neutral",
    "unstable": "avoid",
}


class RegimeMismatchEntry(BaseModel):
    regime: str = Field(description="Market regime")
    total_trades: int = Field(description="Total trades in this regime")
    failed_trades: int = Field(description="Failed trades in this regime")
    mismatch_rate: float = Field(description="Failure rate in this regime")
    overall_failure_rate: float = Field(description="Overall system failure rate")
    relative_risk: float = Field(description="Relative risk ratio vs overall")
    direction_bias: str = Field(description="bullish/bearish/neutral/avoid")
    avg_pnl: float = Field(default=0.0)
    recommendation: str = Field(default="")


class RegimeMismatchReport(BaseModel):
    mismatches: list[RegimeMismatchEntry] = Field(default_factory=list)
    total_trades_analyzed: int = Field(default=0)
    regimes_with_elevated_risk: list[str] = Field(default_factory=list)
    highest_mismatch_regime: Optional[str] = Field(default=None)
    overall_failure_rate: float = Field(default=0.0)
    regime_transition_impact: Optional[float] = Field(default=None)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RegimeMismatchDetector:
    def __init__(self, analytics_db=None, regime_service=None):
        self._analytics_db = analytics_db
        self._regime_service = regime_service
        self._regime_engine = None

    def _get_analytics_db(self):
        if self._analytics_db is not None:
            return self._analytics_db
        try:
            from core.analytics_db import AnalyticsDB
            self._analytics_db = AnalyticsDB()
            return self._analytics_db
        except Exception:
            return None

    def _get_current_regime(self) -> Optional[str]:
        try:
            if self._regime_engine is None:
                from intelligence.market_regime.service import RegimeService
                from intelligence.market_regime.config import RegimeConfig
                self._regime_engine = RegimeService(config=RegimeConfig())
            current = self._regime_engine.get_current_regime()
            if current:
                return str(current.regime.value) if hasattr(current.regime, "value") else str(current.regime)
        except Exception as e:
            logger.warning(f"Failed to get current regime: {e}")
        return None

    def analyze(self, trades: Optional[list[dict]] = None) -> RegimeMismatchReport:
        if trades is None:
            trades = self._load_trades_from_db()

        if not trades:
            return RegimeMismatchReport()

        total = len(trades)
        registry: dict[str, dict] = {}
        for t in trades:
            regime = (t.get("market_region") or t.get("market_regime", "unknown")).lower()
            if regime not in registry:
                registry[regime] = {"total": 0, "failed": 0, "pnl_sum": 0.0}
            registry[regime]["total"] += 1
            registry[regime]["pnl_sum"] += float(t.get("pnl", 0) or 0)
            if self._is_failure(t):
                registry[regime]["failed"] += 1

        total_failures = sum(r["failed"] for r in registry.values())
        overall_failure_rate = total_failures / total if total > 0 else 0

        entries = []
        elevated_risk_regimes = []
        highest_mismatch_rate = 0
        highest_mismatch_regime = None

        for regime, data in registry.items():
            rate = data["failed"] / data["total"] if data["total"] > 0 else 0
            relative_risk = rate / overall_failure_rate if overall_failure_rate > 0 else 1.0
            direction = REGIME_DIRECTION_MAP.get(regime, "unknown")
            bias = REGIME_RISK_BIAS.get(regime, "neutral")

            rec = ""
            if relative_risk > 1.5 and rate > 0.3:
                elevated_risk_regimes.append(regime)
                rec = f"Consider avoiding or reducing position sizes in {regime} regime"
            elif relative_risk > 1.0:
                rec = f"Monitor trades in {regime} regime more closely"

            if rate > highest_mismatch_rate:
                highest_mismatch_rate = rate
                highest_mismatch_regime = regime

            entries.append(RegimeMismatchEntry(
                regime=regime,
                total_trades=data["total"],
                failed_trades=data["failed"],
                mismatch_rate=round(rate, 4),
                overall_failure_rate=round(overall_failure_rate, 4),
                relative_risk=round(relative_risk, 4),
                direction_bias=bias,
                avg_pnl=round(data["pnl_sum"] / data["total"], 2) if data["total"] > 0 else 0,
                recommendation=rec,
            ))

        entries.sort(key=lambda e: e.relative_risk, reverse=True)

        current = self._get_current_regime()
        transition_impact = None
        if current and current in elevated_risk_regimes:
            transition_impact = relative_risk_for_entry(entries, current)

        return RegimeMismatchReport(
            mismatches=entries,
            total_trades_analyzed=total,
            regimes_with_elevated_risk=elevated_risk_regimes,
            highest_mismatch_regime=highest_mismatch_regime,
            overall_failure_rate=round(overall_failure_rate, 4),
            regime_transition_impact=transition_impact,
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
            logger.warning(f"Failed to load trades for regime mismatch analysis: {e}")
            return []

    def _is_failure(self, trade: dict) -> bool:
        outcome = trade.get("outcome", "")
        if isinstance(outcome, str):
            lower = outcome.lower()
            return any(kw in lower for kw in ("loss", "fail", "stop", "sl"))
        pnl = float(trade.get("pnl", 0) or 0)
        return pnl < 0


def relative_risk_for_entry(entries: list[RegimeMismatchEntry], regime: str) -> Optional[float]:
    for e in entries:
        if e.regime == regime:
            return e.relative_risk
    return None
