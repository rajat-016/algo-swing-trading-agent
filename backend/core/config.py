from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import enum


class TradingMode(str, enum.Enum):
    PAPER = "paper"
    LIVE = "live"


class ZerodhaConfig(BaseSettings):
    api_key: str = Field(default="")
    api_secret: str = Field(default="")
    access_token: str = Field(default="")
    request_token: str = Field(default="")
    username: str = Field(default="")
    password: str = Field(default="")
    two_factor: str = Field(default="")
    kite_url: str = Field(default="https://kite.zerodha.com")
    enviro: str = Field(default="prod")

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"


class Settings(BaseSettings):
    # Trading Parameters
    target_profit_pct: float = Field(default=10.0)
    stop_loss_pct: float = Field(default=3.0)
    max_positions: int = Field(default=10)
    risk_per_trade: float = Field(default=1.0)
    min_confidence: float = Field(default=70.0)

    # Database
    database_url: str = Field(default="sqlite:///trading.db")

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    # Trading Mode: 'paper' or 'live'
    trading_mode: str = Field(default="paper")

    # Paper Trading
    paper_trading_capital: float = Field(default=100000.0)

    # ChartInk
    chartink_url: str = Field(default="")

    # Zerodha
    zerodha: ZerodhaConfig = Field(default_factory=ZerodhaConfig)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"

    @property
    def is_paper_trading(self) -> bool:
        return self.trading_mode.lower() == "paper"

    @property
    def is_live_trading(self) -> bool:
        return self.trading_mode.lower() == "live"


settings = Settings()


def get_settings() -> Settings:
    return settings
