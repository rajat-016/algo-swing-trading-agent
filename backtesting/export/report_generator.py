import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
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

        all_keys = set()
        for trade in trade_log:
            all_keys.update(trade.keys())

        # Maintain a logical order for readability
        ordered_keys = [k for k in ["action", "symbol", "datetime", "price", "qty", "pnl", "pnl_pct", "reason"] if k in all_keys]
        for k in sorted(all_keys):
            if k not in ordered_keys:
                ordered_keys.append(k)

        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=ordered_keys, extrasaction="ignore")
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

    def generate_executive_summary(self, all_results: List[Dict], best_model: Dict) -> str:
        """Generate executive summary with key strategy metrics."""
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        filepath = self.reports_dir / f"executive_summary_{timestamp}.txt"

        total_trades = sum(r.get("total_trades", 0) for r in all_results)
        avg_sharpe = sum(r.get("sharpe_ratio", 0) for r in all_results) / len(all_results) if all_results else 0
        avg_dd = sum(r.get("max_drawdown", 0) for r in all_results) / len(all_results) if all_results else 0
        avg_precision_buy = sum(r.get("precision_buy", 0) for r in all_results) / len(all_results) if all_results else 0

        expectancy_data = best_model.get("trade_expectancy", {})

        # NEW: Aggregate optimal thresholds
        thresholds = [r.get("optimal_confidence_threshold", {}) for r in all_results]
        valid_thresholds = [t for t in thresholds if t.get("trade_count", 0) > 0]
        avg_optimal_threshold = (
            sum(t["optimal_threshold"] for t in valid_thresholds) / len(valid_thresholds)
            if valid_thresholds else 0.50
        )

        lines = [
            "=" * 60,
            "EXECUTIVE SUMMARY - WALK-FORWARD BACKTEST",
            "=" * 60,
            f"Generated: {datetime.now().isoformat()}",
            f"Total Windows: {len(all_results)}",
            f"Total Trades: {total_trades}",
            "",
            "--- Strategy Metrics ---",
            f"Avg Sharpe Ratio: {avg_sharpe:.2f} (Target: >= 1.0)",
            f"Avg Max Drawdown: {avg_dd:.2%} (Target: <= 25%)",
            f"Avg Precision(BUY): {avg_precision_buy:.2%}",
            "",
            "--- Optimal Confidence Threshold ---",
            f"Average Optimal Threshold: {avg_optimal_threshold:.2f}",
            f"Windows with Valid Threshold: {len(valid_thresholds)}/{len(all_results)}",
            "",
            "--- Trade Expectancy ---",
            f"Expectancy: {expectancy_data.get('expectancy', 0):.2f}",
            f"Avg Win: {expectancy_data.get('avg_win', 0):.2f}",
            f"Avg Loss: {expectancy_data.get('avg_loss', 0):.2f}",
            f"Win Rate: {expectancy_data.get('win_rate', 0):.2%}",
            "",
            "--- Best Model (Selected) ---",
            f"Symbol: {best_model.get('symbol', 'N/A')}",
            f"Window: {best_model.get('window_index', 'N/A')}",
            f"Sharpe: {best_model.get('sharpe_ratio', 0):.2f}",
            f"DD: {best_model.get('max_drawdown', 0):.2%}",
            f"Precision(BUY): {best_model.get('precision_buy', 0):.2%}",
            "=" * 60,
        ]

        summary = "\n".join(lines)
        with open(filepath, "w") as f:
            f.write(summary)

        logger.info(f"Executive summary saved to {filepath}")
        return str(filepath)

    def generate_alpha_validation(self, all_results: List[Dict]) -> str:
        """Generate alpha validation report with per-symbol and confidence analysis."""
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        filepath = self.reports_dir / f"alpha_validation_{timestamp}.json"

        # Per-symbol performance
        symbol_stats = {}
        for r in all_results:
            sym = r.get("symbol", "UNKNOWN")
            if sym not in symbol_stats:
                symbol_stats[sym] = {"trades": 0, "sharpe": [], "precision_buy": []}
            symbol_stats[sym]["trades"] += r.get("total_trades", 0)
            symbol_stats[sym]["sharpe"].append(r.get("sharpe_ratio", 0))
            symbol_stats[sym]["precision_buy"].append(r.get("precision_buy", 0))

        # Aggregate
        for sym in symbol_stats:
            stats = symbol_stats[sym]
            stats["avg_sharpe"] = sum(stats["sharpe"]) / len(stats["sharpe"]) if stats["sharpe"] else 0
            stats["avg_precision_buy"] = sum(stats["precision_buy"]) / len(stats["precision_buy"]) if stats["precision_buy"] else 0
            del stats["sharpe"]
            del stats["precision_buy"]

        # Confidence bucket analysis (from first result that has it)
        confidence_buckets = {}
        for r in all_results:
            if "confidence_buckets" in r:
                confidence_buckets = r["confidence_buckets"]
                break

        report = {
            "generated_at": datetime.now().isoformat(),
            "total_windows": len(all_results),
            "per_symbol_stats": symbol_stats,
            "confidence_bucket_analysis": confidence_buckets,
            "alpha_validated": any(r.get("sharpe_ratio", 0) >= 1.2 for r in all_results),
        }

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Alpha validation report saved to {filepath}")
        return str(filepath)

    def generate_decision_report(
        self,
        all_results: List[Dict],
        best_model: Dict,
        prediction_log: Optional[List[Dict]] = None,
        trade_log: Optional[List[Dict]] = None,
    ) -> str:
        """
        Generate decision-focused report with actionable insights.
        Human-readable, not just metrics.
        """
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        filepath = self.reports_dir / f"decision_report_{timestamp}.txt"

        lines = [
            "=" * 70,
            "DECISION-FOCUSED BACKTEST REPORT",
            "=" * 70,
            f"Generated: {datetime.now().isoformat()}",
            "",
        ]

        # A. Where Edge Exists
        lines.extend(self._section_edge_existence(all_results))

        # B. Symbol Performance
        lines.extend(self._section_symbol_performance(all_results))

        # C. Trade Quality
        lines.extend(self._section_trade_quality(trade_log or []))

        # D. System Health
        lines.extend(self._section_system_health(all_results, prediction_log or []))

        lines.extend(["", "=" * 70])

        report_text = "\n".join(lines)
        with open(filepath, "w") as f:
            f.write(report_text)

        logger.info(f"Decision report saved to {filepath}")
        return str(filepath)

    def _section_edge_existence(self, all_results: List[Dict]) -> List[str]:
        """A. Where Edge Exists - Best confidence range, highest expectancy."""
        lines = ["", "--- A. WHERE EDGE EXISTS ---", ""]

        # Find best confidence threshold across results
        threshold_stats = {}
        for r in all_results:
            thresh = r.get("optimal_confidence_threshold", {})
            if thresh and thresh.get("trade_count", 0) > 0:
                thresh_val = thresh["optimal_threshold"]
                bucket = f"{int(thresh_val * 100)//5 * 5:.0f}-{int(thresh_val * 100)//5 * 5 + 5:.0f}%"
                if bucket not in threshold_stats:
                    threshold_stats[bucket] = {"expectancy": [], "trades": 0}
                threshold_stats[bucket]["expectancy"].append(thresh["expected_return"])
                threshold_stats[bucket]["trades"] += thresh["trade_count"]

        if threshold_stats:
            best_bucket = max(
                threshold_stats.keys(),
                key=lambda b: sum(threshold_stats[b]["expectancy"]) / len(threshold_stats[b]["expectancy"]) if threshold_stats[b]["expectancy"] else 0
            )
            avg_exp = sum(threshold_stats[best_bucket]["expectancy"]) / len(threshold_stats[best_bucket]["expectancy"])
            total_trades = threshold_stats[best_bucket]["trades"]
            lines.append(f"Best Confidence Range: {best_bucket}")
            lines.append(f"  - Avg Expectancy: {avg_exp:.2f}")
            lines.append(f"  - Total Trades: {total_trades}")
            lines.append(f"  → ACTION: Focus on trades with confidence in this range")
        else:
            lines.append("No valid confidence thresholds found.")
            lines.append("  → ACTION: Lower min_trades threshold or check prediction quality")

        # Highest expectancy window
        valid_results = [r for r in all_results if r.get("trade_expectancy", {}).get("expectancy", 0) > 0]
        if valid_results:
            best_exp = max(valid_results, key=lambda r: r.get("trade_expectancy", {}).get("expectancy", 0))
            lines.append("")
            lines.append(f"Highest Expectancy Window: {best_exp.get('symbol', 'N/A')} W{best_exp.get('window_index', 'N/A')}")
            lines.append(f"  - Expectancy: {best_exp.get('trade_expectancy', {}).get('expectancy', 0):.2f}")
            lines.append(f"  - Sharpe: {best_exp.get('sharpe_ratio', 0):.2f}")
            lines.append(f"  → ACTION: Analyze this window's regime/market conditions")

        return lines

    def _section_symbol_performance(self, all_results: List[Dict]) -> List[str]:
        """B. Symbol Performance - Per-symbol stats, top/worst."""
        lines = ["", "--- B. SYMBOL PERFORMANCE ---", ""]

        symbol_stats = {}
        for r in all_results:
            sym = r.get("symbol", "UNKNOWN")
            if sym == "PORTFOLIO":
                continue
            if sym not in symbol_stats:
                symbol_stats[sym] = {"trades": 0, "wins": 0, "losses": 0, "expectancy": []}
            symbol_stats[sym]["trades"] += r.get("total_trades", 0)
            # Approximate wins/losses from win_rate
            win_rate = r.get("trade_expectancy", {}).get("win_rate", 0)
            trades = r.get("total_trades", 0)
            symbol_stats[sym]["wins"] += int(trades * win_rate)
            symbol_stats[sym]["losses"] += int(trades * (1 - win_rate))
            exp = r.get("trade_expectancy", {}).get("expectancy", 0)
            if exp != 0:
                symbol_stats[sym]["expectancy"].append(exp)

        if not symbol_stats:
            lines.append("No symbol data available.")
            return lines

        # Sort by total trades
        sorted_syms = sorted(symbol_stats.items(), key=lambda x: x[1]["trades"], reverse=True)

        lines.append(f"{'Symbol':<15} {'Trades':>6} {'Win Rate':>10} {'Avg Exp':>10}")
        lines.append("-" * 50)
        for sym, stats in sorted_syms:
            win_rate = stats["wins"] / stats["trades"] if stats["trades"] > 0 else 0
            avg_exp = sum(stats["expectancy"]) / len(stats["expectancy"]) if stats["expectancy"] else 0
            lines.append(f"{sym:<15} {stats['trades']:>6} {win_rate:>9.1%} {avg_exp:>10.2f}")

        # Top 3 and Worst 3 by expectancy
        sym_by_exp = [(s, sum(stats["expectancy"]) / len(stats["expectancy"]) if stats["expectancy"] else 0)
                       for s, stats in symbol_stats.items() if stats["expectancy"]]
        sym_by_exp.sort(key=lambda x: x[1], reverse=True)

        lines.append("")
        lines.append("Top 3 Symbols (by Expectancy):")
        for sym, exp in sym_by_exp[:3]:
            lines.append(f"  {sym}: {exp:.2f}")

        lines.append("")
        lines.append("Worst 3 Symbols (by Expectancy):")
        for sym, exp in sym_by_exp[-3:]:
            lines.append(f"  {sym}: {exp:.2f}")

        lines.append("")
        lines.append("→ ACTION: Focus capital on top symbols, avoid or reduce size on worst")

        return lines

    def _section_trade_quality(self, trade_log: List[Dict]) -> List[str]:
        """C. Trade Quality - Avg win, avg loss, expectancy."""
        lines = ["", "--- C. TRADE QUALITY ---", ""]

        if not trade_log:
            lines.append("No trades executed.")
            lines.append("  → ACTION: Check entry conditions, lower confidence threshold, or verify model is predicting BUY")
            return lines

        wins = [t for t in trade_log if t.get("pnl", 0) > 0]
        losses = [t for t in trade_log if t.get("pnl", 0) <= 0]

        avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(abs(t["pnl"]) for t in losses) / len(losses) if losses else 0
        win_rate = len(wins) / len(trade_log) if trade_log else 0
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

        lines.append(f"Total Trades: {len(trade_log)}")
        lines.append(f"Win Rate: {win_rate:.1%}")
        lines.append(f"Avg Win: {avg_win:.2f}")
        lines.append(f"Avg Loss: {avg_loss:.2f}")
        lines.append(f"Expectancy: {expectancy:.2f}")

        if expectancy > 0:
            lines.append("  ✓ Positive expectancy - strategy has edge")
            lines.append("  → ACTION: Increase position size or frequency")
        else:
            lines.append("  ✗ Negative expectancy - strategy is losing money")
            lines.append("  → ACTION: Stop trading, review model, or adjust parameters")

        # Check win/loss ratio
        if avg_win > 0 and avg_loss > 0:
            ratio = avg_win / avg_loss
            lines.append(f"Win/Loss Ratio: {ratio:.2f}")
            if ratio < 1.5:
                lines.append("  → WARNING: Wins are too small compared to losses")
                lines.append("  → ACTION: Tighten stop loss or let winners run longer")

        return lines

    def _section_system_health(self, all_results: List[Dict], prediction_log: List[Dict]) -> List[str]:
        """D. System Health - Trade frequency, high-confidence %, drawdown."""
        lines = ["", "--- D. SYSTEM HEALTH ---", ""]

        total_windows = len(all_results)
        total_trades = sum(r.get("total_trades", 0) for r in all_results)
        avg_trades_per_window = total_trades / total_windows if total_windows > 0 else 0

        lines.append(f"Total Windows: {total_windows}")
        lines.append(f"Total Trades: {total_trades}")
        lines.append(f"Avg Trades/Window: {avg_trades_per_window:.1f}")

        if avg_trades_per_window < 2:
            lines.append("  → WARNING: Low trade frequency - edge may be sparse")
            lines.append("  → ACTION: Lower confidence threshold or review model predictions")
        elif avg_trades_per_window > 10:
            lines.append("  ✓ Good trade frequency - edge is being captured")
        else:
            lines.append("  → Moderate trade frequency")

        # High-confidence trades
        if prediction_log:
            high_conf = [p for p in prediction_log if p.get("confidence", 0) >= 0.65]
            pct_high = len(high_conf) / len(prediction_log) * 100 if prediction_log else 0
            lines.append("")
            lines.append(f"High-Confidence Predictions: {len(high_conf)} ({pct_high:.1f}%)")
            if pct_high < 20:
                lines.append("  → WARNING: Few high-confidence predictions")
                lines.append("  → ACTION: Model may be uncertain - check feature quality")

        # Drawdown classification
        max_dds = [r.get("max_drawdown", 0) for r in all_results if r.get("max_drawdown", 1) > 0]
        avg_dd = sum(max_dds) / len(max_dds) if max_dds else 0

        lines.append("")
        lines.append(f"Avg Max Drawdown: {avg_dd:.2%}")

        if avg_dd > 0.25:
            dd_class = "HIGH RISK"
            action = "Reduce position size, tighten stop losses"
        elif avg_dd > 0.15:
            dd_class = "MODERATE RISK"
            action = "Monitor closely, consider reducing exposure"
        else:
            dd_class = "LOW RISK"
            action = "Drawdown is within acceptable limits"

        lines.append(f"Classification: {dd_class}")
        lines.append(f"  → ACTION: {action}")

        return lines
