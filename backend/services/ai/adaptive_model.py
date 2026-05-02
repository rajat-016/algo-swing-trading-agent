import numpy as np
import pandas as pd
from typing import Tuple, Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import deque
import pickle
import os

from core.logging import logger
from core.config import get_settings, get_strategy_target
from services.ai.features import FeatureEngineer


class AdaptiveModel:
    """
    Enhanced ML model with adaptive learning from trade history.
    
    Features:
    - Learns from past trades in DB
    - Adaptive entry/exit based on volatility
    - Dynamic risk management
    - Performance tracking
    """

    def __init__(
        self,
        target_return: float = 0.10,
        stop_loss: float = 0.03,
    ):
        self.target_return = target_return
        self.stop_loss = stop_loss
        self.settings = get_settings()
        self.feature_engineer = FeatureEngineer()
        self.model = None
        self.scaler = None
        self.feature_names: List[str] = []
        self._is_trained = False
        self._trade_history: List[Dict] = []
        self._performance_metrics: Dict[str, float] = {}
        self._volatility_cache: Dict[str, float] = {}
        self._recent_predictions: deque = deque(maxlen=100)
        self._lookback = 60
        self._lookahead = 5
        self._cross_val_scores: Dict[str, float] = {}
        self.imputer = None

    def prepare_data(
        self,
        df: pd.DataFrame,
        additional_dfs: Optional[List[pd.DataFrame]] = None,
    ) -> Tuple:
        """Prepare data with features and labels (handles multi-class)."""
        from sklearn.preprocessing import StandardScaler
        from sklearn.impute import SimpleImputer

        features_df = self.feature_engineer.generate_features(df.copy())

        features_df = self._create_labels(features_df)
        
        if additional_dfs:
            for add_df in additional_dfs:
                add_features = self.feature_engineer.generate_features(add_df.copy())
                add_features = self._create_labels(add_features)
                features_df = pd.concat([features_df, add_features], ignore_index=True)

        features_df = features_df.replace([np.inf, -np.inf], np.nan)

        numeric_cols = features_df.select_dtypes(include=[np.number]).columns
        features_df = features_df[numeric_cols].dropna(thresh=int(len(numeric_cols) * 0.3), axis=1)
        features_df = features_df.dropna(thresh=5)

        if len(features_df) < 10:
            logger.warning(f"Very few samples: {len(features_df)}, using minimal dropna")
            features_df = df.copy()
            for col in df.columns:
                if df[col].dtype in [np.float64, np.int64]:
                    features_df[col] = df[col].fillna(method='ffill').fillna(method='bfill')

        if features_df.empty:
            raise ValueError("No valid data after feature generation")

        available_features = self.feature_engineer.get_feature_names()
        available_features = [f for f in available_features if f in features_df.columns]
        
        for col in ["signal", "future_return", "atr_14", "rsi_14", "volume_ratio"]:
            if col in features_df.columns and col not in available_features:
                available_features.append(col)

        available_features = [f for f in available_features if f in features_df.columns]
        if not available_features:
            available_features = [col for col in features_df.columns if col not in ['signal', 'future_return', 'adaptive_target', 'adaptive_stop']]
        
        available_features = list(set(available_features))
        available_features.sort()

        X = features_df[available_features].values
        y = features_df["signal"].values

        self.feature_names = available_features

        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        self.imputer = SimpleImputer(strategy='median')
        X_train = self.imputer.fit_transform(X_train)
        X_test = self.imputer.transform(X_test)

        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        return X_train_scaled, X_test_scaled, y_train, y_test

    def _create_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create labels based on future returns with dynamic thresholds and confidence levels."""
        if "close" not in df.columns:
            return df

        df = df.copy()
        df["future_return"] = df["close"].shift(-self._lookahead) / df["close"] - 1

        atr = df["atr_14"].iloc[-1] if "atr_14" in df.columns else df["close"].iloc[-1] * 0.02
        atr_pct = atr / df["close"].iloc[-1]

        adaptive_target = max(self.target_return, atr_pct * 3)
        adaptive_stop = max(self.stop_loss, atr_pct * 1.5)

        strong_target = adaptive_target * 1.5
        strong_stop = adaptive_stop * 1.5

        labels = pd.Series(0, index=df.index)
        labels[df["future_return"] > strong_target] = 2
        labels[(df["future_return"] > adaptive_target) & (df["future_return"] <= strong_target)] = 1
        labels[(df["future_return"] < -strong_stop)] = -2
        labels[(df["future_return"] < -adaptive_stop) & (df["future_return"] >= -strong_stop)] = -1

        df["signal"] = labels
        df["signal_strong"] = (labels == 2).astype(int)
        df["signal_weak"] = (labels == 1).astype(int)
        df["adaptive_target"] = adaptive_target
        df["adaptive_stop"] = adaptive_stop

        return df

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        use_trade_history: bool = True,
    ) -> bool:
        """Train ensemble model with option to include trade history."""
        from sklearn.ensemble import (
            GradientBoostingClassifier,
            RandomForestClassifier,
            VotingClassifier,
            HistGradientBoostingClassifier,
        )
        from sklearn.linear_model import LogisticRegression
        from sklearn.neural_network import MLPClassifier
        from sklearn.impute import SimpleImputer
        
        try:
            from xgboost import XGBClassifier
            has_xgboost = True
        except ImportError:
            has_xgboost = False
            logger.warning("XGBoost not available, using sklearn ensemble")

        X_train = np.asarray(X_train, dtype=np.float64)
        y_train = np.asarray(y_train, dtype=np.int32)

        nan_mask = np.isnan(X_train) | np.isinf(X_train)
        if nan_mask.any():
            imputer = SimpleImputer(strategy='median')
            X_train = imputer.fit_transform(X_train)

        try:
            if use_trade_history and self._trade_history:
                X_augmented, y_augmented = self._augment_with_trade_history()
                if len(X_augmented) > 0:
                    X_train = np.vstack([X_train, X_augmented])
                    y_train = np.concatenate([y_train, y_augmented])
                    logger.info(f"Augmented training with {len(X_augmented)} trade samples")

            unique_labels = np.unique(y_train)
            if len(unique_labels) < 2:
                logger.warning("Only one class in training data, using single model")
                self.model = HistGradientBoostingClassifier(
                    max_iter=100,
                    learning_rate=0.1,
                    max_depth=5,
                    random_state=42,
                )
                self.model.fit(X_train, y_train)
                self._is_trained = True
                self._update_performance_metrics()
                logger.info("Model trained successfully (single class)")
                return True

            gb_model = GradientBoostingClassifier(
                n_estimators=150,
                learning_rate=0.08,
                max_depth=6,
                min_samples_split=10,
                min_samples_leaf=5,
                subsample=0.8,
                random_state=42,
            )

            rf_model = RandomForestClassifier(
                n_estimators=100,
                max_depth=8,
                min_samples_split=10,
                min_samples_leaf=5,
                random_state=42,
                n_jobs=-1,
            )

            lr_model = LogisticRegression(
                C=1.0,
                max_iter=1000,
                random_state=42,
                solver='lbfgs',
            )

            mlp_model = MLPClassifier(
                hidden_layer_sizes=(64, 32),
                activation="relu",
                solver="adam",
                alpha=0.01,
                max_iter=500,
                random_state=42,
                early_stopping=True,
                validation_fraction=0.1,
            )
            
            estimators = [
                ("gb", gb_model),
                ("rf", rf_model),
                ("lr", lr_model),
                ("mlp", mlp_model),
            ]
            
            if has_xgboost:
                xgb_model = XGBClassifier(
                    n_estimators=150,
                    learning_rate=0.08,
                    max_depth=6,
                    min_child_weight=5,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    random_state=42,
                    use_label_encoder=False,
                    eval_metric="logloss",
                    verbosity=0,
                )
                estimators.insert(0, ("xgb", xgb_model))
                logger.info("Using XGBoost + sklearn ensemble")
            
            self.model = VotingClassifier(
                estimators=estimators,
                voting="soft",
                n_jobs=-1,
            )

            self.model.fit(X_train, y_train)
            self._is_trained = True
            self._update_performance_metrics()
            logger.info("Ensemble model trained successfully")

            if hasattr(self.model, "named_estimators_"):
                for name, estimator in self.model.named_estimators_.items():
                    if hasattr(estimator, "feature_importances_"):
                        importances = estimator.feature_importances_
                        if len(importances) > 0 and len(self.feature_names) > 0:
                            top_idx = np.argsort(importances)[-5:][::-1]
                            top_features = [self.feature_names[i] for i in top_idx]
                            logger.debug(f"{name} top features: {top_features}")

            return True

        except Exception as e:
            logger.error(f"Model training failed - {e}")
            try:
                logger.warning("Falling back to HistGradientBoostingClassifier (handles NaN)")
                self.model = HistGradientBoostingClassifier(
                    max_iter=100,
                    learning_rate=0.1,
                    max_depth=5,
                    random_state=42,
                )
                self.model.fit(X_train, y_train)
                self._is_trained = True
                self._update_performance_metrics()
                logger.info("Fallback model trained successfully")
                return True
            except Exception as fallback_error:
                logger.error(f"Fallback model also failed: {fallback_error}")
                return False

    def time_series_cross_validate(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_splits: int = 5,
    ) -> Dict[str, Any]:
        """Perform time-series cross-validation (no data leakage)."""
        from sklearn.model_selection import TimeSeriesSplit
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

        if len(X) < n_splits * 20:
            logger.warning("Insufficient data for cross-validation")
            return {"error": "Insufficient data"}

        try:
            tscv = TimeSeriesSplit(n_splits=n_splits)
            fold_scores = []

            for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
                X_train_fold, X_val_fold = X[train_idx], X[val_idx]
                y_train_fold, y_val_fold = y[train_idx], y[val_idx]

                if len(np.unique(y_train_fold)) < 2:
                    continue

                X_train_fold_scaled = self.scaler.fit_transform(X_train_fold)
                X_val_fold_scaled = self.scaler.transform(X_val_fold)

                from sklearn.ensemble import GradientBoostingClassifier

                fold_model = GradientBoostingClassifier(
                    n_estimators=100,
                    learning_rate=0.1,
                    max_depth=5,
                    random_state=42,
                )
                fold_model.fit(X_train_fold_scaled, y_train_fold)
                y_pred = fold_model.predict(X_val_fold_scaled)

                acc = accuracy_score(y_val_fold, y_pred)
                prec = precision_score(y_val_fold, y_pred, average="weighted", zero_division=0)
                rec = recall_score(y_val_fold, y_pred, average="weighted", zero_division=0)
                f1 = f1_score(y_val_fold, y_pred, average="weighted", zero_division=0)

                fold_scores.append({
                    "fold": fold + 1,
                    "accuracy": acc,
                    "precision": prec,
                    "recall": rec,
                    "f1": f1,
                    "train_size": len(train_idx),
                    "val_size": len(val_idx),
                })

                logger.debug(
                    f"Fold {fold + 1}: Acc={acc:.3f}, Prec={prec:.3f}, "
                    f"Rec={rec:.3f}, F1={f1:.3f}"
                )

            if fold_scores:
                self._cross_val_scores = {
                    "accuracy": np.mean([s["accuracy"] for s in fold_scores]),
                    "precision": np.mean([s["precision"] for s in fold_scores]),
                    "recall": np.mean([s["recall"] for s in fold_scores]),
                    "f1": np.mean([s["f1"] for s in fold_scores]),
                    "std_accuracy": np.std([s["accuracy"] for s in fold_scores]),
                    "folds": fold_scores,
                }
                logger.info(
                    f"Cross-validation: Acc={self._cross_val_scores['accuracy']:.3f} "
                    f"+/- {self._cross_val_scores['std_accuracy']:.3f}"
                )

            return self._cross_val_scores

        except Exception as e:
            logger.error(f"Cross-validation failed: {e}")
            return {"error": str(e)}

    def get_feature_importance(self) -> Dict[str, np.ndarray]:
        """Get feature importance from all models in ensemble."""
        if not self._is_trained or not self.model:
            return {}

        try:
            importances = {}

            if hasattr(self.model, "named_estimators_"):
                for name, estimator in self.model.named_estimators_.items():
                    if hasattr(estimator, "feature_importances_"):
                        importances[name] = estimator.feature_importances_
                    elif hasattr(estimator, "coef_"):
                        importances[name] = np.abs(estimator.coef_)

            return importances

        except Exception as e:
            logger.debug(f"Feature importance extraction failed: {e}")
            return {}

    def _augment_with_trade_history(self) -> Tuple[np.ndarray, np.ndarray]:
        """Create training samples from historical trades."""
        X_samples = []
        y_samples = []

        for trade in self._trade_history:
            if "features" in trade and "outcome" in trade:
                try:
                    features = np.array(trade["features"])
                    if len(features) == len(self.feature_names):
                        X_samples.append(features)
                        y_samples.append(1 if trade["outcome"] == "profit" else -1)
                except:
                    pass

        if X_samples:
            return np.array(X_samples), np.array(y_samples)
        return np.array([]), np.array([])

    def add_trade_to_history(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        features: Dict[str, float],
        exit_reason: str,
    ) -> None:
        """Add completed trade to learning history."""
        outcome = "profit" if exit_price > entry_price else "loss"
        pnl_pct = (exit_price - entry_price) / entry_price * 100

        trade = {
            "symbol": symbol,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl_pct": pnl_pct,
            "exit_reason": exit_reason,
            "outcome": outcome,
            "features": features,
            "timestamp": datetime.now().isoformat(),
        }

        self._trade_history.append(trade)

        if len(self._trade_history) > 1000:
            self._trade_history = self._trade_history[-1000:]

        self._update_performance_metrics()
        logger.debug(f"Trade added to history: {symbol} {outcome} {pnl_pct:.2f}%")

    def _update_performance_metrics(self) -> None:
        """Calculate performance metrics from trade history."""
        if not self._trade_history:
            return

        trades = self._trade_history[-100:]
        wins = [t for t in trades if t["outcome"] == "profit"]
        losses = [t for t in trades if t["outcome"] == "loss"]

        total_pnl = sum(t["pnl_pct"] for t in trades)
        win_rate = len(wins) / len(trades) * 100 if trades else 0
        avg_win = np.mean([t["pnl_pct"] for t in wins]) if wins else 0
        avg_loss = abs(np.mean([t["pnl_pct"] for t in losses])) if losses else 0

        self._performance_metrics = {
            "total_trades": len(trades),
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": avg_win / avg_loss if avg_loss > 0 else 0,
            "total_pnl": total_pnl,
            "sharpe_like": (avg_win * win_rate - avg_loss * (100 - win_rate)) / 100 if win_rate > 0 else 0,
        }

        logger.info(
            f"Performance: WR={win_rate:.1f}% | PF={self._performance_metrics['profit_factor']:.2f} | "
            f"AvgW={avg_win:.2f}% | AvgL={avg_loss:.2f}%"
        )

    def predict_advanced(
        self,
        df: pd.DataFrame,
        strategy_name: str = None,
    ) -> Dict[str, Any]:
        """
        Advanced prediction with adaptive entry/exit levels.
        
        Args:
            df: Price data
            strategy_name: Optional strategy name to use, otherwise auto-detect best strategy
            
        Returns:
            dict with signal, confidence, entry_price, target, stop_loss, risk_reward, strategy
        """
        if not self._is_trained or df.empty:
            return self._get_default_prediction(df)

        current_price = float(df["close"].iloc[-1])

        strategy = strategy_name if strategy_name else self._detect_best_strategy(df)
        strategy_config = get_strategy_target(strategy)
        
        target_return = strategy_config["target"]
        stop_loss_pct = strategy_config["stop_loss"]

        try:
            features_df = self.feature_engineer.generate_features(df.copy())
            features_df = features_df.dropna()
            
            if features_df.empty:
                return self._get_default_prediction(df)

            available_features = [f for f in self.feature_names if f in features_df.columns]

            X = features_df[available_features].values[-1:]
            X_scaled = self.scaler.transform(X)

            prediction = self.model.predict(X_scaled)[0]
            probabilities = self.model.predict_proba(X_scaled)[0]

            confidence = max(probabilities) * 100 if len(probabilities) > 0 else 50

            entry_price = current_price

            atr = self._calculate_adaptive_atr(df)
            atr_pct = atr / current_price

            volatility_multiplier = self._get_volatility_multiplier(df)

            target_return = target_return * volatility_multiplier
            stop_loss_pct = stop_loss_pct / volatility_multiplier

            target_price = entry_price * (1 + target_return)
            stop_loss = entry_price * (1 - stop_loss_pct)

            risk_reward = target_return / stop_loss_pct if stop_loss_pct > 0 else 1

            optimal_entry_buffer = self._get_entry_buffer(df)
            adjusted_entry = entry_price * (1 + optimal_entry_buffer)
            target_price = adjusted_entry * (1 + target_return)
            stop_loss = adjusted_entry * (1 - stop_loss_pct)

            self._recent_predictions.append({
                "symbol": df.get("symbol", ["UNKNOWN"])[0] if hasattr(df.get("symbol"), "__iter__") else "UNKNOWN",
                "signal": prediction,
                "confidence": confidence,
                "entry": adjusted_entry,
                "target": target_price,
                "stop": stop_loss,
                "timestamp": datetime.now(),
            })

            return {
                "signal": "BUY" if prediction == 1 else ("SELL" if prediction == -1 else "HOLD"),
                "confidence": confidence,
                "entry_price": adjusted_entry,
                "target_price": target_price,
                "stop_loss": stop_loss,
                "risk_reward": risk_reward,
                "atr_pct": atr_pct * 100,
                "volatility": volatility_multiplier,
                "optimal_entry": optimal_entry_buffer * 100,
                "strategy": strategy,
                "strategy_target": target_return * 100,
                "strategy_stop": stop_loss_pct * 100,
            }

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return self._get_default_prediction(df)

    def _detect_best_strategy(self, df: pd.DataFrame) -> str:
        """Auto-detect best strategy based on current price action"""
        scores = {}
        
        try:
            features_df = df.copy()
            
            if "ema_20_above_50" in features_df.columns and "pullback_pct" in features_df.columns:
                pullback_score = 0
                if features_df["ema_20_above_50"].iloc[-1] == 1:
                    pullback_score += 0.4
                if -0.02 < features_df["pullback_pct"].iloc[-1] < 0:
                    pullback_score += 0.3
                if features_df["support_distance"].iloc[-1] < 0.03:
                    pullback_score += 0.3
                scores["trend_pullback"] = pullback_score
            
            if "breakout_volume" in features_df.columns and "retest_holds" in features_df.columns:
                breakout_score = 0
                if features_df["breakout_volume"].iloc[-1] > 1.5:
                    breakout_score += 0.4
                if features_df["retest_holds"].iloc[-1] == 1:
                    breakout_score += 0.4
                if features_df["resistance_distance"].iloc[-1] < 0.02:
                    breakout_score += 0.2
                scores["breakout_retest"] = breakout_score
            
            if "stage" in features_df.columns:
                stage_score = 0
                stage_val = features_df["stage"].iloc[-1]
                if stage_val == 2:
                    stage_score = 0.7
                elif stage_val == 1:
                    stage_score = 0.3
                scores["stage_2"] = stage_score
            
            if "vs_nifty_return" in features_df.columns and "relative_strength" in features_df.columns:
                rs_score = 0
                if features_df["vs_nifty_return"].iloc[-1] > 0:
                    rs_score += 0.5
                if features_df["relative_strength"].iloc[-1] == 1:
                    rs_score += 0.3
                scores["relative_strength"] = rs_score
            
            if "vcp_signal" in features_df.columns:
                vcp_score = 0
                if features_df["vcp_signal"].iloc[-1] == 1:
                    vcp_score = 0.7
                elif features_df["range_contraction"].iloc[-1] < 0.5 if "range_contraction" in features_df.columns else False:
                    vcp_score = 0.4
                scores["vcp"] = vcp_score
            
            if "near_support" in features_df.columns and "reversal_candle" in features_df.columns:
                support_score = 0
                if features_df["near_support"].iloc[-1] == 1:
                    support_score += 0.4
                if features_df["reversal_candle"].iloc[-1] == 1:
                    support_score += 0.6
                scores["support_zone"] = support_score
            
            if "weekly_trend" in features_df.columns and "daily_weekly_aligned" in features_df.columns:
                mtf_score = 0
                if features_df["weekly_trend"].iloc[-1] == 1:
                    mtf_score += 0.5
                if features_df["daily_weekly_aligned"].iloc[-1] == 1:
                    mtf_score += 0.5
                scores["multi_timeframe"] = mtf_score
            
            if scores:
                best = max(scores.items(), key=lambda x: x[1])
                if best[1] > 0.3:
                    return best[0]
        
        except Exception as e:
            logger.debug(f"Strategy detection error: {e}")
        
        return "trend_pullback"

    def _calculate_adaptive_atr(self, df: pd.DataFrame) -> float:
        """Calculate adaptive ATR based on recent volatility."""
        if "atr_14" in df.columns and not df["atr_14"].iloc[-1:].isna().any():
            return float(df["atr_14"].iloc[-1])
        return float(df["close"].iloc[-1] * 0.02)

    def _get_volatility_multiplier(self, df: pd.DataFrame) -> float:
        """Get volatility multiplier (higher vol = tighter targets)."""
        if len(df) < 20:
            return 1.0

        recent_std = df["close"].pct_change().tail(20).std()
        avg_std = df["close"].pct_change().tail(60).std()

        if avg_std > 0:
            vol_ratio = recent_std / avg_std
            return max(0.5, min(1.5, 1 / vol_ratio))

        return 1.0

    def _get_entry_buffer(self, df: pd.DataFrame) -> float:
        """Determine if entry should be at market or with buffer."""
        if "rsi_14" not in df.columns:
            return 0.0

        rsi = float(df["rsi_14"].iloc[-1])

        if rsi < 35:
            return -0.005
        elif rsi < 45:
            return -0.002
        elif rsi > 65:
            return 0.005
        elif rsi > 55:
            return 0.002
        return 0.0

    def _get_default_prediction(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get default prediction when model unavailable."""
        current_price = float(df["close"].iloc[-1]) if not df.empty else 0

        return {
            "signal": "HOLD",
            "confidence": 0,
            "entry_price": current_price,
            "target_price": current_price * (1 + self.target_return),
            "stop_loss": current_price * (1 - self.stop_loss),
            "risk_reward": self.target_return / self.stop_loss,
            "atr_pct": 2.0,
            "volatility": 1.0,
            "optimal_entry": 0.0,
        }

    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> dict:
        """Evaluate model performance."""
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

        if not self.model:
            return {"accuracy": 0}

        y_pred = self.model.predict(X_test)

        return {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, average="weighted", zero_division=0),
            "recall": recall_score(y_test, y_pred, average="weighted", zero_division=0),
            "f1": f1_score(y_test, y_pred, average="weighted", zero_division=0),
            "performance": self._performance_metrics,
        }

    def save_model(self, path: str) -> bool:
        """Save model with trade history."""
        import joblib

        if not self.model:
            return False

        try:
            data = {
                "model": self.model,
                "scaler": self.scaler,
                "feature_names": self.feature_names,
                "trade_history": self._trade_history,
                "performance_metrics": self._performance_metrics,
                "target_return": self.target_return,
                "stop_loss": self.stop_loss,
                "trained_at": datetime.now().isoformat(),
            }

            os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
            joblib.dump(data, path)
            logger.info(f"Model saved to {path}")
            return True

        except Exception as e:
            logger.error(f"Model save failed - {e}")
            return False

    def load_model(self, path: str) -> bool:
        """Load model with trade history."""
        import joblib

        try:
            data = joblib.load(path)

            self.model = data["model"]
            self.scaler = data["scaler"]
            self.feature_names = data["feature_names"]
            self._trade_history = data.get("trade_history", [])
            self._performance_metrics = data.get("performance_metrics", {})
            self.target_return = data.get("target_return", self.target_return)
            self.stop_loss = data.get("stop_loss", self.stop_loss)
            self._is_trained = True

            model_type = type(self.model).__name__
            if hasattr(self.model, "estimators"):
                est_names = [f"{name}({type(est).__name__})" for name, est in self.model.estimators]
                logger.info(f"ML Model loaded: {model_type} [{', '.join(est_names)}]")
            else:
                logger.info(f"ML Model loaded: {model_type} ({type(self.model).__name__})")
            logger.info(f"  Features: {len(self.feature_names)} | Trained at: {data.get('trained_at', 'unknown')}")
            if self._performance_metrics:
                logger.info(f"  Performance: {self._performance_metrics}")

            return True

        except Exception as e:
            logger.error(f"Model load failed - {e}")
            return False

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        return {
            "metrics": self._performance_metrics,
            "trade_count": len(self._trade_history),
            "is_trained": self._is_trained,
            "model_ready": self.model is not None,
        }

    def is_trained(self) -> bool:
        return self._is_trained