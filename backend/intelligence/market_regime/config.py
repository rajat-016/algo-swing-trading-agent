from dataclasses import dataclass, field


@dataclass
class RegimeConfig:
    enabled: bool = False

    ema_short: int = 50
    ema_long: int = 200
    sideways_threshold_pct: float = 0.02

    adx_trend_threshold: float = 25.0
    adx_strong_threshold: float = 35.0

    high_vol_atr_pct: float = 0.03
    low_vol_atr_pct: float = 0.015

    bb_high_vol_multiplier: float = 1.5
    bb_low_vol_multiplier: float = 0.5

    breakout_volume_ratio: float = 1.5
    breakout_lookback: int = 20

    event_volume_spike_ratio: float = 3.0
    event_vix_spike_points: float = 5.0

    mean_reversion_bb_bands: float = 2.0
    mean_reversion_rsi_overbought: float = 70.0
    mean_reversion_rsi_oversold: float = 30.0

    trend_bull_separation_pct: float = 0.02
    trend_bear_separation_pct: float = -0.02

    vix_high_threshold: float = 25.0
    vix_low_threshold: float = 15.0

    confidence_signal_agreement_weight: float = 0.4
    confidence_signal_strength_weight: float = 0.4
    confidence_stability_weight: float = 0.2

    max_transition_history: int = 1000
    stability_lookback: int = 5

    transition_high_probability_threshold: float = 0.5
    transition_confidence_degradation_threshold: float = 0.15
    transition_vol_spike_threshold: float = 0.4
    transition_persistence_extended_ratio: float = 2.5
    transition_smoothing_window: int = 3

    persistence_duckdb_table: str = "market_regime_history"

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, d: dict) -> "RegimeConfig":
        valid_keys = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**filtered)
