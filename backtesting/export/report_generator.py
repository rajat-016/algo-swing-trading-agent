import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_metrics_report(self, metrics: Dict, window_index: int = None) -> str:
        filename = f"metrics_window_{window_index}.json" if window_index is not None else "metrics.json"
        filepath = self.reports_dir / filename

        with open(filepath, "w") as f:
            json.dump(metrics, f, indent=2, default=str)

        logger.info(f"Metrics report saved to {filepath}")
        return str(filepath)

    def generate_trades_csv(self, trade_log: List[Dict], window_index: int = None) -> str:
        filename = f"trades_window_{window_index}.csv" if window_index is not None else "trades.csv"
        filepath = self.reports_dir / filename

        if not trade_log:
            with open(filepath, "w") as f:
                f.write("No trades executed\n")
            return str(filepath)

        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=trade_log[0].keys())
            writer.writeheader()
            writer.writerows(trade_log)

        logger.info(f"Trades CSV saved to {filepath}")
        return str(filepath)

    def generate_full_report(self, all_results: List[Dict], best_model: Dict) -> str:
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        filepath = self.reports_dir / f"full_report_{timestamp}.json"

        report = {
            "generated_at": datetime.now().isoformat(),
            "total_windows": len(all_results),
            "windows": all_results,
            "best_model": best_model,
        }

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Full report saved to {filepath}")
        return str(filepath)
