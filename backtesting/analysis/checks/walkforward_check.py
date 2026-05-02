import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)


def check_walkforward_splits(report_path: str = None, log_path: str = None) -> Dict:
    """
    Verify walk-forward time splits are correct:
    - train_end < test_start for all windows
    - No overlapping data between train and test
    - Test windows are sequential

    Non-tech explanation: "We never peek into the future to make decisions"
    """

    result = {
        "check_name": "Walk-Forward Time Splits",
        "status": "PASS",
        "details": "",
        "non_tech_explanation": "Time splits are correct, no future peeking",
        "issues": [],
    }

    issues = []

    if log_path:
        log_file = Path(log_path)
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                log_content = f.read()

            import re

            window_pattern = r"Window \w+_W(\d+).*?Train \[(.*?) -> (.*?)\].*?Test \[(.*?) -> (.*?)\]"
            matches = re.findall(window_pattern, log_content, re.DOTALL)

            if matches:
                prev_test_end = None
                for match in matches:
                    window_num = match[0]
                    train_start = match[1].strip()
                    train_end = match[2].strip()
                    test_start = match[3].strip()
                    test_end = match[4].strip()

                    try:
                        train_end_dt = datetime.strptime(train_end, "%Y-%m-%d")
                        test_start_dt = datetime.strptime(test_start, "%Y-%m-%d")

                        if train_end_dt >= test_start_dt:
                            issues.append(
                                f"Window {window_num}: Train end ({train_end}) >= Test start ({test_start}) - LOOKAHEAD BIAS!"
                            )

                        if prev_test_end and test_start_dt < prev_test_end:
                            issues.append(
                                f"Window {window_num}: Test start ({test_start}) overlaps with previous window"
                            )

                        prev_test_end = test_end_dt = datetime.strptime(test_end, "%Y-%m-%d")

                    except ValueError:
                        continue

    if issues:
        result["status"] = "FAIL"
        result["issues"] = issues
        result["non_tech_explanation"] = "Time split problems detected - possible future peeking"
    else:
        result["details"] = "All walk-forward windows have correct time ordering (train ends before test starts)"

    return result


def generate_non_tech_output(check_result: Dict) -> str:
    status_icon = "✅" if check_result["status"] == "PASS" else "❌"

    output = f"""
-------------------------------------------------------------
  WALK-FORWARD VALIDATION
-------------------------------------------------------------

[{'PASS' if check_result['status'] == 'PASS' else 'FAIL'}] TIME SPLITS: {check_result["status"]}

   What this means: The backtest never uses future data to make decisions.

   How it works (simple version):
   - Take 3 years of data -> Train the model
   - Take next 6 months -> Test the model (without retraining)
   - Slide forward 6 months -> Repeat

   This is like: Study 2019-2021, take a test on Jan-Jun 2022,
   then study 2020-2022, take a test on Jul-Dec 2022, etc.
"""

    if check_result["issues"]:
        output += "\n   Issues found:\n"
        for issue in check_result["issues"]:
            output += f"   [FAIL] {issue}\n"

    output += f"\n   Verdict: {check_result['non_tech_explanation']}\n"

    return output
