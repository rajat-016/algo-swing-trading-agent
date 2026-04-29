import joblib
import numpy as np
import pandas as pd
from typing import Optional, Dict, Any
from pathlib import Path
import logging
import sys
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

BACKEND_PATH = str(Path(__file__).parent.parent.parent / "backend")
if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)


class ModelTrainer:
    def __init__(
        self,
        model_path: str = None,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        if model_path is None:
            model_path = str(Path(BACKEND_PATH) / "services" / "ai" / "model.joblib")

        self.model_path = model_path
        self.parameters = parameters or {}
        self.model = None
        self.scaler = None
        self.feature_names = []
        self._is_trained = False

    def load_existing_model(self) -> bool:
        try:
            data = joblib.load(self.model_path)
            self.model = data["model"]
            
            # Disable parallel processing to avoid joblib KeyboardInterrupt issues
            if hasattr(self.model, 'n_jobs'):
                self.model.n_jobs = 1
            
            # Handle VotingClassifier or similar ensemble models
            if hasattr(self.model, 'estimators'):
                for name, estimator in self.model.estimators:
                    if hasattr(estimator, 'n_jobs'):
                        estimator.n_jobs = 1
            if hasattr(self.model, 'estimators_'):
                for estimator in self.model.estimators_:
                    if hasattr(estimator, 'n_jobs'):
                        estimator.n_jobs = 1
            
            self.scaler = data.get("scaler", None)
            self.feature_names = data.get("feature_names", [])
            self._is_trained = True
            logger.info(f"Loaded existing model from {self.model_path} (parallel processing disabled)")
            return True
        except FileNotFoundError:
            logger.warning(f"No existing model found at {self.model_path}. Will train from scratch.")
            return False
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def prepare_data(
        self,
        train_df: pd.DataFrame,
        feature_names: list,
        label_col: str = "signal",
    ):
        from sklearn.ensemble import GradientBoostingClassifier

        available_features = [f for f in feature_names if f in train_df.columns]
        if not available_features:
            raise ValueError("No matching feature columns found in DataFrame")

        X = train_df[available_features].dropna()
        y = train_df.loc[X.index, label_col]

        if len(X) == 0:
            raise ValueError("No valid data after dropping NaN")

        self.feature_names = available_features

        if self.scaler is None:
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)
        else:
            X_scaled = self.scaler.transform(X)

        if self.model is None:
            self.model = GradientBoostingClassifier(
                n_estimators=self.parameters.get("n_estimators", 100),
                learning_rate=self.parameters.get("learning_rate", 0.1),
                max_depth=self.parameters.get("max_depth", 5),
                subsample=self.parameters.get("subsample", 0.8),
                random_state=42,
            )

        return X_scaled, y

    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> bool:
        try:
            self.model.fit(X_train, y_train)
            self._is_trained = True
            logger.info("Model trained successfully")
            return True
        except KeyboardInterrupt:
            logger.warning("Model training interrupted by user")
            return False
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            return False

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self._is_trained:
            return np.array([])

        X_aligned = self._align_features(X)

        if self.scaler is not None:
            X_scaled = self.scaler.transform(X_aligned)
        else:
            X_scaled = X_aligned

        return self.model.predict(X_scaled)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self._is_trained:
            return np.array([])

        X_aligned = self._align_features(X)

        if self.scaler is not None:
            X_scaled = self.scaler.transform(X_aligned)
        else:
            X_scaled = X_aligned

        return self.model.predict_proba(X_scaled)

    def _align_features(self, X: np.ndarray) -> np.ndarray:
        expected_cols = len(self.feature_names)
        if X.shape[1] == expected_cols:
            return X

        if X.shape[1] > expected_cols:
            return X[:, :expected_cols]

        padded = np.zeros((X.shape[0], expected_cols))
        padded[:, :X.shape[1]] = X
        return padded

    def save_model(self, path: str) -> bool:
        if not self.model:
            return False

        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
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

    def is_trained(self) -> bool:
        return self._is_trained
