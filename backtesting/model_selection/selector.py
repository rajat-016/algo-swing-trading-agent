from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ModelSelector:
    def __init__(
        self,
        min_sharpe: float = 1.2,
        max_drawdown: float = 0.20,
        min_accuracy: float = 0.55,
        primary_metric: str = "sharpe_ratio",
    ):
        self.min_sharpe = min_sharpe
        self.max_drawdown = max_drawdown
        self.min_accuracy = min_accuracy
        self.primary_metric = primary_metric

    def select_best_model(
        self,
        results: List[Dict],
    ) -> Optional[Dict]:
        if not results:
            logger.warning("No results to select from")
            return None

        filtered = [
            r for r in results
            if r.get("sharpe_ratio", 0) >= self.min_sharpe
            and r.get("max_drawdown", 1) <= self.max_drawdown
            and r.get("accuracy", 0) >= self.min_accuracy
        ]

        if not filtered:
            logger.warning(
                f"No models passed threshold gates "
                f"(Sharpe>={self.min_sharpe}, DD<={self.max_drawdown}, Acc>={self.min_accuracy})"
            )

            best = max(
                results,
                key=lambda r: r.get(self.primary_metric, 0)
            )
            logger.info(f"Selected best available model (did not meet all thresholds)")
            return best

        best = max(
            filtered,
            key=lambda r: r.get(self.primary_metric, 0)
        )

        logger.info(
            f"Selected best model: "
            f"Sharpe={best.get('sharpe_ratio', 0):.2f}, "
            f"DD={best.get('max_drawdown', 0):.2f}, "
            f"Acc={best.get('accuracy', 0):.2f}"
        )

        return best
