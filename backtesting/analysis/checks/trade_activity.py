import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def check_trade_activity(all_results: List[Dict]) -> Dict:
    """
    Verify trades actually happened during backtest.
    Zero trades = useless backtest.

    Non-tech explanation: "The system actually bought/sold something"
    """

    total_trades = sum(r.get("total_trades", 0) for r in all_results)
    windows_with_trades = sum(
        1 for r in all_results if r.get("total_trades", 0) > 0
    )
    total_windows = len(all_results)

    windows_no_trades = total_windows - windows_with_trades

    avg_trades_per_window = total_trades / total_windows if total_windows > 0 else 0

    result = {
        "check_name": "Trade Activity",
        "status": "PASS" if total_trades > 0 else "FAIL",
        "total_trades": total_trades,
        "windows_with_trades": windows_with_trades,
        "windows_no_trades": windows_no_trades,
        "total_windows": total_windows,
        "avg_trades_per_window": avg_trades_per_window,
        "non_tech_explanation": "Trades executed during backtest"
        if total_trades > 0
        else "Zero trades - backtest is not testing anything useful",
        "issues": [],
    }

    if total_trades == 0:
        result["issues"].append(
            f"Zero trades across {total_windows} windows - model may only predict HOLD"
        )
        result["issues"].append(
            "Backtest with no trades tells nothing about strategy performance"
        )
    elif avg_trades_per_window < 1:
        result["issues"].append(
            f"Very few trades ({avg_trades_per_window:.1f} per window) - may not be enough to validate"
        )

    return result


def generate_non_tech_output(check_result: Dict) -> str:
    status_icon = "✅" if check_result["status"] == "PASS" else "❌"

    output = f"""
-------------------------------------------------------------
  TRADE ACTIVITY (THE PROBLEM)
-------------------------------------------------------------

[{'PASS' if check_result['status'] == 'PASS' else 'FAIL'}] TRADE ACTIVITY: {check_result["status"]}

   Numbers:
   - Total windows tested: {check_result["total_windows"]}
   - Windows with trades: {check_result["windows_with_trades"]}
   - Windows without trades: {check_result["windows_no_trades"]}
   - Total trades: {check_result["total_trades"]}
"""

    if check_result["total_trades"] == 0:
        output += """
   Plain English: The AI predicted "do nothing" for every single day
   across all test periods.

   Why this is a problem:
   A backtest with no trades tells you nothing about whether the
   strategy works. It's like testing a self-driving car that never
   moves -- the code runs, but it's not doing the job.
"""
    elif check_result["avg_trades_per_window"] < 1:
        output += f"""
   Warning: Very few trades ({check_result["avg_trades_per_window"]:.1f} per window).
   May not be enough data to validate the strategy.
"""

    if check_result["issues"]:
        output += "\n   Issues:\n"
        for issue in check_result["issues"]:
            output += f"   [FAIL] {issue}\n"

    output += f"\n   Verdict: {check_result['non_tech_explanation']}\n"

    return output
