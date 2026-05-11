import time
import numpy as np
from typing import Optional, Dict, Any, List
from core.logging import logger

HAS_SHAP = False
try:
    import shap
    HAS_SHAP = True
except ImportError:
    pass


class SHAPExplainer:
    def __init__(
        self,
        model=None,
        feature_names: Optional[List[str]] = None,
        background_samples: Optional[np.ndarray] = None,
    ):
        self._explainer = None
        self._model = model
        self.feature_names = feature_names or []
        self.background_samples = background_samples
        self.explainer_type = None

    def _build_explainer(self, model):
        if not HAS_SHAP:
            raise ImportError("shap is required for SHAPExplainer. Install with: pip install shap")

        xgb_model = getattr(model, "model", model)
        if hasattr(xgb_model, "get_booster"):
            self._explainer = shap.TreeExplainer(xgb_model)
            self.explainer_type = "TreeExplainer"
            logger.info("Built TreeExplainer for XGBoost model")
        elif self.background_samples is not None:
            self._explainer = shap.Explainer(
                lambda x: model.predict_proba(x) if hasattr(model, "predict_proba") else model(x),
                self.background_samples[:100],
            )
            self.explainer_type = "KernelExplainer"
            logger.info("Built KernelExplainer with background samples")
        else:
            self._explainer = shap.Explainer(
                lambda x: model.predict_proba(x) if hasattr(model, "predict_proba") else model(x),
            )
            self.explainer_type = "GenericExplainer"
            logger.info("Built generic Explainer")

    @property
    def explainer(self):
        if self._explainer is None and self._model is not None:
            self._build_explainer(self._model)
        return self._explainer

    def compute_shap_values(
        self,
        X: np.ndarray,
        class_index: int = 2,
    ) -> Dict[str, Any]:
        start = time.monotonic()
        if self.explainer is None:
            raise RuntimeError("SHAP explainer not built. Provide a model first.")

        if X.ndim == 1:
            X = X.reshape(1, -1)

        try:
            shap_values_obj = self.explainer.shap_values(X, check_additivity=False)
        except Exception as e:
            logger.warning(f"shap_values failed, trying approximate: {e}")
            shap_values_obj = self.explainer(X)
            if hasattr(shap_values_obj, "values"):
                shap_values_obj = shap_values_obj.values

        shap_arrays = self._normalize_shap_output(shap_values_obj, X)
        elapsed = time.monotonic() - start

        result = {}
        for cls_name, cls_idx in [("SELL", 0), ("HOLD", 1), ("BUY", 2)]:
            if cls_idx < len(shap_arrays):
                sv = shap_arrays[cls_idx]
                base_val = getattr(self._explainer, "expected_value", None)
                ev = base_val[cls_idx] if isinstance(base_val, (list, np.ndarray)) else base_val
                result[cls_name] = {
                    "shap_values": sv.tolist() if sv.ndim == 2 else sv.tolist(),
                    "base_value": float(ev) if ev is not None else 0.0,
                }

        result["metadata"] = {
            "explainer_type": self.explainer_type,
            "num_features": X.shape[1],
            "num_samples": X.shape[0],
            "latency_seconds": round(elapsed, 4),
        }

        return result

    def _normalize_shap_output(self, shap_obj, X: np.ndarray) -> List[np.ndarray]:
        if isinstance(shap_obj, list):
            if len(shap_obj) == 3 and all(isinstance(s, np.ndarray) for s in shap_obj):
                return shap_obj
            if len(shap_obj) == 2:
                return [shap_obj[0], shap_obj[1], shap_obj[1]]
            return shap_obj
        if isinstance(shap_obj, np.ndarray):
            if shap_obj.ndim == 3:
                return [shap_obj[:, :, i] for i in range(shap_obj.shape[2])]
            return [shap_obj, shap_obj, shap_obj]
        return [np.zeros_like(X) for _ in range(3)]

    def get_top_features(
        self,
        shap_result: Dict[str, Any],
        class_label: str = "BUY",
        top_n: int = 10,
    ) -> Dict[str, List[Dict[str, Any]]]:
        class_data = shap_result.get(class_label)
        if class_data is None:
            return {"positive": [], "negative": []}

        sv = np.array(class_data["shap_values"])
        if sv.ndim == 2:
            sv = sv[0]

        feature_contribs = list(zip(self.feature_names[: len(sv)], sv))
        feature_contribs.sort(key=lambda x: abs(x[1]), reverse=True)

        positive = []
        negative = []
        for name, val in feature_contribs:
            entry = {"feature": name, "shap_value": round(float(val), 6)}
            if val >= 0:
                positive.append(entry)
            else:
                negative.append(entry)

        return {
            "positive": positive[:top_n],
            "negative": negative[:top_n],
        }

    def feature_importance_from_shap(
        self,
        shap_result: Dict[str, Any],
        class_label: str = "BUY",
    ) -> List[Dict[str, Any]]:
        class_data = shap_result.get(class_label)
        if class_data is None:
            return []

        sv = np.array(class_data["shap_values"])
        if sv.ndim == 2:
            sv = np.mean(np.abs(sv), axis=0)

        total = np.sum(sv) if np.sum(sv) > 0 else 1.0
        importance = []
        for i, name in enumerate(self.feature_names[: len(sv)]):
            importance.append({
                "feature": name,
                "importance": float(np.abs(sv[i])),
                "importance_pct": round(float(np.abs(sv[i]) / total * 100), 2),
                "direction": "positive" if sv[i] >= 0 else "negative",
            })

        importance.sort(key=lambda x: x["importance"], reverse=True)
        return importance
