from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field
from loguru import logger


class RecurringPattern(BaseModel):
    category: str = Field(description="Pattern category identifier")
    label: str = Field(description="Human-readable pattern name")
    description: str = Field(description="Detailed pattern description")
    count: int = Field(description="Number of occurrences in window")
    total_trades: int = Field(description="Total trades analyzed")
    frequency: float = Field(description="Frequency as ratio of total trades")
    trend_direction: str = Field(description="increasing/decreasing/stable")
    severity: str = Field(description="low/medium/high/critical")
    avg_pnl_impact: float = Field(default=0.0, description="Average PnL impact per occurrence")
    sample_trade_ids: list[str] = Field(default_factory=list)
    first_observed: Optional[str] = Field(default=None)
    last_observed: Optional[str] = Field(default=None)


class RecurringPatternReport(BaseModel):
    patterns: list[RecurringPattern] = Field(default_factory=list)
    total_patterns_found: int = Field(default=0)
    total_trades_analyzed: int = Field(default=0)
    window_days: int = Field(default=30)
    dominant_category: Optional[str] = Field(default=None)
    critical_patterns: list[RecurringPattern] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RecurringPatternDetector:
    def __init__(self, analytics_db=None):
        self._analytics_db = analytics_db
        self._failure_analyzer = None
        self._min_trades_for_pattern: int = 5
        self._pattern_frequency_threshold: float = 0.15

    def _get_analytics_db(self):
        if self._analytics_db is not None:
            return self._analytics_db
        try:
            from core.analytics_db import AnalyticsDB
            self._analytics_db = AnalyticsDB()
            return self._analytics_db
        except Exception:
            return None

    def configure(self, min_trades: int = 5, frequency_threshold: float = 0.15):
        self._min_trades_for_pattern = min_trades
        self._pattern_frequency_threshold = frequency_threshold

    def detect(self, trades: Optional[list[dict]] = None, window_days: int = 30) -> RecurringPatternReport:
        if trades is None:
            trades = self._load_trades_from_db(window_days)

        if not trades:
            return RecurringPatternReport(window_days=window_days)

        total = len(trades)
        cut_date = datetime.now(timezone.utc) - timedelta(days=window_days)

        window_trades = [
            t for t in trades
            if self._parse_timestamp(t) >= cut_date
        ]
        if not window_trades:
            window_trades = trades[-min(len(trades), 100):]

        failures = [t for t in window_trades if self._is_failure(t)]
        if not failures:
            return RecurringPatternReport(
                total_trades_analyzed=len(window_trades),
                window_days=window_days,
            )

        patterns_by_category = self._classify_failures(failures, window_trades)

        older_trades = [t for t in trades if self._parse_timestamp(t) < cut_date]
        if older_trades:
            older_failures = [t for t in older_trades if self._is_failure(t)]
            self._compute_trends(patterns_by_category, older_failures, older_trades)

        patterns = []
        for cat, data in patterns_by_category.items():
            if data["count"] < self._min_trades_for_pattern:
                continue
            freq = data["count"] / len(window_trades) if window_trades else 0
            if freq < self._pattern_frequency_threshold:
                continue
            severity = self._compute_severity(freq, data["avg_pnl_impact"])
            patterns.append(RecurringPattern(
                category=cat,
                label=self._category_label(cat),
                description=self._category_description(cat),
                count=data["count"],
                total_trades=len(window_trades),
                frequency=round(freq, 4),
                trend_direction=data.get("trend", "stable"),
                severity=severity,
                avg_pnl_impact=round(data["avg_pnl_impact"], 2),
                sample_trade_ids=data.get("sample_ids", [])[:5],
                first_observed=data.get("first_observed"),
                last_observed=data.get("last_observed"),
            ))

        patterns.sort(key=lambda p: (["critical", "high", "medium", "low"].index(p.severity), -p.frequency))
        critical = [p for p in patterns if p.severity in ("critical", "high")]
        dominant = max(patterns, key=lambda p: p.frequency).category if patterns else None

        return RecurringPatternReport(
            patterns=patterns,
            total_patterns_found=len(patterns),
            total_trades_analyzed=len(window_trades),
            window_days=window_days,
            dominant_category=dominant,
            critical_patterns=critical,
        )

    def _load_trades_from_db(self, window_days: int) -> list[dict]:
        db = self._get_analytics_db()
        if db is None:
            return []
        try:
            rows = db.fetch_all(
                "SELECT * FROM trade_memory ORDER BY created_at DESC LIMIT 500"
            )
            columns = ["trade_id", "symbol", "timestamp", "market_regime",
                        "feature_snapshot", "prediction", "confidence", "reasoning",
                        "outcome", "portfolio_state", "reflection_notes", "schema_version", "created_at"]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to load trades from analytics DB: {e}")
            return []

    def _parse_timestamp(self, trade: dict) -> datetime:
        ts = trade.get("timestamp") or trade.get("created_at") or ""
        if isinstance(ts, datetime):
            return ts
        try:
            return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

    def _is_failure(self, trade: dict) -> bool:
        outcome = trade.get("outcome", "")
        if isinstance(outcome, str):
            lower = outcome.lower()
            return any(kw in lower for kw in ("loss", "fail", "stop", "sl"))
        return False

    def _classify_failures(self, failures: list[dict], all_trades: list[dict]) -> dict:
        patterns: dict[str, dict] = {
            "regime_mismatch": {"count": 0, "total_pnl": 0.0, "sample_ids": [], "first_observed": None, "last_observed": None},
            "volatility_expansion": {"count": 0, "total_pnl": 0.0, "sample_ids": [], "first_observed": None, "last_observed": None},
            "weak_momentum": {"count": 0, "total_pnl": 0.0, "sample_ids": [], "first_observed": None, "last_observed": None},
            "poor_confirmations": {"count": 0, "total_pnl": 0.0, "sample_ids": [], "first_observed": None, "last_observed": None},
            "stop_loss_hunting": {"count": 0, "total_pnl": 0.0, "sample_ids": [], "first_observed": None, "last_observed": None},
            "regime_instability": {"count": 0, "total_pnl": 0.0, "sample_ids": [], "first_observed": None, "last_observed": None},
            "feature_alignment": {"count": 0, "total_pnl": 0.0, "sample_ids": [], "first_observed": None, "last_observed": None},
            "earnings_event": {"count": 0, "total_pnl": 0.0, "sample_ids": [], "first_observed": None, "last_observed": None},
            "sector_rotation": {"count": 0, "total_pnl": 0.0, "sample_ids": [], "first_observed": None, "last_observed": None},
        }

        for t in failures:
            reasoning = (t.get("reasoning") or "").lower()
            regime = (t.get("market_regime") or "").lower()
            tid = str(t.get("trade_id", ""))
            ts = self._parse_timestamp(t).isoformat() if self._parse_timestamp(t) else None
            pnl = float(t.get("pnl", 0) or 0)

            matched = False
            for cat, keywords in self._get_pattern_keywords().items():
                matched_any = any(kw in reasoning for kw in keywords)
                if not matched_any and regime:
                    matched_any = self._match_regime_to_category(regime, cat)
                if matched_any:
                    patterns[cat]["count"] += 1
                    patterns[cat]["total_pnl"] += pnl
                    if len(patterns[cat]["sample_ids"]) < 10:
                        patterns[cat]["sample_ids"].append(tid)
                    if ts:
                        if patterns[cat]["first_observed"] is None or ts < patterns[cat]["first_observed"]:
                            patterns[cat]["first_observed"] = ts
                        if patterns[cat]["last_observed"] is None or ts > patterns[cat]["last_observed"]:
                            patterns[cat]["last_observed"] = ts
                    matched = True

            if not matched:
                patterns["regime_mismatch"]["count"] += 1
                patterns["regime_mismatch"]["total_pnl"] += pnl

        for cat in patterns:
            if patterns[cat]["count"] > 0:
                patterns[cat]["avg_pnl_impact"] = patterns[cat]["total_pnl"] / patterns[cat]["count"]

        return patterns

    def _compute_trends(self, patterns: dict, older_failures: list[dict], older_trades: list[dict]):
        older_patterns = self._classify_failures(older_failures, older_trades)
        for cat in patterns:
            prev_count = older_patterns.get(cat, {}).get("count", 0)
            curr_count = patterns[cat]["count"]
            if prev_count == 0 and curr_count > 0:
                patterns[cat]["trend"] = "new"
            elif prev_count > 0 and curr_count > prev_count:
                patterns[cat]["trend"] = "increasing"
            elif prev_count > 0 and curr_count < prev_count:
                patterns[cat]["trend"] = "decreasing"
            else:
                patterns[cat]["trend"] = "stable"

    def _compute_severity(self, frequency: float, avg_pnl: float) -> str:
        if frequency >= 0.5 or avg_pnl <= -500:
            return "critical"
        if frequency >= 0.3 or avg_pnl <= -200:
            return "high"
        if frequency >= 0.15 or avg_pnl <= -100:
            return "medium"
        return "low"

    def _get_pattern_keywords(self) -> dict[str, list[str]]:
        return {
            "regime_mismatch": ["regime mismatch", "mismatch", "direction conflict", "wrong direction",
                                "unfavorable regime", "bearish environment", "bullish against trend"],
            "volatility_expansion": ["volatility expansion", "vol spike", "high volatility", "atr expansion",
                                     "volatile", "spike", "sudden move", "gap"],
            "weak_momentum": ["weak momentum", "low adx", "weak trend", "momentum divergence",
                              "declining volume", "no momentum", "fading"],
            "poor_confirmations": ["weak confirmation", "low confidence", "thin margin", "conflicting features",
                                   "mixed signals", "low conviction", "uncertain"],
            "stop_loss_hunting": ["stop loss", "sl trigger", "stop hunted", "stop run",
                                  "liquidity grab", "false breakout"],
            "regime_instability": ["regime instability", "unstable", "transitioning", "regime flip",
                                   "regime change", "flipping"],
            "feature_alignment": ["feature alignment", "inappropriate feature", "missing feature",
                                  "wrong features", "feature drift"],
            "earnings_event": ["earnings", "result", "dividend", "corporate action", "buyback",
                               "bonus", "split"],
            "sector_rotation": ["sector rotation", "sector shift", "sector weakness", "sector strength",
                                "rotating out", "sector selloff"],
        }

    def _match_regime_to_category(self, regime: str, category: str) -> bool:
        regime_to_cat = {
            "bear_trend": "regime_mismatch",
            "high_volatility": "volatility_expansion",
            "event_driven": "earnings_event",
            "unstable": "regime_instability",
        }
        return regime_to_cat.get(regime) == category

    def _category_label(self, category: str) -> str:
        labels = {
            "regime_mismatch": "Regime Mismatch",
            "volatility_expansion": "Volatility Expansion",
            "weak_momentum": "Weak Momentum",
            "poor_confirmations": "Poor Confirmations",
            "stop_loss_hunting": "Stop Loss Hunting",
            "regime_instability": "Regime Instability",
            "feature_alignment": "Feature Alignment",
            "earnings_event": "Earnings Event",
            "sector_rotation": "Sector Rotation",
        }
        return labels.get(category, category.replace("_", " ").title())

    def _category_description(self, category: str) -> str:
        descriptions = {
            "regime_mismatch": "Trades taken against prevailing market regime direction",
            "volatility_expansion": "Trades disrupted by sudden volatility expansion",
            "weak_momentum": "Trades entered during weak or declining momentum",
            "poor_confirmations": "Trades with weak feature confirmations or conflicting signals",
            "stop_loss_hunting": "Trades where stop-loss was triggered by price liquidity sweeps",
            "regime_instability": "Trades during unstable or transitioning market regimes",
            "feature_alignment": "Trades where ML features were poorly aligned with regime",
            "earnings_event": "Trades affected by earnings or corporate announcements",
            "sector_rotation": "Trades impacted by sector rotation away from position",
        }
        return descriptions.get(category, "")
