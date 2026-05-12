from __future__ import annotations
from typing import Any
from dataclasses import dataclass

from core.logging import logger


@dataclass
class RiskAlert:
    category: str
    severity: str
    message: str
    details: dict[str, Any]


@dataclass
class RiskInsightsReport:
    alerts: list[RiskAlert]
    overexposure_risks: list[RiskAlert]
    correlated_position_risks: list[RiskAlert]
    instability_flags: list[str]
    overall_risk_level: str
    risk_score: float


class RiskInsightsGenerator:
    def __init__(self, max_sector_pct: float = 40.0,
                 max_position_pct: float = 20.0,
                 correlation_high: float = 0.80,
                 max_capital_concentration_pct: float = 50.0):
        self.max_sector_pct = max_sector_pct
        self.max_position_pct = max_position_pct
        self.correlation_high = correlation_high
        self.max_capital_concentration_pct = max_capital_concentration_pct

    def generate(self, exposure_report, correlation_report,
                 volatility_report, directional_bias,
                 total_capital: float | None = None) -> RiskInsightsReport:
        alerts = []
        overexposure_risks = []
        correlated_risks = []
        instability_flags = []

        overexposure_risks = self._check_overexposure(exposure_report)
        alerts.extend(overexposure_risks)

        correlated_risks = self._check_correlated_positions(correlation_report)
        alerts.extend(correlated_risks)

        vol_risks = self._check_volatility_risks(volatility_report)
        alerts.extend(vol_risks)

        bias_risks = self._check_directional_bias_risks(directional_bias)
        alerts.extend(bias_risks)

        instability_flags = self._check_instability(
            exposure_report, correlation_report, volatility_report
        )

        risk_score = self._calculate_risk_score(
            alerts, exposure_report, correlation_report, volatility_report
        )

        if risk_score >= 70:
            overall = "high"
        elif risk_score >= 40:
            overall = "medium"
        else:
            overall = "low"

        return RiskInsightsReport(
            alerts=alerts,
            overexposure_risks=overexposure_risks,
            correlated_position_risks=correlated_risks,
            instability_flags=instability_flags,
            overall_risk_level=overall,
            risk_score=round(risk_score, 1),
        )

    def _check_overexposure(self, exposure_report) -> list[RiskAlert]:
        alerts = []
        for sec in exposure_report.sector_exposures:
            if sec.is_overexposed:
                alerts.append(RiskAlert(
                    category="sector_overexposure",
                    severity="high",
                    message=f"Sector '{sec.sector}' is {sec.total_pct}% of portfolio (max: {self.max_sector_pct}%)",
                    details={"sector": sec.sector, "exposure_pct": sec.total_pct,
                             "threshold": self.max_sector_pct},
                ))

        for conc in exposure_report.capital_concentrations[:3]:
            if conc.pct_of_portfolio > self.max_position_pct:
                alerts.append(RiskAlert(
                    category="position_concentration",
                    severity="medium",
                    message=f"{conc.symbol} is {conc.pct_of_portfolio}% of portfolio (max: {self.max_position_pct}%)",
                    details={"symbol": conc.symbol, "pct": conc.pct_of_portfolio,
                             "threshold": self.max_position_pct},
                ))

        hhi = exposure_report.herfindahl_index
        if hhi > 0.3:
            alerts.append(RiskAlert(
                category="herfindahl_high",
                severity="medium",
                message=f"Portfolio Herfindahl index {hhi} indicates high concentration risk",
                details={"herfindahl_index": hhi},
            ))

        return alerts

    def _check_correlated_positions(self, correlation_report) -> list[RiskAlert]:
        alerts = []
        for pair in correlation_report.high_correlation_pairs:
            alerts.append(RiskAlert(
                category="high_correlation",
                severity="medium",
                message=f"{pair.symbol_a} and {pair.symbol_b} have correlation {pair.correlation}",
                details={"symbol_a": pair.symbol_a, "symbol_b": pair.symbol_b,
                         "correlation": pair.correlation},
            ))

        if correlation_report.clusters:
            for cluster in correlation_report.clusters[:2]:
                if cluster.avg_correlation >= self.correlation_high:
                    alerts.append(RiskAlert(
                        category="correlation_cluster",
                        severity="high",
                        message=f"Correlation cluster: {', '.join(cluster.symbols)} (avg r={cluster.avg_correlation})",
                        details={"symbols": cluster.symbols,
                                 "avg_correlation": cluster.avg_correlation},
                    ))

        return alerts

    def _check_volatility_risks(self, volatility_report) -> list[RiskAlert]:
        alerts = []
        if volatility_report.high_vol_holdings:
            alerts.append(RiskAlert(
                category="high_volatility",
                severity="medium",
                message=f"High volatility holdings: {', '.join(volatility_report.high_vol_holdings)}",
                details={"holdings": volatility_report.high_vol_holdings},
            ))

        if volatility_report.weighted_vol_pct > 5.0:
            alerts.append(RiskAlert(
                category="portfolio_high_volatility",
                severity="medium",
                message=f"Portfolio weighted volatility {volatility_report.weighted_vol_pct}%",
                details={"weighted_vol_pct": volatility_report.weighted_vol_pct},
            ))

        return alerts

    def _check_directional_bias_risks(self, directional_bias) -> list[RiskAlert]:
        alerts = []
        net = directional_bias.net_exposure_pct
        if abs(net) > 80:
            alerts.append(RiskAlert(
                category="extreme_directional_bias",
                severity="high",
                message=f"Portfolio has {directional_bias.bias} bias with {net}% net exposure",
                details={"net_exposure_pct": net, "bias": directional_bias.bias},
            ))
        elif abs(net) > 50:
            alerts.append(RiskAlert(
                category="strong_directional_bias",
                severity="medium",
                message=f"Portfolio has {directional_bias.bias} bias with {net}% net exposure",
                details={"net_exposure_pct": net, "bias": directional_bias.bias},
            ))

        return alerts

    def _check_instability(self, exposure_report, correlation_report,
                           volatility_report) -> list[str]:
        flags = []
        if exposure_report.top_holding_pct > 30:
            flags.append("Single position exceeds 30% of portfolio")
        if correlation_report.clusters and len(correlation_report.clusters[0].symbols) > 3:
            flags.append("Large correlation cluster detected (>3 positions)")
        if volatility_report.weighted_vol_pct > 4.0:
            flags.append("Portfolio volatility above 4% threshold")
        if exposure_report.num_sectors <= 2 and exposure_report.num_sectors > 0:
            flags.append("Portfolio concentrated in 2 or fewer sectors")
        return flags

    def _calculate_risk_score(self, alerts: list[RiskAlert],
                              exposure_report, correlation_report,
                              volatility_report) -> float:
        score = 0.0
        for alert in alerts:
            if alert.severity == "high":
                score += 20
            elif alert.severity == "medium":
                score += 10
            else:
                score += 5

        if exposure_report.herfindahl_index > 0.3:
            score += 10
        if exposure_report.top_holding_pct > 30:
            score += 10
        if volatility_report.weighted_vol_pct > 5.0:
            score += 10

        return min(score, 100.0)
