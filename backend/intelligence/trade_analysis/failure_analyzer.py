from typing import Any, Optional
from core.logging import logger


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

        if len(failure_reasons) >= 2:
            severity = "high"
        elif len(failure_reasons) == 1:
            severity = "medium"

        return {
            "failure_detected": len(failure_reasons) > 0,
            "failure_reasons": failure_reasons,
            "severity": severity,
            "regime_mismatch": regime_mismatch,
            "volatility_expansion": vol_expansion,
            "weak_confirmations": weak_confirmations,
            "stop_loss_analysis": stop_loss_analysis,
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
