import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


def check_simulator_signals() -> Dict:
    """
    Verify simulator handles all prediction classes.
    Current: Only handles prediction == 1 (moderate buy)
    Problem: Ignores classes -2, -1, 0, 2

    Non-tech explanation: "The strategy ignores 4 out of 5 signals"
    """

    result = {
        "check_name": "Simulator Signal Handling",
        "status": "FAIL",
        "details": "",
        "non_tech_explanation": "Simulator ignores most prediction signals",
        "issues": [],
    }

    simulator_path = (
        Path(__file__).parent.parent.parent
        / "backtest_engine"
        / "trade_simulator.py"
    )

    if simulator_path.exists():
        with open(simulator_path, "r") as f:
            content = f.read()

        if "prediction == 1" in content:
            result["issues"].append(
                "Simulator only acts on prediction == 1 (moderate buy)"
            )
            result["issues"].append(
                "Ignores: -2 (Strong Sell), -1 (Sell), 0 (Hold), 2 (Strong Buy)"
            )
            result["details"] = "Only one prediction class triggers trades"
        elif "prediction" in content:
            result["status"] = "PASS"
            result["non_tech_explanation"] = "Simulator handles multiple prediction classes"
            result["details"] = "Prediction handling found in simulator"

    return result


def generate_non_tech_output(check_result: Dict) -> str:
    status_icon = "✅" if check_result["status"] == "PASS" else "❌"

    output = f"""
-------------------------------------------------------------
  SIMULATOR SIGNAL HANDLING
-------------------------------------------------------------

[{'PASS' if check_result['status'] == 'PASS' else 'FAIL'}] SIMULATOR SIGNAL HANDLING: {check_result["status"]}
"""

    if check_result["status"] == "FAIL":
        output += """
   The system can predict 5 actions:
   1. Strong Sell  <- Ignored!
   2. Sell         <- Ignored!
   3. Hold         <- Correctly ignored
   4. Buy          <- Used (but rarely predicted)
   5. Strong Buy   <- Ignored!

   Fix needed: The simulator needs to handle all 5 signals:
   - Classes 1 or 2 -> Enter BUY position
   - Classes -1 or -2 -> Exit position (if open)
"""

    if check_result["issues"]:
        output += "\n   Issues:\n"
        for issue in check_result["issues"]:
            output += f"   [FAIL] {issue}\n"

    output += f"\n   Verdict: {check_result['non_tech_explanation']}\n"

    return output
