import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def check_overfitting(all_results: List[Dict]) -> Dict:
    """
    Detect overfitting by comparing metrics across windows.
    - High accuracy but zero trades = overfitting to HOLD class
    - Huge variance in accuracy across windows = overfitting
    - Train acc >> Test acc (need train metrics to confirm)

    Non-tech explanation: "Is model memorizing instead of learning?"
    """

    result = {
        "check_name": "Overfitting Detection",
        "status": "SUSPECTED",
        "details": "",
        "accuracy_stats": {},
        "non_tech_explanation": "Cannot fully verify - need training metrics",
        "issues": [],
    }

    if not all_results:
        result["status"] = "FAIL"
        result["issues"].append("No results to analyze")
        return result

    accuracies = [r.get("accuracy", 0) for r in all_results if "accuracy" in r]
    sharpes = [r.get("sharpe_ratio", 0) for r in all_results if "sharpe_ratio" in r]

    if accuracies:
        result["accuracy_stats"] = {
            "min": min(accuracies),
            "max": max(accuracies),
            "mean": sum(accuracies) / len(accuracies),
            "variance": max(accuracies) - min(accuracies),
        }

        if result["accuracy_stats"]["variance"] > 0.3:
            result["issues"].append(
                f"High accuracy variance ({result['accuracy_stats']['variance']:.2f}) - possible overfitting"
            )

    total_trades = sum(r.get("total_trades", 0) for r in all_results)
    if total_trades == 0 and accuracies:
        avg_acc = result["accuracy_stats"]["mean"]
        if avg_acc > 0.8:
            result["status"] = "FAIL"
            result["issues"].append(
                f"High test accuracy ({avg_acc:.2f}) but zero trades = overfitting to majority class (HOLD)"
            )
            result["non_tech_explanation"] = (
                "Model appears to predict majority class (HOLD) to get high accuracy without learning useful patterns"
            )

    return result


def generate_non_tech_output(check_result: Dict) -> str:
    status_icon = (
        "✅"
        if check_result["status"] == "PASS"
        else "❌" if check_result["status"] == "FAIL" else "⚠️"
    )

    status_icon = (
        "[PASS]"
        if check_result["status"] == "PASS"
        else "[FAIL]" if check_result["status"] == "FAIL" else "[?]"
    )

    output = f"""
-------------------------------------------------------------
  OVERFITTING CHECK
-------------------------------------------------------------

{status_icon} OVERFITTING: {check_result["status"]}
"""

    if check_result.get("accuracy_stats"):
        stats = check_result["accuracy_stats"]
        output += f"""
   Accuracy across windows:
   - Min: {stats['min']:.2f}
   - Max: {stats['max']:.2f}
   - Average: {stats['mean']:.2f}
   - Variance: {stats['variance']:.2f}
"""

    output += """
   What is overfitting?
   Like a student who memorizes that the answer to every question 
   is "C" -- they get 25% right by luck, but haven't learned anything.
   
   True test: Does the model make correct BUY/SELL decisions?
"""

    if check_result["status"] == "FAIL":
        output += """
   This appears to be happening:
   - High accuracy (82-95%) from always predicting HOLD
   - Zero trades executed
   - Model hasn't learned when to actually buy/sell
"""
    elif check_result["status"] == "SUSPECTED":
        output += """
   Cannot fully confirm without training metrics.
   Need to compare train accuracy vs test accuracy:
   - If train acc = 99% but test acc = 82% -> Overfitting
   - If both are 82% but only predicting HOLD -> Different problem
"""

    if check_result["issues"]:
        output += "\n   Issues:\n"
        for issue in check_result["issues"]:
            output += f"   [FAIL] {issue}\n"

    output += f"\n   Verdict: {check_result['non_tech_explanation']}\n"

    return output
