from typing import Any, Optional
from core.logging import logger


REGIME_FEATURE_ALIGNMENT: dict[str, list[str]] = {
    "bull_trend": ["momentum", "trend", "breakout", "relative_strength", "volume_expansion", "price_expansion", "sector_momentum"],
    "bear_trend": ["defensive", "mean_reversion", "put", "bearish", "volatility"],
    "high_volatility": ["volatility", "atr", "stop_loss", "risk", "range", "compression"],
    "low_volatility": ["breakout", "compression", "momentum", "volume", "relative_strength"],
    "breakout": ["breakout", "volume", "momentum", "relative_strength", "price_expansion", "volatility_compression"],
    "sideways": ["mean_reversion", "range", "support", "resistance", "oscillator"],
    "event_driven": ["event", "news", "sentiment", "gap", "volume_spike"],
    "mean_reversion": ["mean_reversion", "oversold", "overbought", "rsi", "bbands", "support", "resistance"],
}

MOMENTUM_FEATURE_KEYWORDS: list[str] = [
    "momentum", "trend", "adx", "rsi", "macd", "relative_strength",
    "price_expansion", "volume_expansion", "breakout",
]


class FailureAnalyzer:
    def analyze_failure(self, prediction: Optional[dict] = None,
                         top_positive: Optional[list] = None,
                         top_negative: Optional[list] = None,
                         regime_context: Optional[dict] = None,
                         stock_data: Optional[dict] = None) -> dict:
        regime_mismatch = self.analyze_regime_mismatch(regime_context, prediction)
        vol_expansion = self.analyze_volatility_expansion(regime_context)
        weak_confirmations = self.detect_weak_confirmations(prediction, top_positive, top_negative)
        stop_loss_analysis = self.analyze_stop_loss(stock_data, regime_context)
        weak_momentum = self.detect_weak_momentum(regime_context, top_positive)
        regime_instability = self.analyze_regime_instability(regime_context)
        feature_alignment = self.analyze_feature_alignment(top_positive, regime_context)

        failure_reasons = []
        severity = "low"

        if regime_mismatch.get("mismatch_detected"):
            failure_reasons.append(regime_mismatch["description"])
        if vol_expansion.get("expansion_detected"):
            failure_reasons.append(vol_expansion["description"])
        if weak_confirmations.get("weak_confirmations_detected"):
            failure_reasons.append(weak_confirmations["description"])
        if stop_loss_analysis.get("sl_contributor"):
            failure_reasons.append(stop_loss_analysis["description"])
        if weak_momentum.get("weak_momentum_detected"):
            failure_reasons.append(weak_momentum["description"])
        if regime_instability.get("instability_detected"):
            failure_reasons.append(regime_instability["description"])
        if feature_alignment.get("poor_alignment_detected"):
            failure_reasons.append(feature_alignment["description"])

        if len(failure_reasons) >= 3:
            severity = "high"
        elif len(failure_reasons) >= 1:
            severity = "medium"

        return {
            "failure_detected": len(failure_reasons) > 0,
            "failure_reasons": failure_reasons,
            "severity": severity,
            "regime_mismatch": regime_mismatch,
            "volatility_expansion": vol_expansion,
            "weak_confirmations": weak_confirmations,
            "stop_loss_analysis": stop_loss_analysis,
            "weak_momentum": weak_momentum,
            "regime_instability": regime_instability,
            "feature_alignment": feature_alignment,
            "primary_cause": failure_reasons[0] if failure_reasons else None,
        }

    def analyze_regime_mismatch(self, regime_context: Optional[dict],
                                 prediction: Optional[dict] = None) -> dict:
        result = {
            "mismatch_detected": False,
            "description": None,
            "entry_regime": None,
            "current_regime": None,
            "regime_risk_level": None,
            "confidence_degraded": False,
        }

        if not regime_context:
            return result

        regime = regime_context.get("regime", "unknown")
        risk_level = regime_context.get("risk_level", "medium")
        stability = regime_context.get("stability", "moderate")
        trans_data = regime_context.get("transition_data", {}) or {}

        result["current_regime"] = regime
        result["regime_risk_level"] = risk_level
        result["confidence_degraded"] = trans_data.get("confidence_degraded", False)

        decision = prediction.get("decision") if prediction else None

        if risk_level == "high":
            if decision == "BUY":
                result["mismatch_detected"] = True
                result["description"] = (
                    f"BUY decision in high-risk {regime} regime. "
                    f"High-volatility or bear regimes increase failure probability for long positions."
                )
            elif decision == "SELL":
                result["mismatch_detected"] = True
                result["description"] = (
                    f"SELL decision in {regime} regime. Consider trend strength and mean-reversion risk."
                )

        bearish_regimes = {"bear_trend", "high_volatility", "event_driven"}
        bullish_regimes = {"bull_trend", "breakout", "low_volatility"}

        if regime in bearish_regimes and decision == "BUY":
            result["mismatch_detected"] = True
            result["description"] = (
                f"Regime mismatch: BUY in {regime.replace('_', ' ')} environment. "
                f"Bearish or volatile regimes typically unfavorable for long positions."
            )

        if regime in bullish_regimes and decision == "SELL":
            result["mismatch_detected"] = True
            result["description"] = (
                f"Regime mismatch: SELL in {regime.replace('_', ' ')} environment. "
                f"Bullish regimes typically unfavorable for short positions."
            )

        if stability == "unstable":
            result["mismatch_detected"] = True
            if not result["description"]:
                result["description"] = (
                    f"Unstable {regime} regime increases execution risk. "
                    f"Rapid regime changes can invalidate trade thesis."
                )

        if trans_data.get("is_transitioning") and not result["description"]:
            result["mismatch_detected"] = True
            result["description"] = (
                f"Market transitioning between regimes. "
                f"Trade thesis may be invalidated by upcoming regime change."
            )

        return result

    def analyze_volatility_expansion(self, regime_context: Optional[dict]) -> dict:
        result = {
            "expansion_detected": False,
            "description": None,
            "volatility_regime": None,
            "spike_detected": False,
            "spike_severity": None,
        }

        if not regime_context:
            return result

        vol_context = regime_context.get("volatility_context", {}) or {}
        trans_data = regime_context.get("transition_data", {}) or {}

        regime = regime_context.get("regime", "")

        atr_pct = vol_context.get("atr_pct")
        is_high_vol = "high_vol" in regime or regime == "high_volatility"
        spike_detected = trans_data.get("vol_spike_detected", False)
        spike_severity = trans_data.get("vol_spike_severity")

        result["volatility_regime"] = "high" if is_high_vol else "low" if regime == "low_volatility" else "normal"
        result["spike_detected"] = spike_detected
        result["spike_severity"] = spike_severity

        if is_high_vol or spike_detected:
            result["expansion_detected"] = True
            parts = ["Volatility expansion detected"]
            if is_high_vol:
                parts.append(f"market in {regime.replace('_', ' ')}")
            if atr_pct is not None:
                parts.append(f"ATR at {atr_pct:.2%}")
            if spike_detected and spike_severity:
                parts.append(f"spike severity: {spike_severity}")
            result["description"] = ". ".join(parts) + "."

        return result

    def detect_weak_confirmations(self, prediction: Optional[dict],
                                   top_positive: Optional[list],
                                   top_negative: Optional[list]) -> dict:
        result = {
            "weak_confirmations_detected": False,
            "description": None,
            "confidence_weak": False,
            "margin_thin": False,
            "conflicting_features": False,
            "feature_agreement": None,
        }

        if not prediction:
            return result

        level = prediction.get("confidence_level", "low")
        confidence = prediction.get("confidence", 0.0)
        margin = prediction.get("margin_over_second", 1.0)
        entropy = prediction.get("entropy", 0.0)

        if level == "low":
            result["confidence_weak"] = True
            result["weak_confirmations_detected"] = True
        elif level == "medium":
            result["confidence_weak"] = True

        if margin is not None and margin < 0.1:
            result["margin_thin"] = True
            result["weak_confirmations_detected"] = True

        if entropy is not None and entropy > 1.0:
            result["weak_confirmations_detected"] = True

        if top_positive and top_negative:
            neg_strength = sum(abs(f.get("shap_value", 0)) for f in top_negative[:3])
            pos_strength = sum(abs(f.get("shap_value", 0)) for f in top_positive[:3])
            if pos_strength > 0:
                ratio = neg_strength / pos_strength
                result["feature_agreement"] = round(1.0 - min(ratio, 1.0), 4)
                if ratio > 0.5:
                    result["conflicting_features"] = True
                    result["weak_confirmations_detected"] = True

        if result["weak_confirmations_detected"]:
            reasons = []
            if result["confidence_weak"]:
                reasons.append(f"confidence level is {level} ({confidence:.2f})")
            if result["margin_thin"]:
                reasons.append(f"thin margin of {margin:.4f} between top classes")
            if result["conflicting_features"]:
                reasons.append("significant opposing feature contributions")
            if entropy is not None and entropy > 1.0:
                reasons.append(f"high prediction entropy ({entropy:.2f})")

            result["description"] = "Weak trade confirmations: " + "; ".join(reasons) + "."

        return result

    def detect_weak_momentum(self, regime_context: Optional[dict],
                              top_positive: Optional[list] = None) -> dict:
        result = {
            "weak_momentum_detected": False,
            "description": None,
            "trend_strength": None,
            "adx_value": None,
            "volume_confirmation": None,
            "momentum_in_features": None,
        }

        if not regime_context:
            return result

        trend_ctx = regime_context.get("trend_context", {}) or {}
        vol_ctx = regime_context.get("volatility_context", {}) or {}
        trans_data = regime_context.get("transition_data", {}) or {}

        adx = trend_ctx.get("adx")
        if adx is not None:
            result["adx_value"] = adx
            result["trend_strength"] = "strong" if adx >= 25 else "moderate" if adx >= 20 else "weak"
            if adx < 20:
                result["weak_momentum_detected"] = True

        vol_decline = trans_data.get("volume_decline_detected", trans_data.get("volume_drop_detected", False))
        if vol_decline:
            result["volume_confirmation"] = "declining"
            result["weak_momentum_detected"] = True
        elif vol_ctx.get("volume_trend") == "falling":
            result["volume_confirmation"] = "declining"
            result["weak_momentum_detected"] = True

        if top_positive:
            feature_names = [f.get("feature", "").lower() for f in top_positive]
            has_momentum = any(
                any(kw in name for kw in MOMENTUM_FEATURE_KEYWORDS)
                for name in feature_names
            )
            result["momentum_in_features"] = has_momentum
            if not has_momentum and len(feature_names) > 0:
                result["weak_momentum_detected"] = True

        if result["weak_momentum_detected"]:
            parts = ["Weak momentum confirmation"]
            if result.get("adx_value") is not None and result["adx_value"] < 20:
                parts.append(f"low trend strength (ADX={result['adx_value']:.1f})")
            if result.get("volume_confirmation") == "declining":
                parts.append("declining volume")
            if result.get("momentum_in_features") is False:
                parts.append("no momentum-related features in top drivers")
            result["description"] = ". ".join(parts) + "."

        return result

    def analyze_regime_instability(self, regime_context: Optional[dict]) -> dict:
        result = {
            "instability_detected": False,
            "description": None,
            "stability_label": None,
            "is_transitioning": False,
            "likely_next_regime": None,
            "transition_probability": None,
            "vol_spike_alert": False,
            "regime_flip_risk": False,
        }

        if not regime_context:
            return result

        stability = regime_context.get("stability", "moderate")
        trans_data = regime_context.get("transition_data", {}) or {}

        result["stability_label"] = stability
        result["is_transitioning"] = trans_data.get("is_transitioning", False)
        result["likely_next_regime"] = trans_data.get("most_likely_next_regime")
        result["transition_probability"] = trans_data.get("most_likely_next_probability")
        result["vol_spike_alert"] = trans_data.get("vol_spike_detected", False)

        reasons = []

        if stability == "unstable":
            result["instability_detected"] = True
            reasons.append(f"market regime is unstable")

        if trans_data.get("is_transitioning"):
            result["instability_detected"] = True
            next_regime = trans_data.get("most_likely_next_regime", "unknown")
            prob = trans_data.get("most_likely_next_probability")
            prob_str = f" ({prob:.0%} probability)" if prob else ""
            reasons.append(f"transitioning to {next_regime}{prob_str}")

        if trans_data.get("vol_spike_detected"):
            result["instability_detected"] = True
            reasons.append("volatility spike detected during trade")

        current_regime = regime_context.get("regime", "")
        likely_next = trans_data.get("most_likely_next_regime", "")
        if likely_next and current_regime:
            is_flip = (
                ("bull" in current_regime and "bear" in likely_next)
                or ("bear" in current_regime and "bull" in likely_next)
            )
            if is_flip:
                result["regime_flip_risk"] = True
                result["instability_detected"] = True
                reasons.append("regime flip risk (bull↔bear transition)")

        if result["instability_detected"]:
            result["description"] = "Regime instability: " + "; ".join(reasons) + "."

        return result

    def analyze_feature_alignment(self, top_positive: Optional[list],
                                   regime_context: Optional[dict]) -> dict:
        result = {
            "poor_alignment_detected": False,
            "description": None,
            "regime_inappropriate_features": [],
            "missing_regime_features": [],
            "regime_alignment_score": None,
        }

        if not top_positive or not regime_context:
            return result

        regime = regime_context.get("regime", "unknown")
        feature_names = [f.get("feature", "").lower() for f in top_positive]
        appropriate = REGIME_FEATURE_ALIGNMENT.get(regime, [])

        regime_inappropriate = [
            f for f in feature_names
            if f and not any(akw in f for akw in appropriate)
        ]
        missing = [
            af for af in appropriate[:5]
            if not any(af in fn for fn in feature_names)
        ]

        result["regime_inappropriate_features"] = regime_inappropriate[:5]
        result["missing_regime_features"] = missing[:5]

        if feature_names:
            aligned = len([f for f in feature_names if any(akw in f for akw in appropriate)])
            result["regime_alignment_score"] = round(aligned / len(feature_names), 4)

        if regime_inappropriate and len(regime_inappropriate) >= len(feature_names) * 0.5:
            result["poor_alignment_detected"] = True
            result["description"] = (
                f"Poor feature alignment for {regime.replace('_', ' ')} regime. "
                f"Top features {', '.join(regime_inappropriate[:3])} are not regime-appropriate. "
                f"Missing regime-aligned features: {', '.join(missing[:3])}."
            )

        return result

    def analyze_stop_loss(self, stock_data: Optional[dict],
                           regime_context: Optional[dict]) -> dict:
        result = {
            "sl_contributor": False,
            "description": None,
            "exit_due_to_sl": False,
            "volatility_contributor": False,
            "regime_contributor": False,
        }

        if not stock_data:
            return result

        exit_reason = stock_data.get("exit_reason")
        pnl_pct = stock_data.get("pnl_percentage")

        if exit_reason == "SL":
            result["exit_due_to_sl"] = True
            result["sl_contributor"] = True

            regime = regime_context.get("regime", "unknown") if regime_context else "unknown"
            trans_data = regime_context.get("transition_data", {}) if regime_context else {}
            spike_detected = trans_data.get("vol_spike_detected", False)

            if spike_detected or regime in ("high_volatility", "event_driven"):
                result["volatility_contributor"] = True
                result["description"] = (
                    f"Stop-loss triggered in {regime.replace('_', ' ')} environment. "
                    f"Volatility expansion likely contributed to SL breach."
                )
            elif regime in ("bear_trend", "sideways"):
                result["regime_contributor"] = True
                result["description"] = (
                    f"Stop-loss triggered in {regime.replace('_', ' ')} regime. "
                    f"Regime conditions were unfavorable for the trade direction."
                )
            else:
                result["description"] = (
                    f"Stop-loss triggered. Review position sizing and SL placement."
                )

        elif pnl_pct is not None and pnl_pct < 0:
            if regime_context:
                regime = regime_context.get("regime", "unknown")
                risk_level = regime_context.get("risk_level", "medium")
                if risk_level == "high":
                    result["sl_contributor"] = True
                    result["description"] = (
                        f"Loss incurred in {risk_level}-risk {regime} environment. "
                        f"Regime conditions may have contributed to adverse price movement."
                    )

        return result
