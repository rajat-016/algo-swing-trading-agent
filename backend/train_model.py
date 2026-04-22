"""
Model training script.
Fetches data, creates features/labels, trains ML model, and saves it.
"""

import asyncio
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report

from services.broker.kite import get_broker
from services.broker.chartink import get_chartink_client
from services.ai.features import FeatureEngineer
from core.logging import logger


class ModelTrainer:
    def __init__(self):
        self.broker = get_broker()
        self.chartink = get_chartink_client()
        self.feature_engineer = FeatureEngineer()
        self.model = None
        self.scaler = None
        self.feature_names = []

    def prepare_data(self, df: pd.DataFrame, lookahead: int = 5) -> pd.DataFrame:
        features_df = self.feature_engineer.generate_features(df)
        features_df = self._create_labels(features_df, lookahead)
        features_df = features_df.dropna()
        return features_df

    def _create_labels(self, df: pd.DataFrame, lookahead: int = 5) -> pd.DataFrame:
        if "close" not in df.columns:
            return df

        future_returns = df["close"].shift(-lookahead) / df["close"] - 1

        labels = pd.Series(0, index=df.index)
        labels[future_returns > 0.05] = 1
        labels[future_returns < -0.03] = -1

        df = df.copy()
        df["signal"] = labels

        return df

    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> bool:
        try:
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42,
            )
            self.model.fit(X_train, y_train)
            logger.info("Model trained successfully")
            return True
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            return False

    def save_model(self, path: str) -> bool:
        if not self.model:
            return False
        try:
            joblib.dump(
                {
                    "model": self.model,
                    "scaler": self.scaler,
                    "feature_names": self.feature_names,
                },
                path,
            )
            logger.info(f"Model saved to {path}")
            return True
        except Exception as e:
            logger.error(f"Model save failed: {e}")
            return False


async def fetch_symbol_data(broker, symbol: str, days: int = 60) -> pd.DataFrame:
    try:
        to_date = datetime.utcnow()
        from_date = to_date - timedelta(days=days)

        data = broker.get_historical_data(symbol, from_date, to_date, "60minute")
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
        logger.error(f"Error fetching {symbol}: {e}")
        return pd.DataFrame()


async def main():
    logger.info("Starting model training...")

    trainer = ModelTrainer()

    connected = trainer.broker.connect()
    if not connected:
        logger.error("Failed to connect to broker")
        return

    logger.info("Fetching symbols from ChartInk...")
    symbols = await trainer.chartink.fetch_stocks()
    if not symbols:
        logger.error("No symbols from ChartInk")
        return

    logger.info(f"Fetching data for {len(symbols)} symbols...")

    all_data = []
    for i, symbol in enumerate(symbols[:20]):
        logger.info(f"[{i+1}/20] {symbol}")

        df = await fetch_symbol_data(trainer.broker, symbol, days=90)
        if len(df) < 50:
            continue

        prepared = trainer.prepare_data(df, lookahead=5)
        if len(prepared) < 20:
            continue

        prepared["symbol"] = symbol
        all_data.append(prepared)

    if not all_data:
        logger.error("No data collected")
        return

    combined = pd.concat(all_data, ignore_index=True)
    logger.info(f"Combined dataset: {len(combined)} rows")

    feature_names = trainer.feature_engineer.get_feature_names()
    available_features = [f for f in feature_names if f in combined.columns]

    X = combined[available_features]
    y = combined["signal"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    trainer.scaler = StandardScaler()
    X_train_scaled = trainer.scaler.fit_transform(X_train)
    X_test_scaled = trainer.scaler.transform(X_test)

    trainer.feature_names = available_features

    logger.info("Training model...")
    success = trainer.train(X_train_scaled, y_train)
    if not success:
        return

    y_pred = trainer.model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    logger.info(f"Test accuracy: {accuracy:.2%}")
    logger.info(f"Classification:\n{classification_report(y_test, y_pred)}")

    model_path = "model.joblib"
    trainer.save_model(model_path)
    logger.info(f"Model saved to {model_path}")


if __name__ == "__main__":
    asyncio.run(main())