import numpy as np
import pandas as pd
from typing import Tuple, Optional, List
from core.logging import logger
from services.ai.features import FeatureEngineer


class ModelTrainer:
    def __init__(self, target_return: float = 0.10, stop_loss: float = 0.03):
        self.target_return = target_return
        self.stop_loss = stop_loss
        self.feature_engineer = FeatureEngineer()
        self.model = None
        self.scaler = None
        self.feature_names: List[str] = []
        self._is_trained = False

    def prepare_data(self, df: pd.DataFrame, lookahead: int = 5) -> Tuple:
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler

        features_df = self.feature_engineer.generate_features(df)

        features_df = self._create_labels(features_df, lookahead)
        features_df = features_df.dropna()

        if features_df.empty:
            raise ValueError("No valid data after feature generation")

        feature_names = self.feature_engineer.get_feature_names()
        available_features = [f for f in feature_names if f in features_df.columns]
        X = features_df[available_features]
        y = features_df["signal"]

        self.feature_names = available_features

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False
        )

        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        return X_train_scaled, X_test_scaled, y_train, y_test

    def _create_labels(self, df: pd.DataFrame, lookahead: int = 5) -> pd.DataFrame:
        if "close" not in df.columns:
            return df

        future_returns = df["close"].shift(-lookahead) / df["close"] - 1

        labels = pd.Series(0, index=df.index)
        labels[future_returns > self.target_return] = 1
        labels[future_returns < -self.stop_loss] = -1

        df = df.copy()
        df["signal"] = labels

        return df

    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> bool:
        from sklearn.ensemble import GradientBoostingClassifier
        try:
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42,
            )

            self.model.fit(X_train, y_train)
            self._is_trained = True
            logger.info("Model trained successfully")
            return True

        except Exception as e:
            logger.error(f"Model training failed - {e}")
            return False

    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> dict:
        from sklearn.metrics import accuracy_score, classification_report
        if not self.model:
            return {"accuracy": 0}

        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)

        return {
            "accuracy": accuracy,
            "report": classification_report(y_test, y_pred),
        }

    def save_model(self, path: str) -> bool:
        import joblib
        if not self.model:
            return False

        try:
            joblib.dump(
                {"model": self.model, "scaler": self.scaler, "feature_names": self.feature_names},
                path,
            )
            logger.info(f"Model saved to {path}")
            return True
        except Exception as e:
            logger.error(f"Model save failed - {e}")
            return False

    def load_model(self, path: str) -> bool:
        import joblib
        try:
            data = joblib.load(path)
            self.model = data["model"]
            self.scaler = data["scaler"]
            self.feature_names = data["feature_names"]
            self._is_trained = True
            logger.debug(f"Model loaded from {path}")
            return True
        except Exception as e:
            logger.error(f"Model load failed - {e}")
            return False

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.model:
            return np.array([])

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            X_aligned = self._align_features(X)
            X_scaled = self.scaler.transform(X_aligned)
            return self.model.predict(X_scaled)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.model:
            return np.array([])

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            X_aligned = self._align_features(X)
            X_scaled = self.scaler.transform(X_aligned)
            return self.model.predict_proba(X_scaled)

    def _align_features(self, X: np.ndarray) -> np.ndarray:
        if not self.feature_names:
            return X

        expected_cols = len(self.feature_names)
        if X.shape[1] == expected_cols:
            return X

        if X.shape[1] > expected_cols:
            return X[:, :expected_cols]

        padded = np.zeros((X.shape[0], expected_cols))
        padded[:, :X.shape[1]] = X
        return padded

    def is_trained(self) -> bool:
        return self._is_trained