from typing import Dict, List, Optional, Any
import numpy as np


FEATURE_GROUPS = {
    "price_action": ["returns", "log_returns", "price_range", "hl_ratio", "co_ratio",
                     "close_position", "body_to_range", "intraday_return", "gap_size",
                     "inside_bar", "bullish_signal", "bearish_signal"],
    "moving_averages": ["sma_20", "sma_50", "ema_20", "ema_50", "sma_20_50_diff",
                        "price_to_sma_20", "price_to_sma_50", "ema_20_above_50",
                        "ema_20_slope"],
    "momentum": ["rsi_14", "macd", "macd_signal", "macd_hist", "momentum_12",
                 "momentum_26", "returns_5d", "returns_10d", "returns_20d",
                 "momentum_persistency"],
    "volatility": ["atr_14", "stddev_20", "bb_position", "historical_volatility_20",
                   "hv_ratio", "donchian_position", "atr_percent", "volatility_expansion"],
    "volume": ["volume_ratio", "vwap", "breakout_volume", "volume_imbalance",
               "buying_volume_ratio", "selling_volume_ratio", "relative_volume"],
    "pattern_strategy": ["pullback_pct", "support_distance", "trend_strength",
                         "resistance_distance", "retest_holds", "stage",
                         "range_contraction", "vcp_signal", "reversal_candle",
                         "near_support", "weekly_trend", "daily_weekly_aligned"],
    "relative_strength": ["vs_nifty_return", "relative_strength"],
}


class ConfidenceAnalyzer:
    def decompose_confidence(
        self,
        shap_result: Dict[str, Any],
        feature_names: List[str],
        class_label: str = "BUY",
    ) -> Dict[str, Any]:
        class_data = shap_result.get(class_label)
        if class_data is None:
            return {}

        sv = np.array(class_data["shap_values"])
        if sv.ndim == 2:
            sv = sv[0]

        base_value = class_data.get("base_value", 0.0)
        predicted_score = float(base_value + np.sum(sv))

        group_contributions = {}
        for group_name, group_features in FEATURE_GROUPS.items():
            group_shap = 0.0
            group_abs = 0.0
            matched = 0
            for i, name in enumerate(feature_names[: len(sv)]):
                if name in group_features:
                    group_shap += float(sv[i])
                    group_abs += float(abs(sv[i]))
                    matched += 1
            if matched > 0:
                group_contributions[group_name] = {
                    "total_shap": round(group_shap, 6),
                    "abs_shap": round(group_abs, 6),
                    "matched_features": matched,
                    "direction": "positive" if group_shap >= 0 else "negative",
                }

        total_abs = sum(g["abs_shap"] for g in group_contributions.values()) or 1.0
        for g in group_contributions.values():
            g["contribution_pct"] = round(g["abs_shap"] / total_abs * 100, 2)

        sorted_groups = sorted(
            group_contributions.items(),
            key=lambda x: x[1]["abs_shap"],
            reverse=True,
        )

        return {
            "class_label": class_label,
            "predicted_score": predicted_score,
            "base_value": round(float(base_value), 6),
            "shap_sum": round(float(np.sum(sv)), 6),
            "group_contributions": {
                name: data for name, data in sorted_groups
            },
            "top_groups": [name for name, _ in sorted_groups[:5]],
            "primary_driver": sorted_groups[0][0] if sorted_groups else None,
        }

    def analyze_decision_drivers(
        self,
        probs: Dict[str, float],
        shap_result: Dict[str, Any],
        feature_names: List[str],
    ) -> Dict[str, Any]:
        analysis = {}
        for cls_label in ["SELL", "HOLD", "BUY"]:
            decomposition = self.decompose_confidence(shap_result, feature_names, cls_label)
            analysis[cls_label] = {
                "probability": probs.get(cls_label.lower(), 0.0),
                "confidence_decomposition": decomposition,
            }
        return analysis

    def compute_confidence_metrics(
        self,
        probs: Dict[str, float],
    ) -> Dict[str, Any]:
        p_buy = probs.get("buy", 0.0)
        p_sell = probs.get("sell", 0.0)
        p_hold = probs.get("hold", 0.0)

        max_prob = max(p_buy, p_sell, p_hold)
        margin = max_prob - sorted([p_buy, p_sell, p_hold])[-2] if len([p_buy, p_sell, p_hold]) >= 2 else 0.0
        entropy = 0.0
        for p in [p_buy, p_sell, p_hold]:
            if p > 0:
                entropy -= p * np.log2(p)

        return {
            "max_probability": round(max_prob, 4),
            "margin_over_second": round(margin, 4),
            "entropy": round(float(entropy), 4),
            "confidence_level": "high" if max_prob >= 0.65 else "medium" if max_prob >= 0.50 else "low",
            "predicted_class": "BUY" if p_buy == max_prob else "SELL" if p_sell == max_prob else "HOLD",
        }
