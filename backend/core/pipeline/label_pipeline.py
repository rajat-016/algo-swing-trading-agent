import pandas as pd
import numpy as np
from typing import Optional
from core.logging import logger


class LabelPipeline:
    def __init__(
        self,
        lookahead: int = 5,
        threshold: float = 0.10,
        stop_loss: float = 0.03,
    ):
        self.lookahead = lookahead
        self.threshold = threshold
        self.stop_loss = stop_loss

    def transform(self, df: pd.DataFrame, atr_col: Optional[str] = None) -> pd.Series:
        if "close" not in df.columns:
            raise ValueError("DataFrame must contain 'close' column")

        df = df.copy()
        df["future_return"] = df["close"].shift(-self.lookahead) / df["close"] - 1

        if atr_col and atr_col in df.columns:
            atr_pct = df[atr_col] / df["close"]
            adaptive_target = (atr_pct * 2.0).clip(lower=self.threshold, upper=0.15)
            adaptive_stop = (atr_pct * 1.0).clip(lower=self.stop_loss, upper=0.06)
        else:
            adaptive_target = self.threshold
            adaptive_stop = self.stop_loss

        labels = pd.Series(1, index=df.index, name="label")
        labels[df["future_return"] < -adaptive_stop] = 0
        labels[df["future_return"] > adaptive_target] = 2

        label_counts = {int(v): int((labels == v).sum()) for v in [0, 1, 2]}
        logger.debug(f"LabelPipeline: {label_counts} (SELL/HOLD/BUY)")

        return labels
