from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from typing import Optional
import enum
import os


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
    target_profit_pct: float = Field(default=10.0)
    stop_loss_pct: float = Field(default=3.0)
    max_positions: int = Field(default=10)
    risk_per_trade: float = Field(default=1.0)
    min_momentum_score: float = Field(default=0.4)

    # Market Protection (SL-M orders)
    use_market_protection: bool = Field(default=False)
    market_protection_pct: float = Field(default=0.5)

    # Database
    database_url: str = Field(default="sqlite:///trading.db")

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
    model_path: str = Field(default="model.joblib")

    # Trading Loop
    cycle_interval_seconds: int = Field(default=300)
    auto_start_trading: bool = Field(default=False)

    # Zerodha
    zerodha: ZerodhaConfig = Field(default_factory=ZerodhaConfig)

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


def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


settings = get_settings()
