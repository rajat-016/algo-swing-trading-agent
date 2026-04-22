from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List
import pandas as pd
from datetime import timedelta

from services.broker.zerodha import ZerodhaBroker
from services.ai.features import FeatureEngineer
from services.ai.model import ModelTrainer
from core.config import get_settings
from core.logging import logger


@dataclass
class StockAnalysis:
    symbol: str
    should_enter: bool
    confidence: float
    signal: str
    entry_price: float
    target_price: float
    stop_loss: float
    position_size: int
    reason: str
    momentum_score: float = 0.0


class StockAnalyzer:
    def __init__(self, broker: ZerodhaBroker, model_path: Optional[str] = None):
        self.broker = broker
        self.settings = get_settings()
        self.feature_engineer = FeatureEngineer()
        self.model = ModelTrainer(
            target_return=self.settings.target_profit_pct / 100,
            stop_loss=self.settings.stop_loss_pct / 100,
        )
        self._model_loaded = False
        self.min_confidence = self.settings.min_confidence
        self.lookback_days = 60

        if model_path:
            self.load_model(model_path)

    def load_model(self, model_path: str) -> bool:
        try:
            if self.model.load_model(model_path):
                self._model_loaded = True
                logger.info(f"Model loaded: {model_path}")
                return True
            return False
        except Exception as e:
            logger.warning(f"Model load failed (will use rule-based): {e}")
            return False

    async def analyze(self, symbol: str, available_cash: float) -> StockAnalysis:
        logger.info(f"Analyzing: {symbol}")

        try:
            df = await self._fetch_data(symbol)
            if df.empty or len(df) < 20:
                return self._create_analysis(symbol, False, 0, "HOLD", 0, 0, 0, 0, "Insufficient data")

            current_price = float(df["close"].iloc[-1])
            prediction = await self._get_prediction(df)
            momentum_score = self._calculate_momentum_score(df)

            confidence = prediction.get("confidence", 0) if prediction else 0
            ml_signal = prediction.get("signal", "HOLD") if prediction else "HOLD"

            if confidence < self.min_confidence and ml_signal != "BUY":
                return self._create_analysis(
                    symbol,
                    False,
                    confidence,
                    ml_signal,
                    current_price,
                    0,
                    0,
                    0,
                    f"Low confidence: {confidence:.1f}%",
                    momentum_score,
                )

            target, sl = self._calculate_targets(df, current_price)
            position_size = self._calculate_position_size(current_price, sl, available_cash)

            if position_size < 1:
                return self._create_analysis(
                    symbol,
                    False,
                    confidence,
                    ml_signal,
                    current_price,
                    target,
                    sl,
                    position_size,
                    "Position size too small",
                    momentum_score,
                )

            should_enter = confidence >= self.min_confidence or ml_signal == "BUY"
            reason = self._generate_entry_reason(df, confidence, momentum_score)

            return self._create_analysis(
                symbol,
                should_enter,
                confidence,
                "BUY" if should_enter else "HOLD",
                current_price,
                target,
                sl,
                position_size,
                reason,
                momentum_score,
            )

        except Exception as e:
            logger.error(f"Analysis failed for {symbol}: {e}")
            return self._create_analysis(symbol, False, 0, "ERROR", 0, 0, 0, 0, str(e))

    async def analyze_batch(self, symbols: List[str], available_cash: float) -> List[StockAnalysis]:
        results = []
        for symbol in symbols:
            analysis = await self.analyze(symbol, available_cash)
            if analysis.should_enter:
                results.append(analysis)

        results.sort(key=lambda x: (x.confidence, x.momentum_score), reverse=True)
        logger.info(f"Batch analysis: {len(results)}/{len(symbols)} passed filters")
        return results

    def rank_stocks(self, symbols: List[str], available_cash: float, max_positions: int = 3) -> List[Dict]:
        ranked = []
        for symbol in symbols:
            try:
                df = pd.DataFrame()
                ranked.append({"symbol": symbol, "momentum_score": 0, "current_price": 0})
            except Exception as e:
                logger.error(f"Score calc failed for {symbol}: {e}")

        ranked.sort(key=lambda x: x["momentum_score"], reverse=True)
        return ranked[:max_positions]

    async def _fetch_data(self, symbol: str) -> pd.DataFrame:
        try:
            to_date = datetime.utcnow()
            from_date = to_date - timedelta(days=self.lookback_days)

            data = self.broker.get_historical_data(symbol, from_date, to_date, "15minute")
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

    async def _get_prediction(self, df: pd.DataFrame) -> Dict:
        if not self._model_loaded:
            return {"signal": "HOLD", "confidence": 0}

        try:
            features_df = self.feature_engineer.generate_features(df)
            features_df = features_df.dropna()

            if len(features_df) < 50:
                return {"signal": "HOLD", "confidence": 0}

            available_features = [f for f in self.model.feature_names if f in features_df.columns]
            X = features_df[available_features].tail(1).values

            prediction = self.model.predict(X)[0]
            probabilities = self.model.predict_proba(X)[0]

            signal_map = {-1: "SELL", 0: "HOLD", 1: "BUY"}
            signal = signal_map.get(prediction, "HOLD")
            confidence = float(max(probabilities)) * 100

            return {"signal": signal, "confidence": confidence}

        except Exception as e:
            logger.debug(f"Prediction failed: {e}")
            return {"signal": "HOLD", "confidence": 0}

    def _calculate_momentum_score(self, df: pd.DataFrame) -> float:
        if df.empty or len(df) < 20:
            return 0

        try:
            score = 0

            price_change_10d = ((df["close"].iloc[-1] - df["close"].iloc[-11]) / df["close"].iloc[-11]) * 100 if len(df) >= 11 else 0
            score += min(30, max(0, price_change_10d * 3))

            if "rsi_14" in df.columns:
                rsi = df["rsi_14"].iloc[-1]
                if rsi < 30:
                    score += 30
                elif rsi < 50:
                    score += 20
                elif rsi < 70:
                    score += 10

            if "volume_ratio" in df.columns:
                vol_ratio = float(df["volume_ratio"].iloc[-1]) if not pd.isna(df["volume_ratio"].iloc[-1]) else 0
                score += min(20, vol_ratio * 10)

            if "ema_20" in df.columns and "ema_50" in df.columns:
                ema_20 = df["ema_20"].iloc[-1]
                ema_50 = df["ema_50"].iloc[-1]
                if not pd.isna(ema_20) and not pd.isna(ema_50) and ema_20 > ema_50:
                    score += 20

            return score / 100

        except Exception as e:
            logger.debug(f"Momentum score calc failed: {e}")
            return 0

    def _calculate_targets(self, df: pd.DataFrame, current_price: float) -> tuple:
        try:
            atr = self._calculate_atr(df)
            target = current_price + (atr * 3)
            sl = current_price - (atr * 1)
            return target, sl
        except Exception:
            target = current_price * (1 + self.settings.target_profit_pct / 100)
            sl = current_price * (1 - self.settings.stop_loss_pct / 100)
            return target, sl

    def _calculate_atr(self, df: pd.DataFrame) -> float:
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]

            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())

            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=14).mean().iloc[-1]

            return float(atr)
        except Exception:
            return float(df["close"].iloc[-1]) * 0.02

    def _calculate_position_size(self, entry_price: float, stop_loss: float, cash: float) -> int:
        try:
            risk_amount = cash * (self.settings.risk_per_trade / 100)
            price_risk = abs(entry_price - stop_loss)

            if price_risk > 0:
                quantity = int(risk_amount / price_risk)
            else:
                return 0

            max_qty = int(cash / entry_price)
            return min(quantity, max_qty)

        except Exception:
            return 0

    def _generate_entry_reason(self, df: pd.DataFrame, confidence: float, momentum: float) -> str:
        reasons = []
        if confidence >= 70:
            reasons.append(f"ML Confidence {confidence:.0f}%")
        if momentum >= 0.6:
            reasons.append("Strong Momentum")
        if "rsi_14" in df.columns and df["rsi_14"].iloc[-1] < 50:
            reasons.append(f"RSI={df['rsi_14'].iloc[-1]:.0f}")
        if "volume_ratio" in df.columns and df["volume_ratio"].iloc[-1] > 1.5:
            reasons.append("Volume Spike")
        return " | ".join(reasons) if reasons else "Entry Signal"

    def _create_analysis(
        self,
        symbol: str,
        should_enter: bool,
        confidence: float,
        signal: str,
        entry_price: float,
        target_price: float,
        stop_loss: float,
        position_size: int,
        reason: str,
        momentum_score: float = 0,
    ) -> StockAnalysis:
        return StockAnalysis(
            symbol=symbol,
            should_enter=should_enter,
            confidence=confidence,
            signal=signal,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            position_size=position_size,
            reason=reason,
            momentum_score=momentum_score,
        )
