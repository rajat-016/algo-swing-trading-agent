import numpy as np
from typing import Optional
from sklearn.calibration import CalibratedClassifierCV
from core.logging import logger


class Calibrator:
    def __init__(
        self,
        base_model,
        method: str = "isotonic",
        cv: int = 3,
    ):
        self.base_model = base_model
        self.method = method
        self.cv = cv
        self.calibrated_model: Optional[CalibratedClassifierCV] = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        if len(X) < 20:
            logger.warning("Calibrator: insufficient data for calibration, skipping")
            return

        self.calibrated_model = CalibratedClassifierCV(
            self.base_model,
            method=self.method,
            cv=self.cv,
        )
        self.calibrated_model.fit(X, y)
        logger.info(f"Calibrator fitted: method={self.method}, cv={self.cv}")

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self.calibrated_model is not None:
            return self.calibrated_model.predict_proba(X)
        return self.base_model.predict_proba(X)

    def predict(self, X: np.ndarray) -> np.ndarray:
        probs = self.predict_proba(X)
        return np.argmax(probs, axis=1)
