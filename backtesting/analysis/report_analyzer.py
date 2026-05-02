import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from analysis.checks.walkforward_check import check_walkforward_splits, generate_non_tech_output as wf_output
from analysis.checks.lookahead_check import check_lookahead_bias, generate_non_tech_output as la_output
from analysis.checks.trade_activity import check_trade_activity, generate_non_tech_output as ta_output
from analysis.checks.prediction_dist import analyze_prediction_distribution, generate_non_tech_output as pd_output
from analysis.checks.overfit_check import check_overfitting, generate_non_tech_output as of_output
from analysis.checks.simulator_check import check_simulator_signals, generate_non_tech_output as sim_output

logger = logging.getLogger(__name__)


class ReportAnalyzer:
    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def find_latest_report(self) -> Optional[Path]:
        """Find the most recent full_report_*.json file."""
        reports = list(self.reports_dir.glob("full_report_*.json"))
        if not reports:
            return None
        return max(reports, key=lambda p: p.stat().st_mtime)

    def load_report(self, report_path: Optional[str] = None) -> Optional[Dict]:
        """Load a backtest report JSON file."""
        if report_path:
            path = Path(report_path)
        else:
            path = self.find_latest_report()

        if not path or not path.exists():
            logger.error(f"No report found at {path}")
            return None

        with open(path, "r") as f:
            return json.load(f)

    def analyze_report(self, report_data: Dict, report_path: str = None) -> Dict:
        """Run all health checks on the report data."""
        all_results = report_data.get("windows", [])
        best_model = report_data.get("best_model", {})

        checks = {}

        checks["walkforward"] = check_walkforward_splits(
            report_path=report_path,
            log_path=str(Path(report_path).parent.parent / "logs" / "backtest.log") if report_path else None,
        )

        checks["lookahead"] = check_lookahead_bias(report_path=report_path)

        checks["trade_activity"] = check_trade_activity(all_results)

        checks["prediction_dist"] = analyze_prediction_distribution(all_results)

        checks["overfitting"] = check_overfitting(all_results)

        checks["simulator"] = check_simulator_signals()

        overall_status = "PASS" if all(
            c["status"] == "PASS" for c in checks.values()
        ) else "FAIL"

        return {
            "generated_at": datetime.now().isoformat(),
            "report_analyzed": report_path,
            "overall_status": overall_status,
            "total_windows": len(all_results),
            "all_results": all_results,
            "best_model": best_model,
            "checks": checks,
        }

    def generate_health_report(self, analysis: Dict) -> str:
        """Generate human-readable health report."""
        report = analysis
        checks = report["checks"]

        output = f"""
=============================================================
  BACKTESTING HEALTH REPORT
  Generated: {datetime.now().strftime("%Y-%m-%d %I:%M %p")}
  Report analyzed: {report.get("report_analyzed", "Unknown")}
=============================================================

-------------------------------------------------------------
  EXECUTIVE SUMMARY
-------------------------------------------------------------

Overall Verdict: {"[PASS] WORKING AS EXPECTED" if report["overall_status"] == "PASS" else "[FAIL] NOT WORKING AS EXPECTED"}
"""

        working = []
        broken = []

        for check_name, check in checks.items():
            if check["status"] == "PASS":
                working.append(f"  [PASS] {check['check_name']}")
            elif check["status"] == "FAIL":
                broken.append(f"  [FAIL] {check['check_name']}")
            else:
                broken.append(f"  [?] {check['check_name']} ({check['status']})")

        if working:
            output += "\n".join(working) + "\n"

        if broken:
            output += "\nWhat's Broken:\n"
            output += "\n".join(broken) + "\n"

        output += "\n"

        output += wf_output(checks["walkforward"])
        output += la_output(checks["lookahead"])
        output += ta_output(checks["trade_activity"])
        output += pd_output(checks["prediction_dist"])
        output += sim_output(checks["simulator"])
        output += of_output(checks["overfitting"])

        output += self._generate_stock_breakdown(report)
        output += self._generate_recommendations(report)
        output += self._generate_summary(report)

        return output

    def _generate_stock_breakdown(self, analysis: Dict) -> str:
        all_results = analysis.get("all_results", [])
        if not all_results:
            return ""

        output = """
-------------------------------------------------------------
  PER-STOCK BREAKDOWN
-------------------------------------------------------------

   Stock           | Windows | Trades | Avg Accuracy | Verdict
   ---------------|---------|---------|--------------|----------
"""

        stock_data = {}
        for r in all_results:
            sym = r.get("symbol", "Unknown")
            if sym not in stock_data:
                stock_data[sym] = {"windows": 0, "trades": 0, "accuracies": []}
            stock_data[sym]["windows"] += 1
            stock_data[sym]["trades"] += r.get("total_trades", 0)
            if "accuracy" in r:
                stock_data[sym]["accuracies"].append(r["accuracy"])

        for sym, data in sorted(stock_data.items()):
            avg_acc = (
                sum(data["accuracies"]) / len(data["accuracies"])
                if data["accuracies"]
                else 0
            )
            verdict = "[PASS]" if data["trades"] > 0 else "[FAIL] No trades"
            output += f"   {sym:<15} |    {data['windows']}    |   {data['trades']:>3}    |    {avg_acc*100:>5.1f}%    | {verdict}\n"

        return output

    def _generate_recommendations(self, analysis: Dict) -> str:
        checks = analysis.get("checks", {})

        output = """
-------------------------------------------------------------
  RECOMMENDED FIXES
-------------------------------------------------------------
"""

        if checks.get("trade_activity", {}).get("status") == "FAIL":
            output += """
[FIX 1] Lower the return threshold (MOST IMPORTANT)

   Current: return_threshold = 0.10 (10% move needed to trigger BUY)
   Problem: Daily stock moves >10% in 5 days are extremely rare
   Fix: Change to 0.03-0.05 (3-5% move) in backtest_config.yaml

   File: backtesting/config/backtest_config.yaml
   Change: labeling.return_threshold: 0.10 -> 0.03
"""

        if checks.get("simulator", {}).get("status") == "FAIL":
            output += """
[FIX 2] Fix simulator to handle all 5 classes

   Current: Only acts on prediction == 1
   Fix:
   - Class 1 or 2 -> Enter BUY position
   - Class -1 or -2 -> Exit position (if open)

   File: backtesting/backtest_engine/trade_simulator.py:77
"""

        if checks.get("prediction_dist", {}).get("status") == "FAIL":
            output += """
[FIX 3] Add prediction distribution logging

   Current: We don't know what the model predicted
   Fix: Log prediction counts during backtest

   File: backtesting/run_backtest.py (after predictions = trainer.predict())
"""

        if checks.get("overfitting", {}).get("status") in ["FAIL", "SUSPECTED"]:
            output += """
[FIX 4] Log training metrics for overfitting detection

   Current: Only test metrics are logged
   Fix: Log training accuracy/loss during model training

   File: backtesting/training/model_trainer.py (after model.fit())
"""

        return output

    def _generate_summary(self, analysis: Dict) -> str:
        checks = analysis.get("checks", {})
        trade_status = checks.get("trade_activity", {}).get("status")
        overall = analysis.get("overall_status")

        output = """
-------------------------------------------------------------
  SUMMARY FOR NON-TECHNICAL STAKEHOLDERS
-------------------------------------------------------------
"""

        if overall == "PASS":
            output += """
The backtesting system is working correctly. It has proper time splits,
no future peeking, and generates meaningful trades for analysis.
"""
        else:
            output += """
The backtesting system has good architecture (correct time splits,
no future peeking), but it's not testing anything useful because:

1. The AI never makes trades (predicts "do nothing" 100% of the time)
2. The accuracy numbers look good but are misleading
3. The simulator ignores most of the AI's predictions

Think of it like a self-driving car that's "100% safe" because it
never moves. The code works, but it's not doing the job.

After fixing the threshold and simulator, re-run the backtest to get
meaningful results.
"""

        output += """
=============================================================
"""

        return output

    def save_health_report(self, analysis: Dict, output_path: str = None) -> str:
        """Generate and save health report to file."""
        report_text = self.generate_health_report(analysis)

        if output_path is None:
            timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
            output_path = self.reports_dir / f"health_report_{timestamp}.txt"
        else:
            output_path = Path(output_path)

        with open(output_path, "w") as f:
            f.write(report_text)

        logger.info(f"Health report saved to {output_path}")
        return str(output_path)

    def run_analysis(self, report_path: Optional[str] = None) -> Dict:
        """Full analysis pipeline: load, analyze, generate report."""
        if report_path:
            report_data = self.load_report(report_path)
        else:
            report_data = self.load_report()

        if not report_data:
            logger.error("No report data to analyze")
            return {}

        analysis = self.analyze_report(report_data, report_path)
        return analysis
