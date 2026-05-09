import numpy as np
from typing import Dict, Any, Optional, Tuple
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from core.logging import logger


class OutOfSampleValidator:
    def __init__(self, overfitting_threshold: float = 0.15):
        self.overfitting_threshold = overfitting_threshold

    def validate(
        self,
        model,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
        model_name: str = "model",
    ) -> Dict[str, Any]:
        results = {
            "model_name": model_name,
            "train_size": len(X_train),
            "test_size": len(X_test),
            "overfitting_detected": False,
            "train_metrics": {},
            "test_metrics": {},
            "confusion_matrix": None,
        }

        try:
            y_train_pred = model.predict(X_train)
            y_test_pred = model.predict(X_test)

            results["train_metrics"] = self._calculate_metrics(y_train, y_train_pred)
            results["test_metrics"] = self._calculate_metrics(y_test, y_test_pred)

            train_acc = results["train_metrics"]["accuracy"]
            test_acc = results["test_metrics"]["accuracy"]
            acc_diff = train_acc - test_acc

            results["overfitting_detected"] = acc_diff > self.overfitting_threshold
            results["accuracy_drop"] = acc_diff

            if results["overfitting_detected"]:
                logger.warning(
                    f"Overfitting detected in {model_name}: "
                    f"train_acc={train_acc:.3f}, test_acc={test_acc:.3f}, "
                    f"drop={acc_diff:.3f}"
                )

            from sklearn.metrics import confusion_matrix
            results["confusion_matrix"] = confusion_matrix(y_test, y_test_pred).tolist()

            logger.info(
                f"Validation {model_name}: "
                f"train_acc={train_acc:.3f}, test_acc={test_acc:.3f}, "
                f"precision_buy={results['test_metrics'].get('precision_buy', 0):.3f}"
            )

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            results["error"] = str(e)

        return results

    def _calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        return {
            "accuracy": accuracy_score(y_true, y_pred),
            "precision": precision_score(y_true, y_pred, average="weighted", zero_division=0),
            "recall": recall_score(y_true, y_pred, average="weighted", zero_division=0),
            "f1_score": f1_score(y_true, y_pred, average="weighted", zero_division=0),
            "precision_buy": precision_score(y_true, y_pred, labels=[2], average="micro", zero_division=0),
        }

    def compare_folds(self, fold_results: list) -> Dict[str, Any]:
        if not fold_results:
            return {}

        train_accs = [r["train_metrics"]["accuracy"] for r in fold_results]
        test_accs = [r["test_metrics"]["accuracy"] for r in fold_results]
        buy_precisions = [r["test_metrics"].get("precision_buy", 0) for r in fold_results]

        return {
            "avg_train_accuracy": float(np.mean(train_accs)),
            "avg_test_accuracy": float(np.mean(test_accs)),
            "std_test_accuracy": float(np.std(test_accs)),
            "avg_precision_buy": float(np.mean(buy_precisions)),
            "min_test_accuracy": float(np.min(test_accs)),
            "max_test_accuracy": float(np.max(test_accs)),
            "folds": len(fold_results),
        }
