from __future__ import annotations
from typing import Any
from dataclasses import dataclass, field, asdict

from core.logging import logger
from intelligence.trade_analysis.sector_map import get_sector


@dataclass
class SectorExposure:
    sector: str
    total_value: float
    total_pct: float
    holdings: list[dict[str, Any]]
    is_overexposed: bool = False


@dataclass
class CapitalConcentration:
    symbol: str
    value: float
    pct_of_portfolio: float
    rank: int = 0


@dataclass
class ExposureReport:
    total_portfolio_value: float
    sector_exposures: list[SectorExposure]
    capital_concentrations: list[CapitalConcentration]
    top_holding_pct: float
    top_3_holdings_pct: float
    num_sectors: int
    herfindahl_index: float


class ExposureAnalyzer:
    def __init__(self, max_sector_exposure_pct: float = 40.0,
                 max_single_position_pct: float = 20.0):
        self.max_sector_exposure_pct = max_sector_exposure_pct
        self.max_single_position_pct = max_single_position_pct

    def analyze(self, holdings: list[dict[str, Any]],
                total_capital: float | None = None) -> ExposureReport:
        if not holdings:
            return ExposureReport(
                total_portfolio_value=0.0,
                sector_exposures=[],
                capital_concentrations=[],
                top_holding_pct=0.0,
                top_3_holdings_pct=0.0,
                num_sectors=0,
                herfindahl_index=0.0,
            )

        total_value = total_capital or sum(
            self._holding_value(h) for h in holdings
        )
        if total_value <= 0:
            total_value = 1.0

        holdings_with_value = []
        for h in holdings:
            val = self._holding_value(h)
            if val > 0:
                holdings_with_value.append({**h, "_value": val})

        sector_map: dict[str, list[dict[str, Any]]] = {}
        for h in holdings_with_value:
            sym = (h.get("symbol") or "").upper().replace(".NS", "")
            sector = get_sector(sym) or "Unknown"
            if sector not in sector_map:
                sector_map[sector] = []
            sector_map[sector].append(h)

        sector_exposures = []
        for sector, sec_holdings in sorted(sector_map.items()):
            sector_value = sum(h["_value"] for h in sec_holdings)
            sector_pct = (sector_value / total_value) * 100
            sector_exposures.append(SectorExposure(
                sector=sector,
                total_value=round(sector_value, 2),
                total_pct=round(sector_pct, 2),
                holdings=[{"symbol": h.get("symbol"), "value": round(h["_value"], 2),
                           "pct": round((h["_value"] / total_value) * 100, 2)}
                          for h in sec_holdings],
                is_overexposed=sector_pct > self.max_sector_exposure_pct,
            ))

        sorted_holdings = sorted(
            holdings_with_value, key=lambda h: h["_value"], reverse=True
        )
        concentrations = []
        for i, h in enumerate(sorted_holdings):
            pct = (h["_value"] / total_value) * 100
            concentrations.append(CapitalConcentration(
                symbol=h.get("symbol", "UNKNOWN"),
                value=round(h["_value"], 2),
                pct_of_portfolio=round(pct, 2),
                rank=i + 1,
            ))

        top_holding_pct = concentrations[0].pct_of_portfolio if concentrations else 0.0
        top_3_pct = sum(c.pct_of_portfolio for c in concentrations[:3])
        herfindahl = sum((c.pct_of_portfolio / 100) ** 2 for c in concentrations)

        return ExposureReport(
            total_portfolio_value=round(total_value, 2),
            sector_exposures=sector_exposures,
            capital_concentrations=concentrations,
            top_holding_pct=top_holding_pct,
            top_3_holdings_pct=round(top_3_pct, 2),
            num_sectors=len(sector_exposures),
            herfindahl_index=round(herfindahl, 4),
        )

    def _holding_value(self, h: dict[str, Any]) -> float:
        qty = abs(float(h.get("entry_quantity") or h.get("quantity", 0)))
        price = float(h.get("entry_price") or h.get("current_price") or h.get("price", 0))
        return qty * price
