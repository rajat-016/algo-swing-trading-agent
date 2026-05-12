from __future__ import annotations
import time
from typing import Any, Optional
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.orm import Session

from core.logging import logger
from core.config import get_settings
from core.analytics_db import AnalyticsDB
from intelligence.portfolio_analysis.correlation.models import (
    RollingCorrelationResult,
    SectorClusteringReport,
    InstabilityReport,
    DiversificationScore,
)
from intelligence.portfolio_analysis.correlation.rolling import RollingCorrelationAnalyzer
from intelligence.portfolio_analysis.correlation.clustering import SectorClusteringEngine
from intelligence.portfolio_analysis.correlation.instability import InstabilityAnalyzer
from intelligence.portfolio_analysis.correlation.diversification import DiversificationScorer


CORRELATION_ANALYSIS_SCHEMA = """
CREATE TABLE IF NOT EXISTS correlation_analysis (
    id INTEGER PRIMARY KEY,
    snapshot_time TIMESTAMP,
    rolling_window_size INTEGER,
    rolling_step INTEGER,
    rolling_trend VARCHAR,
    rolling_stability DOUBLE,
    current_avg_corr DOUBLE,
    num_symbols INTEGER,
    sector_clusters TEXT,
    inter_sector_matrix TEXT,
    instability_alerts TEXT,
    correlation_regime VARCHAR,
    diversification_score DOUBLE,
    diversification_breakdown TEXT,
    regime_label VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class CorrelationAnalysisService:
    def __init__(self, config=None, db: Optional[AnalyticsDB] = None):
        self._config = config
        self._db = db
        self._rolling_analyzer = RollingCorrelationAnalyzer(
            window_size_days=60, step_days=10, high_threshold=0.80,
        )
        self._clustering_engine = SectorClusteringEngine(high_threshold=0.80)
        self._instability_analyzer = InstabilityAnalyzer(
            high_threshold=0.80, change_threshold=0.15, lookback_windows=3,
        )
        self._diversification_scorer = DiversificationScorer(
            target_effective_n=5.0, target_sector_count=3,
        )

    def analyze(self, db: Session,
                holdings: Optional[list[dict[str, Any]]] = None,
                price_data: Optional[pd.DataFrame] = None,
                persist: bool = True) -> dict[str, Any]:
        start = time.monotonic()
        result = {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

        if holdings is None:
            holdings = self._load_holdings(db)

        result["num_positions"] = len(holdings)

        if not holdings or len(holdings) < 2:
            result["status"] = "insufficient_positions" if holdings and len(holdings) == 1 else "no_positions"
            result["rolling"] = self._rolling_analyzer.analyze().__dict__
            result["sector_clustering"] = self._clustering_engine.analyze(holdings or []).__dict__
            result["instability"] = self._instability_analyzer.analyze().__dict__
            result["diversification"] = self._diversification_scorer.score(holdings or []).__dict__
            result["latency_seconds"] = round(time.monotonic() - start, 3)
            return result

        if price_data is None:
            price_data = self._load_price_data(db, holdings)

        try:
            rolling_result = self._rolling_analyzer.analyze(price_data=price_data)
            result["rolling"] = rolling_result.__dict__
        except Exception as e:
            logger.error(f"Rolling correlation failed: {e}")
            result["rolling"] = {"error": str(e)}
            rolling_result = None

        try:
            sector_result = self._clustering_engine.analyze(
                holdings=holdings, price_data=price_data,
            )
            result["sector_clustering"] = sector_result.__dict__
        except Exception as e:
            logger.error(f"Sector clustering failed: {e}")
            result["sector_clustering"] = {"error": str(e)}
            sector_result = None

        try:
            instability_result = self._instability_analyzer.analyze(
                price_data=price_data, holdings=holdings,
                rolling_result=rolling_result,
            )
            result["instability"] = instability_result.__dict__
        except Exception as e:
            logger.error(f"Instability analysis failed: {e}")
            result["instability"] = {"error": str(e)}
            instability_result = None

        try:
            diversification_result = self._diversification_scorer.score(
                holdings=holdings, price_data=price_data,
                sector_clustering_report=sector_result,
            )
            result["diversification"] = diversification_result.__dict__
        except Exception as e:
            logger.error(f"Diversification scoring failed: {e}")
            result["diversification"] = {"error": str(e)}

        regime_label = self._get_regime_context()
        result["regime_label"] = regime_label

        result["latency_seconds"] = round(time.monotonic() - start, 3)

        if persist and self._db:
            try:
                self._persist_snapshot(result)
            except Exception as e:
                logger.warning(f"Failed to persist correlation analysis: {e}")

        return result

    def _load_holdings(self, db: Session) -> list[dict[str, Any]]:
        try:
            from models.stock import Stock, StockStatus
            stocks = db.query(Stock).filter(
                Stock.status == StockStatus.ENTERED
            ).all()
            return [s.to_dict() for s in stocks]
        except Exception as e:
            logger.warning(f"Failed to load holdings: {e}")
            return []

    def _load_price_data(self, db: Session,
                          holdings: list[dict[str, Any]]) -> pd.DataFrame:
        if not holdings or self._db is None:
            return pd.DataFrame()
        try:
            symbols = [h.get("symbol") for h in holdings if h.get("symbol")]
            if not symbols:
                return pd.DataFrame()
            names = []
            for s in symbols:
                clean = s.upper().replace(".NS", "")
                names.append(clean + ".NS" if not clean.endswith(".NS") else clean)
            placeholders = ", ".join(f"'{s}'" for s in names)
            query = f"""
                SELECT datetime, symbol, close
                FROM ohlcv
                WHERE symbol IN ({placeholders})
                ORDER BY datetime
            """
            df = self._db.query_df(query)
            if df.empty:
                return pd.DataFrame()
            pivot = df.pivot_table(index="datetime", columns="symbol", values="close")
            pivot = pivot.ffill().bfill().dropna()
            return pivot
        except Exception as e:
            logger.warning(f"Failed to load price data: {e}")
            return pd.DataFrame()

    def _get_regime_context(self) -> Optional[str]:
        try:
            from intelligence.market_regime.service import RegimeService
            from intelligence.market_regime.config import RegimeConfig
            settings = get_settings()
            rc = RegimeConfig(
                enabled=settings.regime_engine_enabled,
                ema_short=settings.regime_ema_short,
                ema_long=settings.regime_ema_long,
            )
            rs = RegimeService(config=rc, db=self._db)
            if self._db:
                rs.initialize(self._db)
            current = rs.get_current_regime()
            if current:
                return str(current.regime.value) if hasattr(current.regime, "value") else str(current.regime)
        except Exception as e:
            logger.warning(f"Regime context unavailable: {e}")
        return None

    def _persist_snapshot(self, analysis: dict[str, Any]) -> bool:
        if self._db is None:
            return False
        try:
            self._db.ensure_table(CORRELATION_ANALYSIS_SCHEMA)
            rolling = analysis.get("rolling", {})
            cluster = analysis.get("sector_clustering", {})
            instability = analysis.get("instability", {})
            diversification = analysis.get("diversification", {})

            import json
            self._db.execute(
                """
                INSERT INTO correlation_analysis
                (snapshot_time, rolling_window_size, rolling_step,
                 rolling_trend, rolling_stability, current_avg_corr,
                 num_symbols, sector_clusters, inter_sector_matrix,
                 instability_alerts, correlation_regime,
                 diversification_score, diversification_breakdown,
                 regime_label)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    datetime.now(timezone.utc),
                    rolling.get("window_size_days", 0),
                    rolling.get("step_days", 0),
                    rolling.get("trend", "stable"),
                    rolling.get("stability_score", 1.0),
                    rolling.get("current_avg_correlation", 0.0),
                    analysis.get("num_positions", 0),
                    json.dumps([c.__dict__ for c in cluster.get("clusters", [])]
                               if cluster.get("clusters") and hasattr(cluster["clusters"][0], "__dict__")
                               else json.dumps(cluster.get("clusters", []))),
                    json.dumps(cluster.get("inter_sector_matrix", [])),
                    json.dumps([a.__dict__ for a in instability.get("alerts", [])]
                               if instability.get("alerts") and hasattr(instability["alerts"][0], "__dict__")
                               else json.dumps(instability.get("alerts", []))),
                    instability.get("correlation_regime", "stable"),
                    diversification.get("overall_score", 0.0),
                    json.dumps([b.__dict__ for b in diversification.get("breakdown", [])]
                               if diversification.get("breakdown") and hasattr(diversification["breakdown"][0], "__dict__")
                               else json.dumps(diversification.get("breakdown", []))),
                    analysis.get("regime_label", "unknown"),
                ],
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to persist correlation snapshot: {e}")
            return False

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        if self._db is None:
            return []
        try:
            rows = self._db.fetch_all(
                "SELECT * FROM correlation_analysis ORDER BY snapshot_time DESC LIMIT ?",
                [limit],
            )
            return [self._row_to_dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"Failed to load correlation history: {e}")
            return []

    def get_latest(self) -> Optional[dict[str, Any]]:
        rows = self.get_history(limit=1)
        return rows[0] if rows else None

    def _row_to_dict(self, row) -> dict[str, Any]:
        import json
        return {
            "id": row[0],
            "snapshot_time": str(row[1]) if row[1] else None,
            "rolling_window_size": row[2],
            "rolling_step": row[3],
            "rolling_trend": row[4],
            "rolling_stability": row[5],
            "current_avg_corr": row[6],
            "num_symbols": row[7],
            "sector_clusters": json.loads(row[8]) if row[8] else [],
            "inter_sector_matrix": json.loads(row[9]) if row[9] else [],
            "instability_alerts": json.loads(row[10]) if row[10] else [],
            "correlation_regime": row[11],
            "diversification_score": row[12],
            "diversification_breakdown": json.loads(row[13]) if row[13] else [],
            "regime_label": row[14],
        }
