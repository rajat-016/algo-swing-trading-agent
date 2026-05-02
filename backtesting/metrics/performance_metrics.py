import numpy as np
import pandas as pd
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    @staticmethod
    def calculate_all(
        trade_log: List[Dict],
        equity_curve: List[float],
        dates: List[str],
        predictions: np.ndarray = None,
        actuals: np.ndarray = None,
    ) -> Dict:
        results = {}

        results.update(PerformanceMetrics.trading_metrics(trade_log, equity_curve, dates))

        if predictions is not None and actuals is not None:
            results.update(PerformanceMetrics.ml_metrics(predictions, actuals))

        return results

    @staticmethod
    def trading_metrics(
        trade_log: List[Dict],
        equity_curve: List[float],
        dates: List[str],
    ) -> Dict:
        if not trade_log:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "avg_pnl": 0,
                "cagr": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "profit_factor": 0,
            }

        pnls = [t["pnl"] for t in trade_log]
        pnl_pcts = [t["pnl_pct"] for t in trade_log]

        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        total_trades = len(trade_log)
        win_count = len(wins)
        win_rate = win_count / total_trades if total_trades > 0 else 0
        avg_pnl = np.mean(pnls) if pnls else 0

        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        returns = pd.Series(equity_curve).pct_change().dropna()
        cagr = PerformanceMetrics.calculate_cagr(equity_curve, dates)

        sharpe = PerformanceMetrics.calculate_sharpe(returns)

        max_dd = PerformanceMetrics.calculate_max_drawdown(equity_curve)

        return {
            "total_trades": total_trades,
            "win_count": win_count,
            "loss_count": len(losses),
            "win_rate": win_rate,
            "avg_pnl": avg_pnl,
            "avg_pnl_pct": np.mean(pnl_pcts) if pnl_pcts else 0,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "profit_factor": profit_factor,
            "cagr": cagr,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
        }

    @staticmethod
    def ml_metrics(predictions: np.ndarray, actuals: np.ndarray) -> Dict:
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

        accuracy = accuracy_score(actuals, predictions)
        precision = precision_score(actuals, predictions, average="weighted", zero_division=0)
        recall = recall_score(actuals, predictions, average="weighted", zero_division=0)
        f1 = f1_score(actuals, predictions, average="weighted", zero_division=0)

        # NEW: Precision(BUY=2)
        precision_buy = precision_score(actuals, predictions, labels=[2], average="macro", zero_division=0)

        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "precision_buy": precision_buy,  # NEW
        }

    @staticmethod
    def confidence_bucket_analysis(prediction_log: List[Dict]) -> Dict:
        """Analyze performance by confidence buckets."""
        if not prediction_log:
            return {}

        buckets = {
            "low": {"count": 0, "correct": 0},      # < 0.50
            "medium": {"count": 0, "correct": 0},    # 0.50-0.65
            "high": {"count": 0, "correct": 0},      # >= 0.65
        }

        for entry in prediction_log:
            conf = entry.get("confidence", 0.0)
            # Note: prediction_log doesn't store actual outcome, just prediction
            # This is a simplified version - full implementation needs actual labels
            if conf < 0.50:
                buckets["low"]["count"] += 1
            elif conf < 0.65:
                buckets["medium"]["count"] += 1
            else:
                buckets["high"]["count"] += 1

        return buckets

    @staticmethod
    def trade_expectancy(trade_log: List[Dict]) -> Dict:
        """Calculate trade expectancy: E = (WinRate * AvgWin) - (LossRate * AvgLoss)."""
        if not trade_log:
            return {"expectancy": 0, "avg_win": 0, "avg_loss": 0, "win_rate": 0}

        wins = [t["pnl"] for t in trade_log if t["pnl"] > 0]
        losses = [t["pnl"] for t in trade_log if t["pnl"] <= 0]

        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 0
        win_rate = len(wins) / len(trade_log) if trade_log else 0

        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

        return {
            "expectancy": expectancy,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "win_rate": win_rate,
            "total_trades": len(trade_log),
        }

    @staticmethod
    def find_optimal_confidence_threshold(
        trade_log: List[Dict],
        min_trades: int = 5,
        threshold_step: float = 0.05,
        min_confidence: float = 0.50,
        max_confidence: float = 1.0,
    ) -> Dict:
        """
        Find optimal confidence threshold by iterating through buckets.
        Returns the LOWEST threshold where expectancy >0 and trades >= min_trades.
        """
        if not trade_log:
            return {"optimal_threshold": min_confidence, "expected_return": 0, "trade_count": 0}

        best_threshold = None
        best_expectancy = float("-inf")
        best_trade_count = 0

        thresholds = np.arange(min_confidence, max_confidence + threshold_step, threshold_step)

        for threshold in thresholds:
            filtered_trades = [
                t for t in trade_log
                if t.get("entry_confidence", 0) >= threshold
            ]

            if len(filtered_trades) < min_trades:
                continue

            exp = PerformanceMetrics.trade_expectancy(filtered_trades)
            expectancy = exp["expectancy"]

            if expectancy > 0 and (best_threshold is None or threshold < best_threshold):
                best_threshold = threshold
                best_expectancy = expectancy
                best_trade_count = len(filtered_trades)

        if best_threshold is None:
            # Return actual trade count for logging, not 0
            return {
                "optimal_threshold": min_confidence,
                "expected_return": 0,
                "trade_count": len(trade_log),
                "all_negative_expectancy": True,
            }

        return {
            "optimal_threshold": float(best_threshold),
            "expected_return": float(best_expectancy),
            "trade_count": int(best_trade_count),
            "all_negative_expectancy": False,
        }

        return {
            "optimal_threshold": float(best_threshold),
            "expected_return": float(best_expectancy),
            "trade_count": int(best_trade_count),
            "all_negative_expectancy": False,
        }

    @staticmethod
    def calculate_cagr(equity_curve: List[float], dates: List[str]) -> float:
        if len(equity_curve) < 2:
            return 0

        start_value = equity_curve[0]
        end_value = equity_curve[-1]

        try:
            start_date = pd.to_datetime(dates[0])
            end_date = pd.to_datetime(dates[-1])
            years = (end_date - start_date).days / 365.25
            if years <= 0:
                return 0
            cagr = (end_value / start_value) ** (1 / years) - 1
            return cagr
        except Exception:
            return 0

    @staticmethod
    def calculate_sharpe(returns: pd.Series, risk_free_rate: float = 0.06) -> float:
        if returns.empty or returns.std() == 0:
            return 0

        excess_returns = returns - (risk_free_rate / 252)
        sharpe = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
        return sharpe

    @staticmethod
    def calculate_max_drawdown(equity_curve: List[float]) -> float:
        if not equity_curve:
            return 0

        equity = pd.Series(equity_curve)
        running_max = equity.cummax()
        drawdown = (equity - running_max) / running_max
        max_dd = abs(drawdown.min())
        return max_dd
