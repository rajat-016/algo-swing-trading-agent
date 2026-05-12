from __future__ import annotations
import time
from typing import Any, Optional
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.orm import Session

from core.logging import logger
from core.config import get_settings
from core.analytics_db import AnalyticsDB
from intelligence.portfolio_analysis.config import PortfolioConfig
from intelligence.portfolio_analysis.exposure_analyzer import ExposureAnalyzer
from intelligence.portfolio_analysis.correlation_analyzer import CorrelationAnalyzer
from intelligence.portfolio_analysis.volatility_analyzer import VolatilityAnalyzer
from intelligence.portfolio_analysis.directional_bias import DirectionalBiasAnalyzer
from intelligence.portfolio_analysis.risk_insights import RiskInsightsGenerator
from intelligence.portfolio_analysis.persistence import PortfolioPersistence


class PortfolioIntelligenceService:
    def __init__(self, config: Optional[PortfolioConfig] = None, db: Optional[AnalyticsDB] = None):
        self._config = config or PortfolioConfig()
        self._db = db
        self._exposure = ExposureAnalyzer(
            max_sector_exposure_pct=self._config.max_sector_exposure_pct,
            max_single_position_pct=self._config.max_single_position_pct,
        )
        self._correlation = CorrelationAnalyzer(
            high_threshold=self._config.correlation_high_threshold,
            medium_threshold=self._config.correlation_medium_threshold,
            min_trades=self._config.min_trades_for_correlation,
        )
        self._volatility = VolatilityAnalyzer(
            high_threshold_pct=self._config.volatility_high_threshold_pct,
            low_threshold_pct=self._config.volatility_low_threshold_pct,
        )
        self._directional = DirectionalBiasAnalyzer()
        self._risk = RiskInsightsGenerator(
            max_sector_pct=self._config.max_sector_exposure_pct,
            max_position_pct=self._config.max_single_position_pct,
            correlation_high=self._config.correlation_high_threshold,
        )
        self._persistence = PortfolioPersistence(db=self._db)
        self._regime_service = None

    def _get_regime_context(self) -> Optional[str]:
        if self._regime_service is None:
            try:
                from intelligence.market_regime.service import RegimeService
                from intelligence.market_regime.config import RegimeConfig
                settings = get_settings()
                rc = RegimeConfig(
                    enabled=settings.regime_engine_enabled,
                    ema_short=settings.regime_ema_short,
                    ema_long=settings.regime_ema_long,
                    sideways_threshold_pct=settings.regime_sideways_threshold_pct,
                    adx_trend_threshold=settings.regime_adx_trend_threshold,
                    high_vol_atr_pct=settings.regime_high_vol_atr_pct,
                    low_vol_atr_pct=settings.regime_low_vol_atr_pct,
                )
                self._regime_service = RegimeService(config=rc, db=self._db)
                if self._db:
                    self._regime_service.initialize(self._db)
            except Exception as e:
                logger.warning(f"Regime service not available for portfolio: {e}")
                return None

        try:
            current = self._regime_service.get_current_regime()
            if current:
                return str(current.regime.value) if hasattr(current.regime, "value") else str(current.regime)
        except Exception as e:
            logger.warning(f"Could not get current regime: {e}")
        return None

    def analyze(self, db: Session,
                holdings: Optional[list[dict[str, Any]]] = None,
                price_data: Optional[pd.DataFrame] = None,
                total_capital: Optional[float] = None,
                persist: bool = True) -> dict[str, Any]:
        start = time.monotonic()
        result = {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

        if holdings is None:
            holdings = self._load_holdings(db)

        result["num_positions"] = len(holdings)

        if not holdings:
            result["status"] = "no_positions"
            result["exposure"] = self._exposure.analyze([], total_capital).__dict__
            result["correlation"] = self._correlation.analyze(holdings=[]).__dict__
            result["volatility"] = self._volatility.analyze(holdings=[]).__dict__
            result["directional_bias"] = self._directional.analyze([], total_capital).__dict__
            result["risk_insights"] = self._risk.generate(
                self._exposure.analyze([], total_capital),
                self._correlation.analyze(holdings=[]),
                self._volatility.analyze(holdings=[]),
                self._directional.analyze([], total_capital),
                total_capital,
            ).__dict__
            result["latency_seconds"] = round(time.monotonic() - start, 3)
            return result
        try:
            exposure_report = self._exposure.analyze(holdings, total_capital)
            result["exposure"] = {
                "total_portfolio_value": exposure_report.total_portfolio_value,
                "sector_exposures": [s.__dict__ for s in exposure_report.sector_exposures],
                "capital_concentrations": [c.__dict__ for c in exposure_report.capital_concentrations],
                "top_holding_pct": exposure_report.top_holding_pct,
                "top_3_holdings_pct": exposure_report.top_3_holdings_pct,
                "num_sectors": exposure_report.num_sectors,
                "herfindahl_index": exposure_report.herfindahl_index,
            }
        except Exception as e:
            logger.error(f"Exposure analysis failed: {e}")
            result["exposure"] = {"error": str(e)}

        try:
            corr_data = self._load_price_data_for_correlation(db, holdings) if price_data is None else price_data
            correlation_report = self._correlation.analyze(price_data=corr_data, holdings=holdings)
            result["correlation"] = {
                "pairs": [p.__dict__ for p in correlation_report.pairs],
                "clusters": [c.__dict__ for c in correlation_report.clusters],
                "high_correlation_pairs": [p.__dict__ for p in correlation_report.high_correlation_pairs],
                "symbols": correlation_report.symbols,
            }
        except Exception as e:
            logger.error(f"Correlation analysis failed: {e}")
            result["correlation"] = {"error": str(e)}
            correlation_report = None

        try:
            vol_data = corr_data if price_data is None else price_data
            volatility_report = self._volatility.analyze(price_data=vol_data, holdings=holdings)
            result["volatility"] = volatility_report.__dict__
        except Exception as e:
            logger.error(f"Volatility analysis failed: {e}")
            result["volatility"] = {"error": str(e)}
            volatility_report = None

        try:
            bias_report = self._directional.analyze(holdings, total_capital)
            result["directional_bias"] = bias_report.__dict__
        except Exception as e:
            logger.error(f"Directional bias analysis failed: {e}")
            result["directional_bias"] = {"error": str(e)}
            bias_report = None

        try:
            risk_report = self._risk.generate(
                exposure_report, correlation_report or self._correlation.analyze(holdings=holdings),
                volatility_report or self._volatility.analyze(holdings=holdings),
                bias_report or self._directional.analyze(holdings, total_capital),
                total_capital,
            )
            result["risk_insights"] = risk_report.__dict__
        except Exception as e:
            logger.error(f"Risk insights generation failed: {e}")
            result["risk_insights"] = {"error": str(e)}

        regime_label = self._get_regime_context()
        result["regime_label"] = regime_label

        result["latency_seconds"] = round(time.monotonic() - start, 3)

        if persist and self._config.persist_insights:
            try:
                self._persistence.save_snapshot(result)
            except Exception as e:
                logger.warning(f"Failed to persist portfolio insights: {e}")

        return result

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._persistence.get_history(limit=limit)

    def get_latest_snapshot(self) -> Optional[dict[str, Any]]:
        return self._persistence.get_latest()

    def _load_holdings(self, db: Session) -> list[dict[str, Any]]:
        try:
            from models.stock import Stock, StockStatus
            stocks = db.query(Stock).filter(
                Stock.status == StockStatus.ENTERED
            ).all()
            return [s.to_dict() for s in stocks]
        except Exception as e:
            logger.warning(f"Failed to load holdings from DB: {e}")
            return []

    def _load_price_data_for_correlation(self, db: Session,
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
            logger.warning(f"Failed to load price data for correlation: {e}")
            return pd.DataFrame()
