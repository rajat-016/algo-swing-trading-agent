from typing import Any, Optional
from core.logging import logger


class ReasoningEngine:
    def generate_trade_reasoning(self, prediction: Optional[dict] = None,
                                  top_positive: Optional[list] = None,
                                  top_negative: Optional[list] = None,
                                  regime_context: Optional[dict] = None,
                                  stock_data: Optional[dict] = None,
                                  outcome: Optional[str] = None) -> dict:
        entry_rationale = self._generate_entry_rationale(
            prediction, top_positive, regime_context
        )
        outcome_analysis = self._generate_outcome_analysis(
            outcome, prediction, regime_context, stock_data
        )
        risk_factors = self._identify_risk_factors(
            prediction, top_positive, top_negative, regime_context
        )
        confidence_assessment = self._assess_confidence(
            prediction, top_positive, top_negative
        )
        summary = self._generate_summary_text(
            prediction, outcome, entry_rationale, outcome_analysis, risk_factors
        )

        return {
            "entry_rationale": entry_rationale,
            "outcome_analysis": outcome_analysis,
            "risk_factors": risk_factors,
            "confidence_assessment": confidence_assessment,
            "summary": summary,
        }

    def _generate_entry_rationale(self, prediction: Optional[dict],
                                   top_positive: Optional[list],
                                   regime_context: Optional[dict]) -> dict:
        rationale = {"primary_reason": None, "supporting_factors": [], "regime_alignment": None}

        if prediction:
            decision = prediction.get("decision", "UNKNOWN")
            level = prediction.get("confidence_level", "unknown")
            rationale["primary_reason"] = f"Model predicted {decision} with {level} confidence"

        if top_positive:
            rationale["supporting_factors"] = [
                f["feature"] for f in top_positive[:3]
            ]

        if regime_context:
            regime = regime_context.get("regime", "unknown")
            rationale["regime_alignment"] = f"Market in {regime} regime"

        return rationale

    def _generate_outcome_analysis(self, outcome: Optional[str],
                                    prediction: Optional[dict],
                                    regime_context: Optional[dict],
                                    stock_data: Optional[dict]) -> dict:
        analysis = {
            "outcome": outcome or "unknown",
            "exit_reason": None,
            "pnl_analysis": None,
            "regime_impact": None,
        }

        if stock_data:
            analysis["exit_reason"] = stock_data.get("exit_reason")
            pnl_pct = stock_data.get("pnl_percentage")
            if pnl_pct is not None:
                if pnl_pct > 0:
                    analysis["pnl_analysis"] = f"Profitable trade: +{pnl_pct:.2f}%"
                elif pnl_pct < 0:
                    analysis["pnl_analysis"] = f"Loss-making trade: {pnl_pct:.2f}%"
                else:
                    analysis["pnl_analysis"] = "Break-even trade"

        if regime_context:
            stability = regime_context.get("stability", "unknown")
            risk_level = regime_context.get("risk_level", "medium")
            if risk_level == "high":
                analysis["regime_impact"] = f"Trade executed in high-risk {stability} regime"
            elif outcome == "LOSS" and risk_level == "high":
                analysis["regime_impact"] = "High-risk regime contributed to trade failure"

        return analysis

    def _identify_risk_factors(self, prediction: Optional[dict],
                                top_positive: Optional[list],
                                top_negative: Optional[list],
                                regime_context: Optional[dict]) -> list:
        factors = []

        if prediction:
            level = prediction.get("confidence_level")
            if level == "low":
                factors.append("Low model confidence")
            elif level == "medium":
                factors.append("Moderate model confidence - limited conviction")

            margin = prediction.get("margin_over_second", 1.0)
            if margin is not None and margin < 0.1:
                factors.append("Thin confidence margin between top classes")

        if top_negative and top_positive:
            neg_strength = sum(abs(f.get("shap_value", 0)) for f in top_negative[:3])
            pos_strength = sum(abs(f.get("shap_value", 0)) for f in top_positive[:3])
            if neg_strength > pos_strength * 0.5:
                factors.append("Significant negative feature contributions opposing the decision")

        if regime_context:
            risk = regime_context.get("risk_level")
            if risk == "high":
                factors.append("High-risk market environment")
            stability = regime_context.get("stability")
            if stability == "unstable":
                factors.append("Unstable market regime - elevated transition risk")
            trans_data = regime_context.get("transition_data", {}) or {}
            if trans_data.get("vol_spike_detected"):
                factors.append("Volatility spike detected in market")
            if trans_data.get("is_transitioning"):
                factors.append("Market is transitioning between regimes")

        return factors

    def _assess_confidence(self, prediction: Optional[dict],
                            top_positive: Optional[list],
                            top_negative: Optional[list]) -> dict:
        assessment = {"verdict": "insufficient_data", "strength": 0.0, "details": []}

        if not prediction:
            return assessment

        confidence = prediction.get("confidence", 0.0)
        level = prediction.get("confidence_level", "low")
        entropy = prediction.get("entropy", 1.0)

        if confidence >= 0.65:
            assessment["verdict"] = "strong"
            assessment["strength"] = confidence
            assessment["details"].append(f"High confidence ({confidence:.2f})")
        elif confidence >= 0.50:
            assessment["verdict"] = "moderate"
            assessment["strength"] = confidence
            assessment["details"].append(f"Moderate confidence ({confidence:.2f})")
        else:
            assessment["verdict"] = "weak"
            assessment["strength"] = confidence
            assessment["details"].append(f"Low confidence ({confidence:.2f})")

        if entropy is not None and entropy < 0.5:
            assessment["details"].append("Low prediction entropy - model was decisive")
        elif entropy is not None and entropy > 1.0:
            assessment["details"].append("High prediction entropy - model was uncertain")

        pos_count = len(top_positive) if top_positive else 0
        neg_count = len(top_negative) if top_negative else 0
        if pos_count > 0:
            assessment["details"].append(f"{pos_count} supporting features identified")
        if neg_count > 0:
            assessment["details"].append(f"{neg_count} opposing features identified")

        return assessment

    def _generate_summary_text(self, prediction: Optional[dict],
                                outcome: Optional[str],
                                entry_rationale: dict,
                                outcome_analysis: dict,
                                risk_factors: list) -> str:
        parts = []

        decision = prediction.get("decision", "UNKNOWN") if prediction else "UNKNOWN"
        parts.append(f"Trade decision: {decision}.")

        primary = entry_rationale.get("primary_reason")
        if primary:
            parts.append(primary.capitalize() + ".")

        if outcome:
            outcome_label = "WIN" if outcome == "WIN" else "LOSS" if outcome == "LOSS" else outcome
            parts.append(f"Outcome: {outcome_label}.")

        pnl = outcome_analysis.get("pnl_analysis")
        if pnl:
            parts.append(pnl + ".")

        regime_alignment = entry_rationale.get("regime_alignment")
        if regime_alignment:
            parts.append(regime_alignment.capitalize() + ".")

        if risk_factors:
            parts.append(f"Risk factors: {'; '.join(risk_factors[:3])}.")

        return " ".join(parts)
