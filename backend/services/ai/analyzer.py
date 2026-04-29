from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List
import warnings
import pandas as pd
from datetime import timedelta

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

from services.broker.kite import KiteBroker
from services.ai.features import FeatureEngineer
from services.ai.model import ModelTrainer
from services.ai.adaptive_model import AdaptiveModel
from services.ai.strategy_optimizer import StrategyOptimizer
from core.config import get_settings, get_strategy_target
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


class StockAnalyzer:
    def __init__(self, broker: KiteBroker, model_path: Optional[str] = None):
        self.broker = broker
        self.settings = get_settings()
        self.feature_engineer = FeatureEngineer()
        self.model = ModelTrainer(
            target_return=self.settings.target_profit_pct / 100,
            stop_loss=self.settings.stop_loss_pct / 100,
        )
        self.adaptive = AdaptiveModel(
            target_return=self.settings.target_profit_pct / 100,
            stop_loss=self.settings.stop_loss_pct / 100,
        )
        self.optimizer = StrategyOptimizer()
        self._model_loaded = False
        self._adaptive_loaded = False
        self.min_momentum_score = self.settings.min_momentum_score
        self.lookback_days = 60
        self.interval = "60minute"

        if model_path:
            self.load_model(model_path)

    def load_model(self, model_path: str) -> bool:
        try:
            if self.model.load_model(model_path):
                self._model_loaded = True
            
            if self.adaptive.load_model(model_path):
                self._adaptive_loaded = True
                perf = self.adaptive.get_performance_summary()
                logger.debug(f"Adaptive model loaded with {perf.get('trade_count', 0)} trades")
            
            return self._model_loaded or self._adaptive_loaded
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
            
            await self._fetch_nifty_and_update(df)
            
            current_price = float(df["close"].iloc[-1])
            technical_score = self._calculate_technical_score(df)
            
            strategy_scores = self.calculate_strategy_scores(df)
            best_strategy, strategy_score = self.get_best_strategy(strategy_scores)
            
            logger.debug(f"{symbol}: Strategy scores: {strategy_scores}, best={best_strategy}/{strategy_score:.2f}")
            
            ml_signal = "HOLD"
            ml_confidence = 0
            adaptive_result = None
            
            if self._adaptive_loaded and self.adaptive.is_trained():
                try:
                    adaptive_result = self.adaptive.predict_advanced(df, best_strategy)
                    ml_signal = adaptive_result.get("signal", "HOLD")
                    ml_confidence = adaptive_result.get("confidence", 0)
                    detected_strategy = adaptive_result.get("strategy", best_strategy)
                except Exception as e:
                    logger.debug(f"Adaptive prediction failed: {e}")
            
            if not adaptive_result and self._model_loaded:
                try:
                    prediction = await self._get_prediction(df)
                    ml_signal = prediction.get("signal", "HOLD")
                    ml_confidence = prediction.get("confidence", 0)
                except:
                    pass
            
            momentum_score = self._get_momentum_for_ranking(df) if self._model_loaded else technical_score
            
            detected_strategy = best_strategy
            
            should_enter = False
            reason = ""
            
            strategy_config = get_strategy_target(detected_strategy)
            target_pct = strategy_config["target"]
            stop_pct = strategy_config["stop_loss"]
            min_score = strategy_config["min_score"]
            
            if ml_signal == "BUY":
                should_enter = True
                reason = f"ML: BUY ({ml_confidence:.0f}%)"
            elif strategy_score >= 0.25:
                should_enter = True
                reason = f"Strategy: {detected_strategy} ({strategy_score:.0%})"
                ml_confidence = max(ml_confidence, strategy_score * 100)
            elif technical_score >= 0.2:
                should_enter = True
                reason = f"Technical: score={technical_score:.2f}"
                ml_confidence = technical_score * 100
                detected_strategy = "technical_fallback"
                strategy_config = get_strategy_target("trend_pullback")
                target_pct = 0.20
                stop_pct = 0.03
            elif momentum_score >= 0.3:
                should_enter = True
                reason = f"Momentum: {momentum_score:.2f}"
                ml_confidence = momentum_score * 100
                detected_strategy = "momentum_play"
                strategy_config = get_strategy_target("trend_pullback")
                target_pct = 0.20
                stop_pct = 0.03
            
            entry_price = current_price
            target_price = current_price * (1 + target_pct)
            stop_loss = current_price * (1 - stop_pct)
            risk_reward = target_pct / stop_pct
            optimal_entry_pct = 0.0
            
            if adaptive_result:
                entry_price = adaptive_result.get("entry_price", current_price)
                target_price = adaptive_result.get("target_price", target_price)
                stop_loss = adaptive_result.get("stop_loss", stop_loss)
                risk_reward = adaptive_result.get("risk_reward", risk_reward)
                optimal_entry_pct = adaptive_result.get("optimal_entry", 0.0)
            
            if not should_enter:
                logger.info(f"{symbol}: SKIP - Strategy:{detected_strategy}/{strategy_score:.0%}, Tech:{technical_score:.2f}, Momentum:{momentum_score:.2f}")
                return self._create_analysis(
                    symbol, trading_symbol, False, ml_confidence, "HOLD", current_price, 0, 0, 0,
                    f"Strategy:{detected_strategy}/{strategy_score:.0%}", momentum_score, current_price
                )
            
            position_size = self._calculate_position_size(entry_price, stop_loss, available_cash)
            
            if position_size < 1:
                return self._create_analysis(
                    symbol, trading_symbol, False, ml_confidence, "HOLD", entry_price, target_price, stop_loss, position_size,
                    "Position size too small", momentum_score, current_price
                )
            
            logger.info(f"{symbol} ({trading_symbol}): QUALIFIES -{reason} | Entry=₹{entry_price:.2f} | Target=₹{target_price:.2f} | SL=₹{stop_loss:.2f} | Qty={position_size} | Strategy={detected_strategy}")
            
            return self._create_analysis(
                symbol, trading_symbol, True, ml_confidence, "BUY", entry_price, target_price, stop_loss, position_size,
                reason, momentum_score, current_price, risk_reward, optimal_entry_pct, detected_strategy
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

            if total_score < 0.01:
                logger.warning(f"Tech score near zero - price:{price_score}, vol:{volume_score}, trend:{trend_score}, rsi:{rsi_score}")
            
            return total_score / 100

        except Exception as e:
            logger.error(f"Technical score calc failed: {e}")
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

    async def _fetch_nifty_and_update(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fetch NIFTY data and set in feature engineer for relative strength"""
        try:
            from datetime import timedelta
            to_date = datetime.utcnow()
            from_date = to_date - timedelta(days=60)
            nifty_data = self.broker.get_nifty_data(from_date, to_date, "60minute")
            if nifty_data:
                nifty_df = pd.DataFrame(nifty_data)
                if "date" in nifty_df.columns:
                    nifty_df["timestamp"] = pd.to_datetime(nifty_df["date"])
                    nifty_df.set_index("timestamp", inplace=True)
                self.feature_engineer.set_nifty_data(nifty_df)
                logger.debug(f"Updated feature engineer with NIFTY data")
        except Exception as e:
            logger.debug(f"NIFTY fetch error: {e}")

    def calculate_strategy_scores(self, df: pd.DataFrame) -> dict:
        """Calculate scores for each strategy - returns dict of strategy_name: score"""
        if df.empty or len(df) < 20:
            logger.warning(f"Strategy: insufficient data ({len(df)} rows)")
            return {"default": 0.5}

        scores = {}
        
        try:
            features_df = self.feature_engineer.generate_features(df.copy())
            
            if features_df.empty:
                logger.warning(f"Strategy: feature generation returned empty, using default")
                return {"default": 0.5}
            
            if "ema_20_above_50" in features_df.columns:
                score = 0
                if features_df["ema_20_above_50"].iloc[-1] == 1:
                    score += 0.4
                pullback = features_df["pullback_pct"].iloc[-1] if "pullback_pct" in features_df.columns else 0
                if -0.08 < pullback < 0.05:
                    score += 0.3
                support_dist = features_df["support_distance"].iloc[-1] if "support_distance" in features_df.columns else 1
                if support_dist < 0.05:
                    score += 0.2
                trend = features_df["trend_strength"].iloc[-1] if "trend_strength" in features_df.columns else 0
                if trend > -0.01:
                    score += 0.1
                scores["trend_pullback"] = min(score, 1.0)

            if "breakout_volume" in features_df.columns:
                score = 0
                bv = features_df["breakout_volume"].iloc[-1]
                if bv > 1.5:
                    score += 0.4
                elif bv > 1.2:
                    score += 0.2
                rh = features_df["retest_holds"].iloc[-1] if "retest_holds" in features_df.columns else 0
                if rh == 1:
                    score += 0.4
                rd = features_df["resistance_distance"].iloc[-1] if "resistance_distance" in features_df.columns else 1
                if rd < 0.02:
                    score += 0.2
                scores["breakout_retest"] = min(score, 1.0)

            if "stage" in features_df.columns:
                stage = features_df["stage"].iloc[-1]
                if stage == 2:
                    score = 0.8
                elif stage == 1:
                    score = 0.4
                else:
                    score = 0.1
                scores["stage_2"] = score

            if "vs_nifty_return" in features_df.columns:
                score = 0
                vs_nifty = features_df["vs_nifty_return"].iloc[-1]
                if vs_nifty > 0:
                    score += 0.5
                if vs_nifty > 0.05:
                    score += 0.3
                rs = features_df["relative_strength"].iloc[-1] if "relative_strength" in features_df.columns else 0
                if rs == 1:
                    score += 0.2
                scores["relative_strength"] = min(score, 1.0)

            if "vcp_signal" in features_df.columns:
                score = 0
                vcp = features_df["vcp_signal"].iloc[-1]
                if vcp == 1:
                    score = 0.7
                else:
                    rc = features_df["range_contraction"].iloc[-1] if "range_contraction" in features_df.columns else 1
                    if rc < 0.5:
                        score = 0.4
                scores["vcp"] = score

            if "reversal_candle" in features_df.columns:
                score = 0
                ns = features_df["near_support"].iloc[-1] if "near_support" in features_df.columns else 0
                if ns == 1:
                    score += 0.3
                rc = features_df["reversal_candle"].iloc[-1]
                if rc == 1:
                    score += 0.7
                scores["support_zone"] = min(score, 1.0)

            if "weekly_trend" in features_df.columns:
                score = 0
                wt = features_df["weekly_trend"].iloc[-1]
                if wt == 1:
                    score += 0.5
                dwa = features_df["daily_weekly_aligned"].iloc[-1] if "daily_weekly_aligned" in features_df.columns else 0
                if dwa == 1:
                    score += 0.5
                scores["multi_timeframe"] = score

        except Exception as e:
            logger.debug(f"Strategy scoring error: {e}")

        return scores

    def get_best_strategy(self, scores: dict) -> tuple:
        """Return (strategy_name, score)"""
        if not scores:
            return "trend_pullback", 0.0
        best = max(scores.items(), key=lambda x: x[1])
        return best[0], best[1]

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
        """
        Calculate position size based on available cash and stock price.
        Quantity is determined by available cash divided by entry price.
        """
        try:
            if cash <= 0 or entry_price <= 0:
                return 0
            
            position_size = int(cash / entry_price)
            
            return max(position_size, 0)

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
        risk_reward: float = 0,
        optimal_entry_pct: float = 0,
        strategy: str = "",
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
            risk_reward=risk_reward,
            optimal_entry_pct=optimal_entry_pct,
            strategy=strategy,
        )
