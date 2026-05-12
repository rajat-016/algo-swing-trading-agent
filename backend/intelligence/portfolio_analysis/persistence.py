from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Optional
import json

from core.logging import logger


PORTFOLIO_INSIGHTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS portfolio_insights (
    id INTEGER PRIMARY KEY,
    snapshot_time TIMESTAMP,
    total_value DOUBLE,
    num_positions INTEGER,
    num_sectors INTEGER,
    top_holding_pct DOUBLE,
    top_3_holdings_pct DOUBLE,
    herfindahl_index DOUBLE,
    sector_exposures TEXT,
    capital_concentrations TEXT,
    correlation_pairs TEXT,
    correlation_clusters TEXT,
    portfolio_daily_vol_pct DOUBLE,
    portfolio_annualized_vol_pct DOUBLE,
    weighted_vol_pct DOUBLE,
    net_exposure_pct DOUBLE,
    directional_bias VARCHAR,
    risk_score DOUBLE,
    overall_risk_level VARCHAR,
    alerts TEXT,
    regime_label VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class PortfolioPersistence:
    def __init__(self, db=None):
        self._db = db

    def save_snapshot(self, analysis: dict[str, Any]) -> bool:
        if self._db is None:
            return False
        try:
            self._db.ensure_table(PORTFOLIO_INSIGHTS_SCHEMA)
            exposures = analysis.get("exposure", {})
            correlations = analysis.get("correlation", {})
            volatilities = analysis.get("volatility", {})
            bias = analysis.get("directional_bias", {})
            risks = analysis.get("risk_insights", {})

            self._db.execute(
                """
                INSERT INTO portfolio_insights
                (snapshot_time, total_value, num_positions, num_sectors,
                 top_holding_pct, top_3_holdings_pct, herfindahl_index,
                 sector_exposures, capital_concentrations,
                 correlation_pairs, correlation_clusters,
                 portfolio_daily_vol_pct, portfolio_annualized_vol_pct, weighted_vol_pct,
                 net_exposure_pct, directional_bias,
                 risk_score, overall_risk_level, alerts,
                 regime_label)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    datetime.now(timezone.utc),
                    exposures.get("total_portfolio_value", 0.0),
                    len(exposures.get("capital_concentrations", [])),
                    exposures.get("num_sectors", 0),
                    exposures.get("top_holding_pct", 0.0),
                    exposures.get("top_3_holdings_pct", 0.0),
                    exposures.get("herfindahl_index", 0.0),
                    self._serialize(exposures.get("sector_exposures", [])),
                    self._serialize(exposures.get("capital_concentrations", [])),
                    self._serialize(correlations.get("pairs", [])),
                    self._serialize(correlations.get("clusters", [])),
                    volatilities.get("portfolio_daily_vol_pct", 0.0),
                    volatilities.get("portfolio_annualized_vol_pct", 0.0),
                    volatilities.get("weighted_vol_pct", 0.0),
                    bias.get("net_exposure_pct", 0.0),
                    bias.get("bias", "neutral"),
                    risks.get("risk_score", 0.0),
                    risks.get("overall_risk_level", "low"),
                    self._serialize(risks.get("alerts", [])),
                    analysis.get("regime_label", "unknown"),
                ],
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to persist portfolio snapshot: {e}")
            return False

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        if self._db is None:
            return []
        try:
            rows = self._db.fetch_all(
                "SELECT * FROM portfolio_insights ORDER BY snapshot_time DESC LIMIT ?",
                [limit],
            )
            return [self._row_to_dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"Failed to load portfolio history: {e}")
            return []

    def get_latest(self) -> Optional[dict[str, Any]]:
        rows = self.get_history(limit=1)
        return rows[0] if rows else None

    def clear(self) -> bool:
        if self._db is None:
            return False
        try:
            self._db.execute("DELETE FROM portfolio_insights")
            return True
        except Exception as e:
            logger.warning(f"Failed to clear portfolio insights: {e}")
            return False

    def _serialize(self, items: Any) -> str:
        if not items:
            return json.dumps([])
        try:
            if isinstance(items, list) and items and hasattr(items[0], "__dict__"):
                return json.dumps([i.__dict__ for i in items])
            return json.dumps(items)
        except (TypeError, ValueError):
            return json.dumps([])

    def _row_to_dict(self, row) -> dict[str, Any]:
        return {
            "id": row[0],
            "snapshot_time": str(row[1]) if row[1] else None,
            "total_value": row[2],
            "num_positions": row[3],
            "num_sectors": row[4],
            "top_holding_pct": row[5],
            "top_3_holdings_pct": row[6],
            "herfindahl_index": row[7],
            "sector_exposures": json.loads(row[8]) if row[8] else [],
            "capital_concentrations": json.loads(row[9]) if row[9] else [],
            "correlation_pairs": json.loads(row[10]) if row[10] else [],
            "correlation_clusters": json.loads(row[11]) if row[11] else [],
            "portfolio_daily_vol_pct": row[12],
            "portfolio_annualized_vol_pct": row[13],
            "weighted_vol_pct": row[14],
            "net_exposure_pct": row[15],
            "directional_bias": row[16],
            "risk_score": row[17],
            "overall_risk_level": row[18],
            "alerts": json.loads(row[19]) if row[19] else [],
            "regime_label": row[20],
        }
