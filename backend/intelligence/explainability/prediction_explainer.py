import time
import json
from typing import Optional, Dict, Any, List
import numpy as np
from core.logging import logger
from intelligence.explainability.shap_explainer import SHAPExplainer
from intelligence.explainability.feature_attribution import FeatureAttribution
from intelligence.explainability.confidence_analyzer import ConfidenceAnalyzer


class PredictionExplainer:
    def __init__(
        self,
        model=None,
        feature_names: Optional[List[str]] = None,
        background_samples: Optional[np.ndarray] = None,
        top_n_features: int = 15,
    ):
        self.shap_explainer = SHAPExplainer(
            model=model,
            feature_names=feature_names,
            background_samples=background_samples,
        )
        self.feature_attribution = FeatureAttribution()
        self.confidence_analyzer = ConfidenceAnalyzer()
        self.feature_names = feature_names or []
        self.top_n_features = top_n_features

    def set_model(self, model, feature_names: Optional[List[str]] = None):
        self.shap_explainer._model = model
        self.shap_explainer._explainer = None
        if feature_names:
            self.feature_names = feature_names
            self.shap_explainer.feature_names = feature_names

    def explain_prediction(
        self,
        X: np.ndarray,
        probs: np.ndarray,
        class_names: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        overall_start = time.monotonic()

        if X.ndim == 1:
            X = X.reshape(1, -1)

        probs_dict = {
            "sell": float(probs[0]) if len(probs) >= 1 else 0.0,
            "hold": float(probs[1]) if len(probs) >= 2 else 0.0,
            "buy": float(probs[2]) if len(probs) >= 3 else 0.0,
        }
        predicted_class_idx = int(np.argmax(probs))
        class_labels = class_names or ["SELL", "HOLD", "BUY"]
        predicted_label = class_labels[predicted_class_idx] if predicted_class_idx < len(class_labels) else "UNKNOWN"

        shap_start = time.monotonic()
        shap_result = self.shap_explainer.compute_shap_values(X, class_index=predicted_class_idx)
        shap_latency = time.monotonic() - shap_start

        attribution = self.feature_attribution.compute_attribution(
            shap_result, self.feature_names, top_n=self.top_n_features
        )

        confidence_decomp = self.confidence_analyzer.decompose_confidence(
            shap_result, self.feature_names, class_label=predicted_label
        )

        decision_drivers = self.confidence_analyzer.analyze_decision_drivers(
            probs_dict, shap_result, self.feature_names
        )

        confidence_metrics = self.confidence_analyzer.compute_confidence_metrics(probs_dict)

        top_features = self.shap_explainer.get_top_features(
            shap_result, class_label=predicted_label, top_n=self.top_n_features
        )

        global_importance = self.shap_explainer.feature_importance_from_shap(
            shap_result, class_label=predicted_label
        )[:10]

        overall_latency = time.monotonic() - overall_start

        explanation = {
            "prediction": {
                "predicted_class": predicted_label,
                "class_index": predicted_class_idx,
                "probabilities": probs_dict,
            },
            "confidence": confidence_metrics,
            "shap": {
                "explainer_type": shap_result["metadata"]["explainer_type"],
                "latency_seconds": shap_result["metadata"]["latency_seconds"],
            },
            "feature_attribution": {
                "primary_class": attribution.get(predicted_label, {}),
                "all_classes": {k: self._summarize_class_attribution(v) for k, v in attribution.items()},
            },
            "top_features": top_features,
            "global_feature_importance": global_importance,
            "confidence_decomposition": confidence_decomp,
            "decision_drivers": decision_drivers,
            "metadata": {
                "explanation_version": "1.0.0",
                "total_latency_seconds": round(overall_latency, 4),
                "shap_latency_seconds": round(shap_latency, 4),
                "num_features_analyzed": len(self.feature_names),
            },
        }

        if metadata:
            explanation["metadata"].update(metadata)

        logger.info(
            f"Generated explanation for {predicted_label} "
            f"(latency={overall_latency:.3f}s, shap={shap_latency:.3f}s)"
        )
        return explanation

    def _summarize_class_attribution(self, attr: Dict[str, Any]) -> Dict[str, Any]:
        if not attr:
            return {}
        return {
            "base_value": attr.get("base_value"),
            "predicted_score": attr.get("predicted_score"),
            "top_3_features": attr.get("top_features", [])[:3],
            "positive_pct": attr.get("positive_pct"),
            "negative_pct": attr.get("negative_pct"),
        }

    def to_json(self, explanation: Dict[str, Any], indent: int = 2) -> str:
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (np.integer,)):
                    return int(obj)
                if isinstance(obj, (np.floating,)):
                    return float(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super().default(obj)

        return json.dumps(explanation, cls=NumpyEncoder, indent=indent)
