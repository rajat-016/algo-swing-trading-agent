from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List
import pandas as pd
from datetime import timedelta

from services.broker.kite import KiteBroker
from services.ai.features import FeatureEngineer
from services.ai.model import ModelTrainer
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


class StockAnalyzer:
    def __init__(self, broker: KiteBroker, model_path: Optional[str] = None):
        self.broker = broker
        self.settings = get_settings()
        self.feature_engineer = FeatureEngineer()
        self.model = ModelTrainer(
            target_return=self.settings.target_profit_pct / 100,
            stop_loss=self.settings.stop_loss_pct / 100,
        )
        self._model_loaded = False
        self.min_momentum_score = self.settings.min_momentum_score
        self.lookback_days = 60
        self.interval = "60minute"

        if model_path:
            self.load_model(model_path)

    def load_model(self, model_path: str) -> bool:
        try:
            if self.model.load_model(model_path):
                self._model_loaded = True
                logger.debug(f"Model loaded: {model_path}")
                return True
            return False
        except Exception as e:
            logger.warning(f"Model load failed (will use rule-based): {e}")
            return False

    async def analyze(self, symbol: str, available_cash: float) -> StockAnalysis:
        chartink_input = symbol
        trading_symbol = self.broker._map_chartink_to_zerodha(symbol)
        
        try:
            df = await self._fetch_data(trading_symbol)
            if df.empty or len(df) < 20:
                logger.info(f"{trading_symbol}: No data ({len(df)} candles)")
                return self._create_analysis(symbol, trading_symbol, False, 0, "HOLD", 0, 0, 0, 0, "Insufficient data")
            
            current_price = float(df["close"].iloc[-1])
            technical_score = self._calculate_technical_score(df)
            
            ml_signal = "HOLD"
            ml_confidence = 0
            
            if self._model_loaded:
                try:
                    prediction = await self._get_prediction(df)
                    ml_signal = prediction.get("signal", "HOLD")
                    ml_confidence = prediction.get("confidence", 0)
                except:
                    pass
            
            momentum_score = self._get_momentum_for_ranking(df) if self._model_loaded else technical_score
            
            should_enter = False
            reason = ""
            
            if ml_signal == "BUY" or (ml_signal == "HOLD" and ml_confidence > 50):
                should_enter = True
                reason = f"ML: {ml_signal} ({ml_confidence:.0f}%)"
            elif technical_score >= 0.3:
                should_enter = True
                reason = f"Technical: {technical_score:.2f}"
                ml_confidence = technical_score * 100
            
            if not should_enter:
                logger.info(f"{symbol}: SKIP - {ml_signal}/{ml_confidence:.0f}%, Tech={technical_score:.2f}")
                return self._create_analysis(
                    symbol, trading_symbol, False, ml_confidence, "HOLD", current_price, 0, 0, 0,
                    f"ML:{ml_signal}/Tech:{technical_score:.2f}", momentum_score, current_price
                )
            
            target, sl = self._calculate_targets(df, current_price)
            position_size = self._calculate_position_size(current_price, sl, available_cash)
            
            if position_size < 1:
                return self._create_analysis(
                    symbol, trading_symbol, False, ml_confidence, "HOLD", current_price, target, sl, position_size,
                    "Position size too small", momentum_score, current_price
                )
            
            logger.info(f"{symbol} ({trading_symbol}): QUALIFIES -{reason} | Price=₹{current_price:.2f} | Qty={position_size}")
            
            return self._create_analysis(
                symbol, trading_symbol, True, ml_confidence, "BUY", current_price, target, sl, position_size,
                reason, momentum_score, current_price
            )
            
        except Exception as e:
            logger.error(f"Analysis failed for {symbol}: {e}")
            return self._create_analysis(symbol, "", False, 0, "ERROR", 0, 0, 0, 0, str(e), 0, 0)

    async def analyze_batch(self, symbols: List[str], available_cash: float) -> List[StockAnalysis]:
        all_analysis = []
        for symbol in symbols:
            analysis = await self.analyze(symbol, available_cash)
            all_analysis.append(analysis)

        valid_analysis = [a for a in all_analysis if a.should_enter and a.position_size > 0]
        valid_analysis.sort(key=lambda x: x.momentum_score, reverse=True)
        
        top_count = min(3, len(valid_analysis))
        results = valid_analysis[:top_count]
        
        if not results:
            logger.info("Top stocks: No qualifying entries")
            return results
            
        logger.info(f"Top {top_count} Momentum Stocks:")
        for i, a in enumerate(results):
            logger.info(f"  {i+1}. {a.trading_symbol}: ML={a.signal} ({a.confidence:.0f}%) | Price=₹{a.current_price:.2f} | Qty={a.position_size}")

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

    async def _get_prediction(self, df: pd.DataFrame) -> Dict:
        if not self._model_loaded:
            return {"signal": "HOLD", "confidence": 0}

        try:
            features_df = self.feature_engineer.generate_features(df)
            features_df = features_df.dropna()

            if len(features_df) < 50:
                return {"signal": "HOLD", "confidence": 0}

            available_features = [f for f in self.model.feature_names if f in features_df.columns]
            if not available_features:
                return {"signal": "HOLD", "confidence": 0}

            X = features_df[available_features].tail(1).values
            prediction = self.model.predict(X)[0]
            probabilities = self.model.predict_proba(X)[0]

            signal_map = {-1: "SELL", 0: "HOLD", 1: "BUY"}
            signal = signal_map.get(int(prediction), "HOLD")
            confidence = float(max(probabilities)) * 100

            return {"signal": signal, "confidence": confidence}

        except Exception as e:
            logger.warning(f"Prediction failed: {e}")
            return {"signal": "HOLD", "confidence": 0}

    def _get_momentum_for_ranking(self, df: pd.DataFrame) -> float:
        if df.empty or len(df) < 50:
            return 0

        try:
            if not self._model_loaded:
                return self._calculate_technical_score(df)

            features_df = self.feature_engineer.generate_features(df)
            features_df = features_df.dropna()

            if len(features_df) < 20:
                return 0

            available_features = [f for f in self.model.feature_names if f in features_df.columns]
            if not available_features:
                return 0

            X = features_df[available_features].tail(1).values
            probabilities = self.model.predict_proba(X)

            if len(probabilities) == 0:
                return self._calculate_technical_score(df)

            prob_buy = float(probabilities[0][2]) if len(probabilities[0]) > 2 else 0

            return prob_buy

        except Exception as e:
            logger.debug(f"Momentum ranking failed: {e}")
            return 0

    def _calculate_momentum_score(self, df: pd.DataFrame) -> float:
        if df.empty or len(df) < 50:
            return 0

        try:
            features_df = self.feature_engineer.generate_features(df)
            features_df = features_df.dropna()

            if len(features_df) < 20:
                return 0

            if not self._model_loaded:
                return self._calculate_technical_score(df)

            try:
                available_features = [f for f in self.model.feature_names if f in features_df.columns]
                if not available_features:
                    return 0

                X = features_df[available_features].tail(1).values
                probabilities = self.model.predict_proba(X)

                if len(probabilities) == 0:
                    return self._calculate_technical_score(df)

                prob_buy = float(probabilities[0][2]) if len(probabilities[0]) > 2 else 0
                prob_hold = float(probabilities[0][1]) if len(probabilities[0]) > 1 else 0
                prob_sell = float(probabilities[0][0]) if len(probabilities[0]) > 0 else 0

                logger.debug(f"ML probs: SELL={prob_sell:.3f} HOLD={prob_hold:.3f} BUY={prob_buy:.3f}")

                if prob_buy > 0.1:
                    return prob_buy

                logger.debug("ML probability too low, using technical score")
                return self._calculate_technical_score(df)

            except Exception as e:
                logger.debug(f"ML prediction failed: {e}")
                return self._calculate_technical_score(df)

        except Exception as e:
            logger.debug(f"Momentum score calc failed: {e}")
            return 0

    def _calculate_technical_score(self, df: pd.DataFrame) -> float:
        if df.empty or len(df) < 20:
            return 0

        try:
            price_score = 0
            volume_score = 0
            trend_score = 0
            rsi_score = 0

            price_change_5d = ((df["close"].iloc[-1] - df["close"].iloc[-6]) / df["close"].iloc[-6]) * 100 if len(df) >= 6 else 0
            price_change_10d = ((df["close"].iloc[-1] - df["close"].iloc[-11]) / df["close"].iloc[-11]) * 100 if len(df) >= 11 else 0
            price_score = min(30, max(0, price_change_10d * 3))

            if "volume_ratio" in df.columns:
                vol_ratio = float(df["volume_ratio"].iloc[-1]) if not pd.isna(df["volume_ratio"].iloc[-1]) else 0
                volume_score = min(20, vol_ratio * 10)

            if "ema_20" in df.columns and "ema_50" in df.columns:
                ema_20 = df["ema_20"].iloc[-1]
                ema_50 = df["ema_50"].iloc[-1]
                current_price = df["close"].iloc[-1]
                if not pd.isna(ema_20) and not pd.isna(ema_50):
                    if ema_20 > ema_50:
                        trend_score = 20
                        if current_price > ema_20:
                            trend_score += 10

            if "rsi_14" in df.columns:
                rsi = df["rsi_14"].iloc[-1]
                if not pd.isna(rsi):
                    if rsi < 30:
                        rsi_score = 30
                    elif rsi < 40:
                        rsi_score = 20
                    elif rsi < 60:
                        rsi_score = 25
                    elif rsi < 70:
                        rsi_score = 15
                    else:
                        rsi_score = 5

            total_score = (
                price_score * 0.4 +
                volume_score * 0.2 +
                trend_score * 0.2 +
                rsi_score * 0.2
            )

            return total_score / 100

        except Exception as e:
            logger.debug(f"Technical score calc failed: {e}")
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
        trading_symbol: str,
        should_enter: bool,
        confidence: float,
        signal: str,
        entry_price: float,
        target_price: float,
        stop_loss: float,
        position_size: int,
        reason: str,
        momentum_score: float = 0,
        current_price: float = 0,
    ) -> StockAnalysis:
        return StockAnalysis(
            symbol=symbol,
            trading_symbol=trading_symbol,
            should_enter=should_enter,
            confidence=confidence,
            signal=signal,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            position_size=position_size,
            reason=reason,
            momentum_score=momentum_score,
            current_price=current_price,
        )
