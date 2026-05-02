from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

from services.broker.kite import KiteBroker
from core.pipeline.feature_pipeline import FeaturePipeline
from core.decision.decision_engine import DecisionEngine
from core.risk.position_sizer import PositionSizer
from core.model.model import TradingModel
from core.model.registry import ModelRegistry
from core.config import get_settings
from core.logging import logger


@dataclass
class StockAnalysis:
    symbol: str
    trading_symbol: str
    should_enter: bool
    confidence: float
    signal: str
    entry_price: float
    target_price: float
    stop_loss: float
    position_size: int
    reason: str
    momentum_score: float = 0.0
    current_price: float = 0.0
    risk_reward: float = 0.0
    optimal_entry_pct: float = 0.0
    strategy: str = ""
    p_buy: float = 0.0
    p_hold: float = 0.0
    p_sell: float = 0.0


class StockAnalyzer:
    def __init__(self, broker: KiteBroker, model_path: Optional[str] = None):
        self.broker = broker
        self.settings = get_settings()
        self.feature_pipeline = FeaturePipeline()
        self.decision_engine = DecisionEngine()
        self.position_sizer = PositionSizer(risk_pct=self.settings.risk_per_trade / 100)

        self.model: Optional[TradingModel] = None
        self._model_loaded = False
        self.lookback_days = 60
        self.interval = "60minute"

        self._nifty_data = None

        if model_path:
            self.load_model(model_path)

    def load_model(self, model_path: str) -> bool:
        try:
            registry = ModelRegistry()
            data = registry.load(model_path)

            self.model = TradingModel()
            self.model.model = data["model"]
            self.model.scaler = data.get("scaler")
            self.model.feature_names = data.get("feature_names", [])
            self.model._is_trained = True
            self._model_loaded = True

            metrics = data.get("metrics", {})
            logger.info(f"ML model loaded: {model_path} ({len(self.model.feature_names)} features)")
            return True
        except Exception as e:
            logger.warning(f"ML model load failed: {e}")
            return False

    async def analyze(self, symbol: str, available_cash: float) -> StockAnalysis:
        trading_symbol = self.broker._map_chartink_to_zerodha(symbol)

        try:
            df = await self._fetch_data(trading_symbol)
            if df.empty or len(df) < 30:
                return self._no_trade(symbol, trading_symbol, "Insufficient data")

            features = self.feature_pipeline.transform(df, self._nifty_data)
            if features.empty or len(features) < 5:
                return self._no_trade(symbol, trading_symbol, "Feature generation failed")

            current_price = float(df["close"].iloc[-1])

            if not self._model_loaded or self.model is None or not self.model.is_trained():
                return self._no_trade(symbol, trading_symbol, "ML model not loaded")

            X = features.iloc[-1:].values
            X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

            probs = self.model.predict_proba(X)[0]

            decision = self.decision_engine.decide_entry(probs)

            if decision["decision"] != "BUY":
                return self._no_trade(
                    symbol, trading_symbol,
                    decision["reason"],
                    confidence=decision["confidence"],
                    p_sell=decision["p_sell"],
                    p_hold=decision["p_hold"],
                    p_buy=decision["p_buy"],
                )

            stop_loss_pct = self.settings.stop_loss_pct / 100
            stop_loss = current_price * (1 - stop_loss_pct)
            target_price = current_price * (1 + self.settings.target_profit_pct / 100)

            position_size = self.position_sizer.size(available_cash, current_price, stop_loss)

            if position_size < 1:
                return self._no_trade(
                    symbol, trading_symbol,
                    "Position size too small",
                    confidence=decision["confidence"],
                    p_sell=decision["p_sell"],
                    p_hold=decision["p_hold"],
                    p_buy=decision["p_buy"],
                )

            risk = abs(current_price - stop_loss)
            reward = abs(target_price - current_price)
            risk_reward = reward / max(risk, 0.001)

            logger.info(
                f"{symbol} ({trading_symbol}): ML BUY | "
                f"Conf={decision['confidence']:.0%} p_buy={decision['p_buy']:.0%} | "
                f"Entry={current_price:.2f} Target={target_price:.2f} SL={stop_loss:.2f} | "
                f"Qty={position_size} RR={risk_reward:.1f}"
            )

            return StockAnalysis(
                symbol=symbol,
                trading_symbol=trading_symbol,
                should_enter=True,
                confidence=decision["confidence"],
                signal="BUY",
                entry_price=current_price,
                target_price=target_price,
                stop_loss=stop_loss,
                position_size=position_size,
                reason=decision["reason"],
                current_price=current_price,
                risk_reward=risk_reward,
                p_buy=decision["p_buy"],
                p_hold=decision["p_hold"],
                p_sell=decision["p_sell"],
            )

        except Exception as e:
            logger.error(f"Analysis failed for {symbol}: {e}")
            return self._no_trade(symbol, "", f"Error: {str(e)}")

    async def analyze_batch(self, symbols: List[str], available_cash: float) -> List[StockAnalysis]:
        all_analysis = []
        for symbol in symbols:
            analysis = await self.analyze(symbol, available_cash)
            all_analysis.append(analysis)

        valid = [a for a in all_analysis if a.should_enter and a.position_size > 0]
        valid.sort(key=lambda x: x.confidence, reverse=True)

        top = valid[: self.settings.max_positions]

        if top:
            logger.info(f"Top {len(top)} ML signals:")
            for a in top:
                logger.info(
                    f"  {a.trading_symbol}: conf={a.confidence:.0%} "
                    f"p_buy={a.p_buy:.0%} price={a.current_price:.2f} qty={a.position_size}"
                )

        return top

    def rank_stocks(self, symbols: List[str], available_cash: float, max_positions: int = 3) -> List[Dict]:
        return []

    async def _fetch_data(self, symbol: str) -> pd.DataFrame:
        try:
            to_date = datetime.utcnow()
            from_date = to_date - timedelta(days=self.lookback_days)

            data = self.broker.get_historical_data(symbol, from_date, to_date, self.interval)
            if not data:
                return pd.DataFrame()

            df = pd.DataFrame(data)
            if "date" in df.columns:
                df["timestamp"] = pd.to_datetime(df["date"])
                df.set_index("timestamp", inplace=True)
                df.drop("date", axis=1, inplace=True)

            numeric_cols = ["open", "high", "low", "close", "volume"]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            return df
        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            return pd.DataFrame()

    async def _fetch_nifty_and_update(self, df: pd.DataFrame) -> None:
        try:
            to_date = datetime.utcnow()
            from_date = to_date - timedelta(days=60)
            nifty_data = self.broker.get_nifty_data(from_date, to_date, "60minute")
            if nifty_data:
                self._nifty_data = pd.DataFrame(nifty_data)
                if "date" in self._nifty_data.columns:
                    self._nifty_data["timestamp"] = pd.to_datetime(self._nifty_data["date"])
                    self._nifty_data.set_index("timestamp", inplace=True)
                logger.debug("NIFTY data loaded for relative strength features")
        except Exception as e:
            logger.debug(f"NIFTY fetch error: {e}")

    def _no_trade(
        self,
        symbol: str,
        trading_symbol: str,
        reason: str,
        confidence: float = 0.0,
        p_sell: float = 0.0,
        p_hold: float = 0.0,
        p_buy: float = 0.0,
    ) -> StockAnalysis:
        logger.debug(f"{symbol}: NO_TRADE - {reason}")
        return StockAnalysis(
            symbol=symbol,
            trading_symbol=trading_symbol,
            should_enter=False,
            confidence=confidence,
            signal="HOLD",
            entry_price=0,
            target_price=0,
            stop_loss=0,
            position_size=0,
            reason=reason,
            p_sell=p_sell,
            p_hold=p_hold,
            p_buy=p_buy,
        )
