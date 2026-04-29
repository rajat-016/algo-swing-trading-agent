import pandas as pd
import logging

logger = logging.getLogger(__name__)


class LabelGenerator:
    def __init__(self, lookahead: int = 5, threshold: float = 0.01, stop_loss: float = 0.03):
        self.lookahead = lookahead
        self.threshold = threshold
        self.stop_loss = stop_loss

    def create_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns:
            raise ValueError("DataFrame must contain 'close' column")

        df = df.copy()

        future_returns = df["close"].shift(-self.lookahead) / df["close"] - 1

        labels = pd.Series(0, index=df.index)
        labels[future_returns > self.threshold] = 1
        labels[future_returns < -self.stop_loss] = -1

        df["signal"] = labels
        df["future_return"] = future_returns

        logger.info(
            f"Labels created: "
            f"BUY={int((labels == 1).sum())}, "
            f"SELL={int((labels == -1).sum())}, "
            f"HOLD={int((labels == 0).sum())}"
        )

        return df
