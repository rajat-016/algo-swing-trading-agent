from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ModelSelector:
    def __init__(
        self,
        min_sharpe: float = 1.0,
        max_drawdown: float = 0.25,
        min_trades: int = 30,
        min_precision_buy: float = 0.55,
        min_expectancy: float = 0.0,
        primary_metric: str = "sharpe_ratio",
    ):
        self.min_sharpe = min_sharpe
        self.max_drawdown = max_drawdown
        self.min_trades = min_trades
        self.min_precision_buy = min_precision_buy
        self.min_expectancy = min_expectancy
        self.primary_metric = primary_metric

    def select_best_model(
        self,
        results: List[Dict],
    ) -> Optional[Dict]:
        if not results:
            logger.warning("No results to select from")
            return None

        filtered = []
        rejected = {
            "low_trades": [],
            "low_precision_buy": [],
            "negative_expectancy": [],
            "high_drawdown": [],
            "low_sharpe": [],
        }

        for r in results:
            sharpe = r.get("sharpe_ratio", 0)
            dd = r.get("max_drawdown", 1)
            trades = r.get("total_trades", 0)
            precision_buy = r.get("precision_buy", 0)
            expectancy_data = r.get("trade_expectancy", {})
            expectancy = expectancy_data.get("expectancy", 0) if isinstance(expectancy_data, dict) else 0

            rejected_for = []

            if trades < self.min_trades:
                rejected_for.append("low_trades")
                rejected["low_trades"].append({
                    "symbol": r.get("symbol"),
                    "window": r.get("window_index"),
                    "trades": trades,
                    "min_required": self.min_trades,
                })

            if precision_buy < self.min_precision_buy:
                rejected_for.append("low_precision_buy")
                rejected["low_precision_buy"].append({
                    "symbol": r.get("symbol"),
                    "window": r.get("window_index"),
                    "precision_buy": precision_buy,
                    "min_required": self.min_precision_buy,
                })

            if expectancy <= self.min_expectancy:
                rejected_for.append("negative_expectancy")
                rejected["negative_expectancy"].append({
                    "symbol": r.get("symbol"),
                    "window": r.get("window_index"),
                    "expectancy": expectancy,
                    "min_required": self.min_expectancy,
                })

            if dd > self.max_drawdown:
                rejected_for.append("high_drawdown")
                rejected["high_drawdown"].append({
                    "symbol": r.get("symbol"),
                    "window": r.get("window_index"),
                    "drawdown": dd,
                    "max_allowed": self.max_drawdown,
                })

            if sharpe < self.min_sharpe:
                rejected_for.append("low_sharpe")
                rejected["low_sharpe"].append({
                    "symbol": r.get("symbol"),
                    "window": r.get("window_index"),
                    "sharpe": sharpe,
                    "min_required": self.min_sharpe,
                })

            if not rejected_for:
                filtered.append(r)

        total_rejected = sum(len(v) for v in rejected.values())
        if total_rejected > 0:
            logger.warning(
                f"Model filtering: {len(results)} evaluated, {len(filtered)} passed, {total_rejected} rejected"
            )
            for reason, items in rejected.items():
                if items:
                    logger.warning(f"  - {reason}: {len(items)} models")

        if not filtered:
            logger.warning(
                f"No models passed ALL threshold gates. Falling back to best available by Sharpe."
            )
            logger.warning(
                f"Thresholds: Sharpe>={self.min_sharpe}, DD<={self.max_drawdown}, "
                f"Trades>={self.min_trades}, Precision(BUY)>={self.min_precision_buy}, "
                f"Expectancy>{self.min_expectancy}"
            )

            best = max(
                results,
                key=lambda r: r.get(self.primary_metric, 0)
            )
            logger.info(f"Selected best available model (did not meet all thresholds): {best.get('symbol')}_W{best.get('window_index')}")
            return best

        best = max(
            filtered,
            key=lambda r: (
                r.get("sharpe_ratio", 0),
                r.get("trade_expectancy", {}).get("expectancy", 0) if isinstance(r.get("trade_expectancy"), dict) else 0,
                -r.get("max_drawdown", 1),
            )
        )

        sharpe = best.get("sharpe_ratio", 0)
        dd = best.get("max_drawdown", 0)
        trades = best.get("total_trades", 0)
        precision_buy = best.get("precision_buy", 0)
        expectancy = best.get("trade_expectancy", {}).get("expectancy", 0) if isinstance(best.get("trade_expectancy"), dict) else 0

        logger.info(
            f"Selected best model: "
            f"Symbol={best.get('symbol')}, Window={best.get('window_index')}, "
            f"Sharpe={sharpe:.2f}, DD={dd:.2f}, "
            f"Trades={trades}, Precision(BUY)={precision_buy:.2f}, "
            f"Expectancy={expectancy:.2f}"
        )

        return best
