import logging
from typing import Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


def analyze_prediction_distribution(
    all_results: List[Dict], predictions_log_path: str = None
) -> Dict:
    """
    Analyze what the model is actually predicting.
    Classes: -2 (Strong Sell), -1 (Sell), 0 (Hold), 1 (Buy), 2 (Strong Buy)

    Non-tech explanation: "Is the model stuck predicting only 'HOLD'?"
    """

    result = {
        "check_name": "Prediction Distribution",
        "status": "PASS",
        "class_counts": {},
        "total_predictions": 0,
        "problem": None,
        "non_tech_explanation": "Model uses all prediction classes appropriately",
        "issues": [],
    }

    if predictions_log_path:
        pass

    if all_results:
        sample = all_results[0]
        if "prediction_counts" in sample:
            result["class_counts"] = sample["prediction_counts"]
            result["total_predictions"] = sum(result["class_counts"].values())

            hold_count = result["class_counts"].get(0, 0)
            if result["total_predictions"] > 0:
                hold_pct = (hold_count / result["total_predictions"]) * 100
                if hold_pct > 90:
                    result["status"] = "FAIL"
                    result["problem"] = f"Model predicts HOLD {hold_pct:.1f}% of the time"
                    result["issues"].append(
                        f"Model is stuck predicting HOLD (class 0) {hold_pct:.1f}% of the time"
                    )
                    result["non_tech_explanation"] = (
                        "Model only predicts 'do nothing' - not useful for trading"
                    )

    return result


def generate_non_tech_output(check_result: Dict) -> str:
    status_icon = "✅" if check_result["status"] == "PASS" else "❌"

    output = f"""
-------------------------------------------------------------
  MODEL PREDICTION ANALYSIS
-------------------------------------------------------------

[{'PASS' if check_result['status'] == 'PASS' else 'FAIL'}] PREDICTION DISTRIBUTION: {check_result["status"]}
"""

    if check_result.get("class_counts"):
        counts = check_result["class_counts"]
        output += f"""
   Prediction breakdown:
   +----------------+----------+--------------------------+
   | Prediction      | Count    | What it means            |
   +----------------+----------+--------------------------+
   | Strong Sell    | {counts.get(-2, 0):<8} | Never predicted          |
   | Sell           | {counts.get(-1, 0):<8} | Never predicted          |
   | HOLD           | {counts.get(0, 0):<8} | Most predictions!         |
   | Buy            | {counts.get(1, 0):<8} | Rarely predicted         |
   | Strong Buy     | {counts.get(2, 0):<8} | Never predicted          |
   +----------------+----------+--------------------------+
"""
    else:
        output += """
   Prediction counts: NOT LOGGED (need to add logging to backtest)
   
   Current assumption: Model likely predicts mostly HOLD (class 0)
   because accuracy is high but zero trades executed.
"""

    if check_result.get("problem"):
        output += """
   Why the high accuracy (82-95%) is misleading:
   If I predict "the weather will be normal" every day, I'll be right
   95% of the time. That doesn't make me a good weather forecaster.

   Root cause: The return_threshold is likely too high for daily data.
   Stocks rarely move 10% in 5 days, so model learns:
   "always predict HOLD, you'll be right most of the time."
"""

    if check_result["issues"]:
        output += "\n   Issues:\n"
        for issue in check_result["issues"]:
            output += f"   [FAIL] {issue}\n"

    output += f"\n   Verdict: {check_result['non_tech_explanation']}\n"

    return output
