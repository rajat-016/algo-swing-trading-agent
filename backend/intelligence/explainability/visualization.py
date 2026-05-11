from typing import Dict, List, Any, Optional


class ExplanationVisualizer:
    def prepare_waterfall_data(
        self,
        top_features: Dict[str, List[Dict[str, Any]]],
        base_value: float,
        predicted_value: float,
        max_features: int = 10,
    ) -> Dict[str, Any]:
        positive = top_features.get("positive", [])
        negative = top_features.get("negative", [])

        combined = []
        for p in positive[:max_features // 2]:
            combined.append(p)
        for n in negative[:max_features // 2]:
            combined.append(n)

        combined.sort(key=lambda x: abs(x.get("shap_value", 0)), reverse=True)
        combined = combined[:max_features]

        waterfall = []
        running = base_value
        for item in combined:
            sv = item["shap_value"]
            running += sv
            waterfall.append({
                "feature": item["feature"],
                "shap_value": sv,
                "cumulative": round(running, 6),
                "direction": item.get("direction", "positive" if sv >= 0 else "negative"),
            })

        return {
            "base_value": base_value,
            "predicted_value": predicted_value,
            "steps": waterfall,
            "num_steps": len(waterfall),
        }

    def prepare_feature_bar_data(
        self,
        importance_list: List[Dict[str, Any]],
        top_n: int = 15,
    ) -> Dict[str, Any]:
        top = importance_list[:top_n]
        bar_data = {
            "features": [t["feature"] for t in top],
            "importance": [t["importance"] for t in top],
            "importance_pct": [t["importance_pct"] for t in top],
            "directions": [t["direction"] for t in top],
        }
        return bar_data

    def prepare_confidence_gauge(
        self,
        confidence_metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "max_probability": confidence_metrics.get("max_probability", 0),
            "confidence_level": confidence_metrics.get("confidence_level", "low"),
            "margin": confidence_metrics.get("margin_over_second", 0),
            "entropy": confidence_metrics.get("entropy", 0),
            "gauge_value": confidence_metrics.get("max_probability", 0) * 100,
        }

    def prepare_group_contribution_chart(
        self,
        group_contributions: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        groups = []
        for name, data in group_contributions.items():
            groups.append({
                "group": name,
                "contribution_pct": data["contribution_pct"],
                "direction": data["direction"],
                "total_shap": data["total_shap"],
                "matched_features": data["matched_features"],
            })
        groups.sort(key=lambda x: x["contribution_pct"], reverse=True)
        return {
            "groups": groups,
            "primary_driver": groups[0]["group"] if groups else None,
        }

    def prepare_summary_dashboard(
        self,
        explanation: Dict[str, Any],
    ) -> Dict[str, Any]:
        pred = explanation.get("prediction", {})
        conf = explanation.get("confidence", {})
        decomp = explanation.get("confidence_decomposition", {})
        top_feat = explanation.get("top_features", {})

        return {
            "predicted_class": pred.get("predicted_class"),
            "confidence_level": conf.get("confidence_level"),
            "max_probability": conf.get("max_probability"),
            "primary_driver": decomp.get("primary_driver"),
            "top_positive_features": [f["feature"] for f in top_feat.get("positive", [])[:5]],
            "top_negative_features": [f["feature"] for f in top_feat.get("negative", [])[:5]],
            "explanation_latency": explanation.get("metadata", {}).get("total_latency_seconds"),
            "data": {
                "waterfall": self.prepare_waterfall_data(
                    top_feat,
                    decomp.get("base_value", 0),
                    decomp.get("predicted_score", 0),
                ),
                "confidence_gauge": self.prepare_confidence_gauge(conf),
                "group_breakdown": self.prepare_group_contribution_chart(
                    decomp.get("group_contributions", {})
                ),
            },
        }
