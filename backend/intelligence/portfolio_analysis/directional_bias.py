from __future__ import annotations
from typing import Any
from dataclasses import dataclass


@dataclass
class DirectionalBiasReport:
    net_exposure_pct: float
    long_exposure_pct: float
    short_exposure_pct: float
    long_positions: int
    short_positions: int
    bias: str


class DirectionalBiasAnalyzer:
    def analyze(self, holdings: list[dict[str, Any]],
                total_capital: float | None = None) -> DirectionalBiasReport:
        if not holdings:
            return DirectionalBiasReport(
                net_exposure_pct=0.0,
                long_exposure_pct=0.0,
                short_exposure_pct=0.0,
                long_positions=0,
                short_positions=0,
                bias="neutral",
            )

        total_cap = total_capital or sum(self._holding_value(h) for h in holdings)
        if total_cap <= 0:
            total_cap = 1.0

        long_value = 0.0
        short_value = 0.0
        long_count = 0
        short_count = 0

        for h in holdings:
            val = self._holding_value(h)
            direction = self._detect_direction(h)
            if direction == "long":
                long_value += val
                long_count += 1
            elif direction == "short":
                short_value += val
                short_count += 1

        long_pct = (long_value / total_cap) * 100
        short_pct = (short_value / total_cap) * 100
        net_pct = long_pct - short_pct

        if net_pct > 10:
            bias = "bullish"
        elif net_pct < -10:
            bias = "bearish"
        else:
            bias = "neutral"

        return DirectionalBiasReport(
            net_exposure_pct=round(net_pct, 2),
            long_exposure_pct=round(long_pct, 2),
            short_exposure_pct=round(short_pct, 2),
            long_positions=long_count,
            short_positions=short_count,
            bias=bias,
        )

    def _holding_value(self, h: dict[str, Any]) -> float:
        qty = abs(float(h.get("entry_quantity") or h.get("quantity", 0)))
        price = float(h.get("entry_price") or h.get("current_price") or h.get("price", 0))
        return qty * price

    def _detect_direction(self, h: dict[str, Any]) -> str:
        qty = float(h.get("entry_quantity") or h.get("quantity", 0))
        if qty > 0:
            return "long"
        if qty < 0:
            return "short"
        side = str(h.get("side", "long")).lower()
        return side if side in ("long", "short") else "long"
