import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore")

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.callbacks import EarlyStopping
    from tensorflow.keras.optimizers import Adam
    HAS_TF = True
except ImportError:
    HAS_TF = False

from core.logging import logger


class LSTMPredictor:
    def __init__(self, sequence_length: int = 60, lookback_days: int = 60):
        self.sequence_length = sequence_length
        self.lookback_days = lookback_days
        self.model = None
        self.scaler_mean = None
        self.scaler_std = None
        self.is_trained = False
        
        if not HAS_TF:
            logger.warning("TensorFlow not available - LSTM disabled")
            return
        
        tf.get_logger().setLevel('ERROR')
    
    def _create_sequences(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        X, y = [], []
        for i in range(len(data) - self.sequence_length):
            X.append(data[i:(i + self.sequence_length)])
            y.append(data[i + self.sequence_length, 3])
        return np.array(X), np.array(y)
    
    def _normalize_data(self, data: np.ndarray) -> np.ndarray:
        self.scaler_mean = np.mean(data, axis=0)
        self.scaler_std = np.std(data, axis=0) + 1e-8
        return (data - self.scaler_mean) / self.scaler_std
    
    def _denormalize(self, data: np.ndarray) -> np.ndarray:
        return (data * self.scaler_std[3]) + self.scaler_mean[3]
    
    def train(self, df: pd.DataFrame, epochs: int = 50) -> bool:
        if not HAS_TF:
            logger.error("TensorFlow not available")
            return False
            
        try:
            if len(df) < self.sequence_length + 20:
                logger.warning(f"Insufficient data for LSTM ({len(df)} rows)")
                return False
            
            features = df[["open", "high", "low", "close", "volume"]].dropna().values
            if len(features) < self.sequence_length + 20:
                logger.warning("Insufficient clean data for LSTM")
                return False
            
            normalized = self._normalize_data(features)
            X, y = self._create_sequences(normalized)
            
            if len(X) < 50:
                logger.warning("Insufficient sequences for LSTM training")
                return False
            
            X = X.reshape((X.shape[0], X.shape[1], X.shape[2]))
            
            split = int(len(X) * 0.8)
            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]
            
            self.model = Sequential([
                LSTM(64, return_sequences=True, input_shape=(self.sequence_length, 5)),
                Dropout(0.2),
                LSTM(32, return_sequences=False),
                Dropout(0.2),
                Dense(16, activation='relu'),
                Dense(1, activation='linear')
            ])
            
            self.model.compile(
                optimizer=Adam(learning_rate=0.001),
                loss='mse',
                metrics=['mae']
            )
            
            early_stop = EarlyStopping(
                monitor='val_loss',
                patience=10,
                restore_best_weights=True
            )
            
            self.model.fit(
                X_train, y_train,
                epochs=epochs,
                batch_size=32,
                validation_split=0.2,
                callbacks=[early_stop],
                verbose=0
            )
            
            test_loss = self.model.evaluate(X_test, y_test, verbose=0)
            logger.info(f"LSTM test loss: {test_loss[0]:.4f}")
            
            self.is_trained = True
            return True
            
        except Exception as e:
            logger.error(f"LSTM training failed: {e}")
            return False
    
    def predict(self, df: pd.DataFrame, days_ahead: int = 1) -> Dict:
        if not HAS_TF or not self.is_trained or self.model is None:
            return {"signal": "HOLD", "confidence": 0, "prediction": 0}
        
        try:
            features = df[["open", "high", "low", "close", "volume"]].tail(self.sequence_length).dropna().values
            if len(features) < self.sequence_length:
                return {"signal": "HOLD", "confidence": 0}
            
            normalized = (features - self.scaler_mean) / self.scaler_std
            X = normalized.reshape(1, self.sequence_length, 5)
            
            prediction = self.model.predict(X, verbose=0)[0, 0]
            predicted_price = self._denormalize(np.array([[[0, 0, 0, prediction, 0]]]))[0, 3]
            
            current_price = float(df["close"].iloc[-1])
            change_pct = ((predicted_price - current_price) / current_price) * 100
            
            signal = "HOLD"
            if change_pct > 2:
                signal = "BUY"
            elif change_pct < -2:
                signal = "SELL"
            
            confidence = min(abs(change_pct) * 10, 100)
            
            return {
                "signal": signal,
                "confidence": confidence,
                "prediction": predicted_price,
                "current_price": current_price,
                "change_pct": change_pct
            }
            
        except Exception as e:
            logger.debug(f"LSTM prediction failed: {e}")
            return {"signal": "HOLD", "confidence": 0}
    
    def predict_price_direction(self, df: pd.DataFrame) -> str:
        result = self.predict(df)
        return result.get("signal", "HOLD")


lstm_predictor = LSTMPredictor()


def get_lstm_predictor() -> LSTMPredictor:
    return lstm_predictor