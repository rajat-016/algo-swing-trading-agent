from typing import Dict, List, Optional, Any
import numpy as np


class FeatureAttribution:
    CLASS_LABELS = ["SELL", "HOLD", "BUY"]

    def compute_attribution(
        self,
        shap_result: Dict[str, Any],
        feature_names: List[str],
        top_n: int = 15,
    ) -> Dict[str, Any]:
        attributions = {}
        for cls_label in self.CLASS_LABELS:
            class_data = shap_result.get(cls_label)
            if class_data is None:
                continue

            sv = np.array(class_data["shap_values"])
            if sv.ndim == 2:
                sv = sv[0]

            base_value = class_data.get("base_value", 0.0)
            predicted_score = float(base_value + np.sum(sv))

            contributions = []
            for i, name in enumerate(feature_names[: len(sv)]):
                contributions.append({
                    "feature": name,
                    "shap_value": float(sv[i]),
                    "abs_contribution": float(abs(sv[i])),
                    "direction": "positive" if sv[i] >= 0 else "negative",
                })

            contributions.sort(key=lambda x: x["abs_contribution"], reverse=True)

            total_abs = sum(c["abs_contribution"] for c in contributions) or 1.0
            for c in contributions:
                c["contribution_pct"] = round(c["abs_contribution"] / total_abs * 100, 2)

            positive = [c for c in contributions if c["direction"] == "positive"]
            negative = [c for c in contributions if c["direction"] == "negative"]

            attributions[cls_label] = {
                "base_value": round(float(base_value), 6),
                "predicted_score": round(float(predicted_score), 6),
                "num_features": len(contributions),
                "positive_drivers": positive[:top_n],
                "negative_drivers": negative[:top_n],
                "top_features": contributions[:top_n],
                "positive_pct": round(
                    sum(c["abs_contribution"] for c in positive) / total_abs * 100, 2
                ) if positive else 0.0,
                "negative_pct": round(
                    sum(c["abs_contribution"] for c in negative) / total_abs * 100, 2
                ) if negative else 0.0,
            }

        return attributions

    def summarize_attribution(
        self,
        attribution: Dict[str, Any],
        primary_class: str = "BUY",
    ) -> Dict[str, Any]:
        cls_data = attribution.get(primary_class)
        if cls_data is None:
            return {}

        top_features = cls_data.get("top_features", [])[:5]
        summary = {
            "primary_class": primary_class,
            "predicted_score": cls_data["predicted_score"],
            "base_value": cls_data["base_value"],
            "top_5_features": [
                {
                    "feature": f["feature"],
                    "shap_value": f["shap_value"],
                    "direction": f["direction"],
                }
                for f in top_features
            ],
            "net_direction": "positive" if cls_data["positive_pct"] > cls_data["negative_pct"] else "negative",
            "positive_pct": cls_data["positive_pct"],
            "negative_pct": cls_data["negative_pct"],
            "feature_count": cls_data["num_features"],
        }
        return summary
