import pandas as pd
import logging

logger = logging.getLogger(__name__)


class LabelGenerator:
    """Creates 3-class labels: SELL=0, HOLD=1, BUY=2."""

    def __init__(
        self,
        lookahead: int = 5,
        threshold: float = 0.10,
        stop_loss: float = 0.03,
        atr_target_multiplier: float = 1.5,
        atr_stop_multiplier: float = 1.0,
    ):
        self.lookahead = lookahead
        self.threshold = threshold
        self.stop_loss = stop_loss
        self.atr_target_multiplier = atr_target_multiplier
        self.atr_stop_multiplier = atr_stop_multiplier

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    def create_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns:
            raise ValueError("DataFrame must contain 'close' column")

        df = df.copy()
        df["future_return"] = df["close"].shift(-self.lookahead) / df["close"] - 1

        atr_col = "atr_14" if "atr_14" in df.columns else None
        if atr_col is None:
            df["atr_14"] = self._calculate_atr(df)
            atr_col = "atr_14"

        atr_pct = df[atr_col] / df["close"]

        # target = atr_pct * multiplier (clip 2%-5%)
        # stop = atr_pct * multiplier (clip 1%-3%)
        adaptive_target = (atr_pct * self.atr_target_multiplier).clip(lower=0.02, upper=0.05)
        adaptive_stop = (atr_pct * self.atr_stop_multiplier).clip(lower=0.01, upper=0.03)

        labels = pd.Series(1, index=df.index, name="signal")
        labels[df["future_return"] < -adaptive_stop] = 0
        labels[df["future_return"] > adaptive_target] = 2

        df["signal"] = labels

        label_counts = {int(v): int((labels == v).sum()) for v in [0, 1, 2]}
        logger.info(f"Labels created (3-class SELL/HOLD/BUY): {label_counts}")

        return df
