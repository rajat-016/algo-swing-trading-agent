from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict, field_validator
from typing import Optional
import enum
import os
from pathlib import Path


class TradingMode(str, enum.Enum):
    PAPER = "paper"
    LIVE = "live"


def _read_env_file_value(key: str, default: str = None) -> Optional[str]:
    try:
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if "=" in line:
                            k, v = line.split("=", 1)
                            if k.strip() == key:
                                return v.strip()
        return default
    except Exception:
        return default


_TRADING_MODE_FROM_ENV = _read_env_file_value("TRADING_MODE", "paper")
if _TRADING_MODE_FROM_ENV:
    os.environ["TRADING_MODE"] = _TRADING_MODE_FROM_ENV


class ZerodhaConfig(BaseSettings):
    model_config = ConfigDict(
        extra="ignore",
        env_file=".env",
        env_nested_delimiter="__",
    )

    api_key: str = Field(default="")
    api_secret: str = Field(default="")
    access_token: str = Field(default="")
    request_token: str = Field(default="")
    username: str = Field(default="")
    password: str = Field(default="")
    two_factor: str = Field(default="")
    kite_url: str = Field(default="https://api.kite.trade")
    enviro: str = Field(default="prod")


class Settings(BaseSettings):
    # Trading Parameters
    target_profit_pct: float = Field(default=20.0)
    stop_loss_pct: float = Field(default=3.0)
    max_positions: int = Field(default=3)
    risk_per_trade: float = Field(default=1.0)
    min_momentum_score: float = Field(default=0.4)

    # Risk Management Parameters
    max_daily_loss: float = Field(default=5.0)
    max_exposure: float = Field(default=60.0)
    min_account_balance: float = Field(default=5000.0)
    max_position_loss_pct: float = Field(default=3.0)

    # Market Protection (SL-M orders)
    use_market_protection: bool = Field(default=False)
    market_protection_pct: float = Field(default=0.5)

    # Database
    database_url: str = Field(default="sqlite:///trading.db")
    _backend_dir: Optional[Path] = None

    @field_validator("database_url", mode="before")
    @classmethod
    def resolve_db_path(cls, v):
        if v and v.startswith("sqlite:///"):
            path_part = v[len("sqlite:///"):]
            if not os.path.isabs(path_part):
                backend_dir = Path(__file__).resolve().parent.parent
                abs_path = backend_dir / path_part
                return f"sqlite:///{abs_path.as_posix()}"
        return v

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    # Trading Mode: 'paper' or 'live'
    trading_mode: str = Field(default=_TRADING_MODE_FROM_ENV)

    # Paper Trading
    paper_trading_capital: float = Field(default=100000.0)

    # ChartInk
    chartink_url: str = Field(default="")

    # ML Model
    model_path: str = Field(default="services/ai/model.joblib")

    # Trading Loop
    cycle_interval_seconds: int = Field(default=300)
    auto_start_trading: bool = Field(default=False)

    # Tiered Exit Settings
    tiered_exit_enabled: bool = Field(default=False)
    exit_only_profit: bool = Field(default=False)
    tier_1_pct: float = Field(default=5.0)
    tier_1_qty_pct: float = Field(default=25.0)
    tier_2_pct: float = Field(default=10.0)
    tier_2_qty_pct: float = Field(default=25.0)
    tier_3_pct: float = Field(default=15.0)
    tier_3_qty_pct: float = Field(default=25.0)
    tier_4_pct: float = Field(default=20.0)
    tier_4_qty_pct: float = Field(default=25.0)
    trailing_sl_tier_1: float = Field(default=0.0)
    trailing_sl_tier_2: float = Field(default=3.0)
    trailing_sl_tier_3: float = Field(default=7.0)
    ml_exit_min_tier: int = Field(default=2)

    # Zerodha
    zerodha: ZerodhaConfig = Field(default_factory=ZerodhaConfig)

    # AI Copilot
    ai_copilot_enabled: bool = Field(default=False)
    ollama_host: str = Field(default="http://localhost:11434")
    llm_model: str = Field(default="qwen2.5:7b")
    embedding_model: str = Field(default="nomic-embed-text")
    chromadb_persist_path: str = Field(default="data/chromadb")
    duckdb_path: str = Field(default="data/analytics.duckdb")

    # Market Regime Engine
    regime_engine_enabled: bool = Field(default=True)
    regime_ema_short: int = Field(default=50)
    regime_ema_long: int = Field(default=200)
    regime_sideways_threshold_pct: float = Field(default=0.02)
    regime_adx_trend_threshold: float = Field(default=25.0)
    regime_high_vol_atr_pct: float = Field(default=0.03)
    regime_low_vol_atr_pct: float = Field(default=0.015)
    regime_breakout_volume_ratio: float = Field(default=1.5)
    regime_event_volume_spike_ratio: float = Field(default=3.0)
    regime_stability_lookback: int = Field(default=5)
    regime_persist_history: bool = Field(default=True)

    # AI Trade Journal
    trade_journal_enabled: bool = Field(default=False)

    # Reflection Engine
    reflection_engine_enabled: bool = Field(default=False)
    reflection_recurring_window_days: int = Field(default=30)
    reflection_degradation_baseline_days: int = Field(default=60)
    reflection_min_trades_for_pattern: int = Field(default=5)
    reflection_pattern_frequency_threshold: float = Field(default=0.15)
    reflection_summary_auto_generate_enabled: bool = Field(default=False)
    reflection_summary_auto_generate_interval_hours: int = Field(default=24)

    # Quant Research Assistant
    research_assistant_enabled: bool = Field(default=True)

    # Portfolio Intelligence Engine
    portfolio_engine_enabled: bool = Field(default=True)

    # Explainability Engine
    explainability_enabled: bool = Field(default=True)
    shap_top_features: int = Field(default=15)
    shap_background_samples: int = Field(default=100)
    shap_max_display_features: int = Field(default=20)
    explanation_cache_ttl_seconds: int = Field(default=3600)

    model_config = ConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )

    @property
    def is_paper_trading(self) -> bool:
        return self.trading_mode.lower() == "paper"

    @property
    def is_live_trading(self) -> bool:
        return self.trading_mode.lower() == "live"


_settings_instance = None

STRATEGY_TARGETS = {
    "trend_pullback": {"target": 0.25, "stop_loss": 0.03, "min_score": 0.6},
    "breakout_retest": {"target": 0.20, "stop_loss": 0.03, "min_score": 0.6},
    "stage_2": {"target": 0.30, "stop_loss": 0.04, "min_score": 0.6},
    "relative_strength": {"target": 0.18, "stop_loss": 0.03, "min_score": 0.5},
    "vcp": {"target": 0.35, "stop_loss": 0.04, "min_score": 0.7},
    "gap_up": {"target": 0.15, "stop_loss": 0.02, "min_score": 0.6},
    "support_zone": {"target": 0.20, "stop_loss": 0.03, "min_score": 0.5},
    "sector_rotation": {"target": 0.25, "stop_loss": 0.03, "min_score": 0.6},
    "multi_timeframe": {"target": 0.20, "stop_loss": 0.03, "min_score": 0.6},
}


def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


def get_strategy_target(strategy: str) -> dict:
    return STRATEGY_TARGETS.get(strategy, {"target": 0.20, "stop_loss": 0.03, "min_score": 0.5})


settings = get_settings()
