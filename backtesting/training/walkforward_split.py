import pandas as pd
from typing import List, Tuple
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class WalkForwardSplitter:
    def __init__(
        self,
        train_window_years: int = 3,
        test_window_months: int = 6,
        step_months: int = 6,
    ):
        self.train_window_years = train_window_years
        self.test_window_months = test_window_months
        self.step_months = step_months

    def generate_splits(
        self,
        df: pd.DataFrame,
        datetime_col: str = "datetime",
    ) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        if datetime_col not in df.columns:
            raise ValueError(f"DataFrame must contain '{datetime_col}' column")

        df = df.copy()
        df[datetime_col] = pd.to_datetime(df[datetime_col])
        df = df.sort_values(datetime_col).reset_index(drop=True)

        start_date = df[datetime_col].min()
        end_date = df[datetime_col].max()

        train_end = start_date + pd.DateOffset(years=self.train_window_years)
        splits = []
        window_num = 0

        while train_end < end_date:
            test_end = train_end + pd.DateOffset(months=self.test_window_months)
            if test_end > end_date:
                test_end = end_date

            train_mask = df[datetime_col] < train_end
            test_mask = (df[datetime_col] >= train_end) & (df[datetime_col] < test_end)

            train_df = df[train_mask].copy()
            test_df = df[test_mask].copy()

            if len(train_df) < 100 or len(test_df) < 10:
                logger.warning(
                    f"Window {window_num}: Insufficient data "
                    f"(train={len(train_df)}, test={len(test_df)}) - skipping"
                )
                train_end += pd.DateOffset(months=self.step_months)
                continue

            splits.append((train_df, test_df))
            logger.info(
                f"Window {window_num}: "
                f"Train [{train_df[datetime_col].min().date()} -> {train_df[datetime_col].max().date()}] ({len(train_df)} rows), "
                f"Test [{test_df[datetime_col].min().date()} -> {test_df[datetime_col].max().date()}] ({len(test_df)} rows)"
            )

            window_num += 1
            train_end += pd.DateOffset(months=self.step_months)

        logger.info(f"Generated {len(splits)} walk-forward splits")
        return splits
