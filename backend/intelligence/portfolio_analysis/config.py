from dataclasses import dataclass, field


@dataclass
class PortfolioConfig:
    enabled: bool = True
    max_sector_exposure_pct: float = 40.0
    max_single_position_pct: float = 20.0
    correlation_high_threshold: float = 0.80
    correlation_medium_threshold: float = 0.60
    volatility_high_threshold_pct: float = 4.0
    volatility_low_threshold_pct: float = 1.5
    lookback_days: int = 90
    min_trades_for_correlation: int = 5
    capital_deployment_pct: float = 100.0
    persist_insights: bool = True
