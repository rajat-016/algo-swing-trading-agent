import numpy as np
from typing import Optional, Dict, Any
from core.logging import logger

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    logger.warning("XGBoost not available")


class TradingModel:
    LABEL_MAP = {0: "SELL", 1: "HOLD", 2: "BUY"}

    def __init__(
        self,
        max_depth: int = 5,
        n_estimators: int = 200,
        learning_rate: float = 0.05,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        min_child_weight: int = 3,
        gamma: float = 0.1,
        random_state: int = 42,
    ):
        if not HAS_XGBOOST:
            raise ImportError("XGBoost is required for TradingModel")

        self.model = XGBClassifier(
            objective="multi:softprob",
            num_class=3,
            max_depth=max_depth,
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            subsample=subsample,
            colsample_bytree=colsample_bytree,
            min_child_weight=min_child_weight,
            gamma=gamma,
            random_state=random_state,
            n_jobs=1,
            eval_metric="mlogloss",
        )
        self._is_trained = False
        self.feature_names: list = []
        self.scaler = None
        self.calibrator = None

    def fit(self, X: np.ndarray, y: np.ndarray, sample_weight: Optional[np.ndarray] = None) -> None:
        if sample_weight is not None:
            self.model.fit(X, y, sample_weight=sample_weight)
        else:
            self.model.fit(X, y)
        self._is_trained = True
        logger.info(f"TradingModel trained: {len(X)} samples, {X.shape[1]} features")

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self._is_trained:
            raise RuntimeError("Model not trained")

        X_aligned = self._align_features(X)
        X_scaled = self.scaler.transform(X_aligned) if self.scaler is not None else X_aligned

        if self.calibrator is not None:
            return self.calibrator.predict_proba(X_scaled)

        return self.model.predict_proba(X_scaled)

    def predict(self, X: np.ndarray) -> np.ndarray:
        probs = self.predict_proba(X)
        return np.argmax(probs, axis=1)

    def set_scaler(self, scaler) -> None:
        self.scaler = scaler

    def set_calibrator(self, calibrator) -> None:
        self.calibrator = calibrator
        self._is_trained = True

    def is_trained(self) -> bool:
        return self._is_trained

    def feature_importance(self) -> Dict[str, float]:
        if not self._is_trained:
            return {}
        importances = self.model.feature_importances_
        return dict(zip(self.feature_names, importances.tolist()))

    def _align_features(self, X: np.ndarray) -> np.ndarray:
        if not self.feature_names:
            return X
        expected = len(self.feature_names)
        if X.shape[1] == expected:
            return X
        if X.shape[1] > expected:
            return X[:, :expected]
        padded = np.zeros((X.shape[0], expected))
        padded[:, : X.shape[1]] = X
        return padded
