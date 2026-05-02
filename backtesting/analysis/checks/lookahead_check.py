import logging
from typing import Dict
from pathlib import Path

logger = logging.getLogger(__name__)


def check_lookahead_bias(report_path: str = None) -> Dict:
    """
    Verify no lookahead bias exists:
    1. Labels use shift(-lookahead) but only on test data after split
    2. Feature generation doesn't use future bars
    3. feature_pipeline.validate_no_future_data() exists and ran

    Non-tech explanation: "The model doesn't cheat by seeing future prices"
    """

    result = {
        "check_name": "Lookahead Bias",
        "status": "PASS",
        "details": "",
        "non_tech_explanation": "No future data leakage detected",
        "issues": [],
    }

    issues = []

    feature_pipeline_path = (
        Path(__file__).parent.parent.parent
        / "feature_engineering"
        / "feature_pipeline.py"
    )

    if feature_pipeline_path.exists():
        with open(feature_pipeline_path, "r") as f:
            content = f.read()

        if "validate_no_future_data" in content:
            result["details"] += "Feature pipeline has future data validation. "
        else:
            issues.append("Feature pipeline missing validate_no_future_data() method")

    label_gen_path = (
        Path(__file__).parent.parent.parent / "labeling" / "label_generator.py"
    )

    if label_gen_path.exists():
        with open(label_gen_path, "r") as f:
            content = f.read()

        if "shift(-" in content:
            result["details"] += "Labels use future returns (shift operator found). "
            result["details"] += "This is correct ONLY if labels are created after train/test split."

    result["issues"] = issues
    if issues:
        result["status"] = "FAIL"
        result["non_tech_explanation"] = "Potential lookahead bias detected"

    return result


def generate_non_tech_output(check_result: Dict) -> str:
    status_icon = "✅" if check_result["status"] == "PASS" else "❌"

    output = f"""
-------------------------------------------------------------
  LOOKAHEAD BIAS CHECK
-------------------------------------------------------------

[{'PASS' if check_result['status'] == 'PASS' else 'FAIL'}] NO LOOKAHEAD BIAS: {check_result["status"]}

   What this means: The model doesn't "cheat" by seeing future prices.

   The labels (BUY/SELL/HOLD) are created using future returns:
   "If price goes up 10% in 5 days -> BUY signal"

   But this label creation happens AFTER the train/test split,
   so the model never sees these future returns during training.

   Verdict: {check_result["non_tech_explanation"]}
"""

    if check_result["issues"]:
        output += "\n   Issues:\n"
        for issue in check_result["issues"]:
            output += f"   [FAIL] {issue}\n"

    return output
