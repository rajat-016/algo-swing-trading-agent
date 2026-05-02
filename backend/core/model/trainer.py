import numpy as np
import pandas as pd
from typing import Optional, Tuple, List
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from core.model.model import TradingModel
from core.model.calibrator import Calibrator
from core.logging import logger


class ModelTrainer:
    def __init__(
        self,
        confidence_threshold: float = 0.65,
        n_cv_splits: int = 3,
    ):
        self.confidence_threshold = confidence_threshold
        self.n_cv_splits = n_cv_splits
        self.model: Optional[TradingModel] = None
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []

    def prepare_data(
        self,
        features: pd.DataFrame,
        labels: pd.Series,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        self.feature_names = features.columns.tolist()

        X = features.values
        y = labels.values.astype(int)

        nan_mask = np.isnan(X) | np.isinf(X)
        if nan_mask.any():
            X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        X_scaled = self.scaler.fit_transform(X)

        sample_weights = compute_sample_weight("balanced", y)

        logger.info(f"Data prepared: {len(X)} samples, {X.shape[1]} features, "
                     f"class dist: {dict(zip(*np.unique(y, return_counts=True)))}")

        return X_scaled, y, sample_weights

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        sample_weights: Optional[np.ndarray] = None,
    ) -> TradingModel:
        self.model = TradingModel()
        self.model.feature_names = self.feature_names
        self.model.set_scaler(self.scaler)

        self.model.fit(X, y, sample_weight=sample_weights)

        calibrator = Calibrator(base_model=self.model.model)
        calibrator.fit(X, y)
        self.model.set_calibrator(calibrator)

        logger.info("Model trained and calibrated")
        return self.model

    def walk_forward_train(
        self,
        features: pd.DataFrame,
        labels: pd.Series,
    ) -> Tuple[TradingModel, List[dict]]:
        tscv = TimeSeriesSplit(n_splits=self.n_cv_splits)
        results = []

        best_score = -1
        best_model_data = None

        for fold, (train_idx, val_idx) in enumerate(tscv.split(features)):
            X_train = features.iloc[train_idx].values
            y_train = labels.iloc[train_idx].values.astype(int)
            X_val = features.iloc[val_idx].values
            y_val = labels.iloc[val_idx].values.astype(int)

            X_train = np.nan_to_num(X_train, nan=0.0, posinf=0.0, neginf=0.0)
            X_val = np.nan_to_num(X_val, nan=0.0, posinf=0.0, neginf=0.0)

            scaler = StandardScaler()
            X_train_s = scaler.fit_transform(X_train)
            X_val_s = scaler.transform(X_val)

            sample_weights = compute_sample_weight("balanced", y_train)

            fold_model = TradingModel()
            fold_model.feature_names = self.feature_names
            fold_model.set_scaler(scaler)
            fold_model.fit(X_train_s, y_train, sample_weight=sample_weights)

            cal = Calibrator(base_model=fold_model.model)
            cal.fit(X_train_s, y_train)
            fold_model.set_calibrator(cal)

            y_pred = fold_model.predict(X_val_s)

            fold_metrics = {
                "fold": fold,
                "train_size": len(train_idx),
                "val_size": len(val_idx),
                "accuracy": accuracy_score(y_val, y_pred),
                "precision_buy": precision_score(y_val, y_pred, labels=[2], average="micro", zero_division=0),
                "precision_sell": precision_score(y_val, y_pred, labels=[0], average="micro", zero_division=0),
                "recall_buy": recall_score(y_val, y_pred, labels=[2], average="micro", zero_division=0),
                "f1": f1_score(y_val, y_pred, average="weighted", zero_division=0),
            }
            results.append(fold_metrics)

            precision_buy = fold_metrics["precision_buy"]
            if precision_buy > best_score:
                best_score = precision_buy
                best_model_data = {
                    "scaler": scaler,
                    "calibrator": cal,
                    "base_model": fold_model.model,
                }

            logger.info(f"Fold {fold}: acc={fold_metrics['accuracy']:.3f}, "
                         f"prec_buy={fold_metrics['precision_buy']:.3f}, "
                         f"f1={fold_metrics['f1']:.3f}")

        final_model = TradingModel()
        final_model.feature_names = self.feature_names
        final_model.set_scaler(best_model_data["scaler"])
        final_model.model = best_model_data["base_model"]
        final_model.set_calibrator(best_model_data["calibrator"])
        self.model = final_model
        self.scaler = best_model_data["scaler"]

        logger.info(f"Walk-forward complete: {len(results)} folds, "
                     f"best BUY precision={best_score:.3f}")

        return final_model, results
