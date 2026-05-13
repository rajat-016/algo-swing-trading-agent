from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field
from loguru import logger


class InstabilityFactor(BaseModel):
    source: str = Field(description="Source system: trade/regime/portfolio/explainability/memory")
    factor: str = Field(description="Specific factor identifier")
    value: float = Field(description="Measured value")
    threshold: float = Field(description="Threshold for concern")
    is_alert: bool = Field(description="Whether threshold exceeded")
    description: str = Field(description="Human-readable description")
    severity: str = Field(description="low/medium/high/critical")


class InstabilityReport(BaseModel):
    composite_score: float = Field(description="Composite instability score 0-1")
    severity: str = Field(description="stable/low/medium/high/critical")
    factors: list[InstabilityFactor] = Field(default_factory=list)
    alert_count: int = Field(default=0)
    critical_factors: list[InstabilityFactor] = Field(default_factory=list)
    regime_stability: Optional[str] = Field(default=None)
    portfolio_risk_level: Optional[str] = Field(default=None)
    feature_stability_status: Optional[str] = Field(default=None)
    recent_regime_transitions: int = Field(default=0)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class InstabilityReporter:
    def __init__(self, analytics_db=None):
        self._analytics_db = analytics_db

    def _get_analytics_db(self):
        if self._analytics_db is not None:
            return self._analytics_db
        try:
            from core.analytics_db import AnalyticsDB
            self._analytics_db = AnalyticsDB()
            return self._analytics_db
        except Exception:
            return None

    def generate_report(
        self,
        regime_data: Optional[dict] = None,
        portfolio_data: Optional[dict] = None,
        trades: Optional[list[dict]] = None,
    ) -> InstabilityReport:
        factors: list[InstabilityFactor] = []
        db = self._get_analytics_db()

        if trades is None:
            trades = self._load_trades(db)
        if regime_data is None:
            regime_data = self._load_regime_data(db)
        if portfolio_data is None:
            portfolio_data = self._load_portfolio_data(db)

        factors.extend(self._assess_regime_factors(regime_data))
        factors.extend(self._assess_portfolio_factors(portfolio_data))
        factors.extend(self._assess_trade_factors(trades))
        factors.extend(self._assess_feature_drift(db))

        alerts = [f for f in factors if f.is_alert]
        critical = [f for f in alerts if f.severity in ("high", "critical")]

        composite = self._compute_composite(factors)

        if composite >= 0.7:
            severity = "critical"
        elif composite >= 0.5:
            severity = "high"
        elif composite >= 0.3:
            severity = "medium"
        elif composite >= 0.1:
            severity = "low"
        else:
            severity = "stable"

        regime_stability = None
        if regime_data:
            regime_stability = regime_data.get("stability", regime_data.get("regime_stability"))

        portfolio_risk = None
        if portfolio_data:
            portfolio_risk = portfolio_data.get("risk_level", portfolio_data.get("overall_risk_level"))

        return InstabilityReport(
            composite_score=round(composite, 4),
            severity=severity,
            factors=factors,
            alert_count=len(alerts),
            critical_factors=critical,
            regime_stability=regime_stability,
            portfolio_risk_level=portfolio_risk,
            feature_stability_status=self._get_feature_stability_label(db),
            recent_regime_transitions=self._count_recent_transitions(regime_data),
        )

    def _load_trades(self, db) -> list[dict]:
        if db is None:
            return []
        try:
            rows = db.fetch_all(
                "SELECT outcome, pnl, confidence, market_regime, created_at FROM trade_memory ORDER BY created_at DESC LIMIT 200"
            )
            columns = ["outcome", "pnl", "confidence", "market_regime", "created_at"]
            return [dict(zip(columns, row)) for row in rows]
        except Exception:
            return []

    def _load_regime_data(self, db) -> dict:
        if db is None:
            return {}
        try:
            row = db.fetch_one("SELECT * FROM market_regime_history ORDER BY created_at DESC LIMIT 1")
            if row:
                cols = ["id", "regime", "confidence", "risk_level", "stability", "atr_pct",
                         "bb_width", "vix_level", "ema_diff_pct", "adx", "macd_histogram",
                         "volume_ratio", "signal_breakdown", "suggested_behavior", "created_at"]
                return dict(zip(cols, row))
        except Exception:
            pass
        return {}

    def _load_portfolio_data(self, db) -> dict:
        if db is None:
            return {}
        try:
            row = db.fetch_one("SELECT * FROM portfolio_insights ORDER BY created_at DESC LIMIT 1")
            if row:
                cols = ["id", "snapshot_time", "total_value", "num_positions", "num_sectors",
                         "top_holding_pct", "top_3_holdings_pct", "herfindahl_index",
                         "sector_exposures", "capital_concentrations", "correlation_pairs",
                         "correlation_clusters", "portfolio_daily_vol_pct",
                         "portfolio_annualized_vol_pct", "weighted_vol_pct", "net_exposure_pct",
                         "directional_bias", "risk_score", "overall_risk_level", "alerts",
                         "regime_label", "created_at"]
                return dict(zip(cols, row))
        except Exception:
            pass
        return {}

    def _assess_regime_factors(self, regime_data: dict) -> list[InstabilityFactor]:
        factors = []
        if not regime_data:
            factors.append(InstabilityFactor(
                source="regime", factor="regime_data_available",
                value=0, threshold=1, is_alert=True,
                description="Regime data not available for instability assessment",
                severity="medium",
            ))
            return factors

        stability = regime_data.get("stability", "unknown")
        is_unstable = stability == "unstable"
        factors.append(InstabilityFactor(
            source="regime", factor="regime_stability",
            value=1.0 if is_unstable else 0.5 if stability == "moderate" else 0.0,
            threshold=0.5, is_alert=is_unstable,
            description=f"Regime stability: {stability}",
            severity="high" if is_unstable else "medium" if stability == "moderate" else "low",
        ))

        risk = regime_data.get("risk_level", "medium")
        is_high_risk = risk == "high"
        factors.append(InstabilityFactor(
            source="regime", factor="regime_risk_level",
            value=1.0 if is_high_risk else 0.5 if risk == "medium" else 0.0,
            threshold=0.5, is_alert=is_high_risk,
            description=f"Regime risk level: {risk}",
            severity="high" if is_high_risk else "low",
        ))

        vol = regime_data.get("atr_pct", 0) or 0
        high_vol = vol > 0.03
        factors.append(InstabilityFactor(
            source="regime", factor="volatility_level",
            value=vol, threshold=0.03, is_alert=high_vol,
            description=f"ATR percentage: {vol:.2%}",
            severity="medium" if high_vol else "low",
        ))

        return factors

    def _assess_portfolio_factors(self, portfolio_data: dict) -> list[InstabilityFactor]:
        factors = []
        if not portfolio_data:
            return factors

        risk_score = portfolio_data.get("risk_score", 0) or 0
        is_high_risk = risk_score > 0.7
        factors.append(InstabilityFactor(
            source="portfolio", factor="portfolio_risk_score",
            value=risk_score, threshold=0.7, is_alert=is_high_risk,
            description=f"Portfolio risk score: {risk_score:.2f}",
            severity="high" if is_high_risk else "medium" if risk_score > 0.4 else "low",
        ))

        num_positions = portfolio_data.get("num_positions", 0) or 0
        herfindahl = portfolio_data.get("herfindahl_index", 0) or 0
        is_concentrated = herfindahl > 0.3
        factors.append(InstabilityFactor(
            source="portfolio", factor="concentration_risk",
            value=herfindahl, threshold=0.3, is_alert=is_concentrated,
            description=f"Portfolio concentration (Herfindahl): {herfindahl:.2f} across {num_positions} positions",
            severity="high" if is_concentrated else "low",
        ))

        top_hold = portfolio_data.get("top_holding_pct", 0) or 0
        is_overweight = top_hold > 0.25
        factors.append(InstabilityFactor(
            source="portfolio", factor="top_holding_concentration",
            value=top_hold, threshold=0.25, is_alert=is_overweight,
            description=f"Top holding: {top_hold:.1%} of portfolio",
            severity="medium" if is_overweight else "low",
        ))

        return factors

    def _assess_trade_factors(self, trades: list[dict]) -> list[InstabilityFactor]:
        factors = []
        if not trades:
            return factors

        total = len(trades)
        recent = trades[:min(50, total)]
        failures = sum(1 for t in recent if self._is_failure(t))
        failure_rate = failures / len(recent) if recent else 0
        high_failure = failure_rate > 0.4
        factors.append(InstabilityFactor(
            source="trade", factor="recent_failure_rate",
            value=failure_rate, threshold=0.4, is_alert=high_failure,
            description=f"Recent failure rate: {failure_rate:.0%} ({failures}/{len(recent)})",
            severity="critical" if failure_rate > 0.6 else "high" if high_failure else "low",
        ))

        confidences = [float(t.get("confidence", 0) or 0) for t in recent if t.get("confidence")]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0
        low_confidence = avg_conf < 0.4
        factors.append(InstabilityFactor(
            source="trade", factor="average_confidence",
            value=avg_conf, threshold=0.4, is_alert=low_confidence,
            description=f"Average prediction confidence: {avg_conf:.2f}",
            severity="medium" if low_confidence else "low",
        ))

        return factors

    def _assess_feature_drift(self, db) -> list[InstabilityFactor]:
        factors = []
        if db is None:
            return factors
        try:
            row = db.fetch_one(
                "SELECT drift_score, feature_count FROM feature_drift_log ORDER BY created_at DESC LIMIT 1"
            )
            if row:
                drift_score = row[0] or 0
                high_drift = drift_score > 0.3
                factors.append(InstabilityFactor(
                    source="explainability", factor="feature_drift",
                    value=drift_score, threshold=0.3, is_alert=high_drift,
                    description=f"Feature drift score: {drift_score:.2f}",
                    severity="high" if drift_score > 0.5 else "medium" if high_drift else "low",
                ))
        except Exception:
            pass
        return factors

    def _compute_composite(self, factors: list[InstabilityFactor]) -> float:
        if not factors:
            return 0.0
        weighted = 0.0
        total_weight = 0.0
        severity_weights = {"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.2}
        for f in factors:
            if f.is_alert:
                w = severity_weights.get(f.severity, 0.3)
                weighted += min(f.value, 1.0) * w
                total_weight += w
        return weighted / total_weight if total_weight > 0 else 0.0

    def _count_recent_transitions(self, regime_data: dict) -> int:
        return 0

    def _get_feature_stability_label(self, db) -> Optional[str]:
        if db is None:
            return None
        try:
            row = db.fetch_one(
                "SELECT drift_score FROM feature_drift_log ORDER BY created_at DESC LIMIT 1"
            )
            if row:
                score = row[0] or 0
                if score > 0.5:
                    return "unstable"
                elif score > 0.3:
                    return "degrading"
                elif score > 0.1:
                    return "moderate"
                return "stable"
        except Exception:
            pass
        return None

    def _is_failure(self, trade: dict) -> bool:
        outcome = trade.get("outcome", "")
        if isinstance(outcome, str):
            lower = outcome.lower()
            return any(kw in lower for kw in ("loss", "fail", "stop", "sl"))
        pnl = float(trade.get("pnl", 0) or 0)
        return pnl < 0
