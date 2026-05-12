from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


class RegimeType(str, Enum):
    BULL_TREND = "bull_trend"
    BEAR_TREND = "bear_trend"
    SIDEWAYS = "sideways"
    BREAKOUT = "breakout"
    MEAN_REVERSION = "mean_reversion"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    EVENT_DRIVEN = "event_driven"
    UNKNOWN = "unknown"


REGIME_METADATA = {
    RegimeType.BULL_TREND: {
        "description": "Sustained upward price movement with strong trend indicators",
        "risk_level": "low",
        "suggested_behavior": ["increase position sizing", "hold for trend", "add on pullbacks"],
    },
    RegimeType.BEAR_TREND: {
        "description": "Sustained downward price movement with strong trend indicators",
        "risk_level": "high",
        "suggested_behavior": ["reduce exposure", "avoid long positions", "consider hedges"],
    },
    RegimeType.SIDEWAYS: {
        "description": "Price moving in a range without clear directional bias",
        "risk_level": "medium",
        "suggested_behavior": ["reduce position sizing", "use mean reversion strategies", "tighten stops"],
    },
    RegimeType.BREAKOUT: {
        "description": "Price breaking above resistance or below support with volume confirmation",
        "risk_level": "medium",
        "suggested_behavior": ["enter on confirmation", "use wide stops", "monitor volume"],
    },
    RegimeType.MEAN_REVERSION: {
        "description": "Price extended from moving average, likely to revert",
        "risk_level": "medium",
        "suggested_behavior": ["counter-trend entries", "tight stops", "quick profits"],
    },
    RegimeType.HIGH_VOLATILITY: {
        "description": "Elevated volatility environment with wide price swings",
        "risk_level": "high",
        "suggested_behavior": ["reduce position sizing", "widen stop losses", "avoid breakouts"],
    },
    RegimeType.LOW_VOLATILITY: {
        "description": "Compressed volatility environment with narrow price ranges",
        "risk_level": "low",
        "suggested_behavior": ["normal position sizing", "prepare for expansion", "use tight stops"],
    },
    RegimeType.EVENT_DRIVEN: {
        "description": "Abnormal price action driven by news, earnings, or macro events",
        "risk_level": "high",
        "suggested_behavior": ["reduce exposure", "avoid new entries", "wait for clarity"],
    },
    RegimeType.UNKNOWN: {
        "description": "Insufficient data to determine regime",
        "risk_level": "medium",
        "suggested_behavior": ["reduce position sizing", "wait for clearer signals"],
    },
}


@dataclass
class VolatilityContext:
    atr_pct: Optional[float] = None
    bb_width: Optional[float] = None
    bb_width_ratio: Optional[float] = None
    vix_level: Optional[float] = None


@dataclass
class TrendContext:
    ema_diff_pct: Optional[float] = None
    adx: Optional[float] = None
    macd_histogram: Optional[float] = None
    price_vs_ema: Optional[float] = None


@dataclass
class BreadthContext:
    adv_decl_ratio: Optional[float] = None
    pct_above_ma50: Optional[float] = None


@dataclass
class VolumeContext:
    volume_ratio: Optional[float] = None
    is_spike: bool = False


@dataclass
class RegimeOutput:
    regime: RegimeType
    confidence: float = 0.0
    risk_level: str = "medium"
    stability: str = "moderate"
    volatility_context: Optional[VolatilityContext] = None
    trend_context: Optional[TrendContext] = None
    breadth_context: Optional[BreadthContext] = None
    volume_context: Optional[VolumeContext] = None
    suggested_behavior: List[str] = field(default_factory=list)
    signal_breakdown: dict = field(default_factory=dict)
    timestamp: Optional[str] = None
    regime_features: Optional[Dict[str, Dict[str, float]]] = None
    transition_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        base = {
            "regime": self.regime.value if isinstance(self.regime, RegimeType) else self.regime,
            "confidence": round(self.confidence, 4),
            "risk_level": self.risk_level,
            "stability": self.stability,
            "suggested_behavior": self.suggested_behavior,
            "signal_breakdown": self.signal_breakdown,
            "timestamp": self.timestamp,
        }
        if self.volatility_context:
            base["volatility_context"] = {
                k: v for k, v in self.volatility_context.__dict__.items() if v is not None
            }
        if self.trend_context:
            base["trend_context"] = {
                k: v for k, v in self.trend_context.__dict__.items() if v is not None
            }
        if self.breadth_context:
            base["breadth_context"] = {
                k: v for k, v in self.breadth_context.__dict__.items() if v is not None
            }
        if self.volume_context:
            base["volume_context"] = {
                k: v for k, v in self.volume_context.__dict__.items() if v is not None
            }
        if self.transition_data:
            base["transition_data"] = self.transition_data
        return base

    @classmethod
    def from_dict(cls, d: dict) -> "RegimeOutput":
        regime_val = d.get("regime", "unknown")
        if isinstance(regime_val, str):
            try:
                regime = RegimeType(regime_val)
            except ValueError:
                regime = RegimeType.UNKNOWN
        else:
            regime = regime_val

        vc_data = d.get("volatility_context", {})
        vc = VolatilityContext(**vc_data) if vc_data else None
        tc_data = d.get("trend_context", {})
        tc = TrendContext(**tc_data) if tc_data else None
        bc_data = d.get("breadth_context", {})
        bc = BreadthContext(**bc_data) if bc_data else None
        voc_data = d.get("volume_context", {})
        voc = VolumeContext(**voc_data) if voc_data else None

        return cls(
            regime=regime,
            confidence=d.get("confidence", 0.0),
            risk_level=d.get("risk_level", "medium"),
            stability=d.get("stability", "moderate"),
            volatility_context=vc,
            trend_context=tc,
            breadth_context=bc,
            volume_context=voc,
            suggested_behavior=d.get("suggested_behavior", []),
            signal_breakdown=d.get("signal_breakdown", {}),
            timestamp=d.get("timestamp"),
        )
