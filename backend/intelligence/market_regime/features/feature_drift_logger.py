from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from loguru import logger
import json
import numpy as np


FEATURE_DRIFT_TABLE = """
CREATE TABLE IF NOT EXISTS feature_drift_log (
    id INTEGER PRIMARY KEY,
    group_name VARCHAR NOT NULL,
    feature_name VARCHAR NOT NULL,
    psi DOUBLE,
    status VARCHAR,
    current_distribution TEXT,
    baseline_distribution TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

FEATURE_DRIFT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_drift_log_group_created
ON feature_drift_log(group_name, created_at DESC);
"""


class FeatureDriftLogger:
    def __init__(self, db=None):
        self._db = db
        self._ready = False
        self._baselines: Dict[str, Dict[str, Any]] = {}

    def initialize(self, db=None):
        if db is not None:
            self._db = db
        if self._db is None:
            logger.warning("No database for FeatureDriftLogger")
            self._ready = False
            return

        try:
            self._db.execute(FEATURE_DRIFT_TABLE)
            try:
                self._db.execute(FEATURE_DRIFT_INDEX)
            except Exception:
                pass
            self._ready = True
            logger.info("FeatureDriftLogger initialized")
        except Exception as e:
            logger.warning(f"Failed to init FeatureDriftLogger: {e}")
            self._ready = False

    def set_baseline(self, group_name: str, baseline: Dict[str, Any]):
        self._baselines[group_name] = baseline

    def get_baseline(self, group_name: str) -> Optional[Dict[str, Any]]:
        return self._baselines.get(group_name)

    def compute_psi(self, expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
        if len(expected) == 0 or len(actual) == 0:
            return 0.0

        expected = np.asarray(expected, dtype=np.float64)
        actual = np.asarray(actual, dtype=np.float64)

        expected = expected[~np.isnan(expected)]
        actual = actual[~np.isnan(actual)]

        if len(expected) < 2:
            return 0.0

        if len(actual) == 1:
            actual = np.repeat(actual, min(10, len(expected)))

        combined = np.concatenate([expected, actual])
        if np.std(combined) == 0:
            return 0.0

        percentiles = np.linspace(0, 100, buckets + 1)[1:-1]
        edges = np.percentile(expected, percentiles)
        edges = np.clip(edges, np.min(combined), np.max(combined))

        if len(np.unique(edges)) < 2:
            return 0.0

        expected_counts, _ = np.histogram(expected, bins=np.concatenate([[-np.inf], edges, [np.inf]]))
        actual_counts, _ = np.histogram(actual, bins=np.concatenate([[-np.inf], edges, [np.inf]]))

        expected_pct = expected_counts / len(expected)
        actual_pct = actual_counts / len(actual)

        psi = 0.0
        for e, a in zip(expected_pct, actual_pct):
            if e == 0:
                e = 0.0001
            if a == 0:
                a = 0.0001
            psi += (a - e) * np.log(a / e)

        return round(float(psi), 6)

    def check_group_drift(
        self, group_name: str, current_features: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        baseline = self._baselines.get(group_name)
        if baseline is None:
            return results

        for fname, value in current_features.items():
            if fname not in baseline:
                continue

            baseline_vals = np.array(baseline[fname], dtype=np.float64)
            current_val = np.array([value], dtype=np.float64)

            psi = self.compute_psi(baseline_vals, current_val)

            if psi < 0.1:
                status = "NORMAL"
            elif psi < 0.25:
                status = "WARNING"
            else:
                status = "DRIFT"

            if psi > 0:
                results.append({
                    "group_name": group_name,
                    "feature_name": fname,
                    "psi": psi,
                    "status": status,
                })

                if status == "DRIFT":
                    logger.warning(f"Feature drift [{group_name}] {fname}: PSI={psi:.4f}")

        return results

    def log_drift_results(self, results: List[Dict[str, Any]]):
        if not self._ready or self._db is None:
            return

        for r in results:
            try:
                self._db.execute(
                    """
                    INSERT INTO feature_drift_log
                    (group_name, feature_name, psi, status, current_distribution, baseline_distribution, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        r["group_name"],
                        r["feature_name"],
                        r["psi"],
                        r["status"],
                        json.dumps({"value": 0}),
                        json.dumps({"value": 0}),
                        datetime.now(timezone.utc).isoformat(),
                    ],
                )
            except Exception as e:
                logger.debug(f"Failed to log drift: {e}")

    def get_recent_drift(self, group_name: Optional[str] = None, limit: int = 100) -> List[Dict]:
        if not self._ready or self._db is None:
            return []

        try:
            if group_name:
                rows = self._db.fetch_all(
                    """
                    SELECT * FROM feature_drift_log
                    WHERE group_name = ?
                    ORDER BY created_at DESC LIMIT ?
                    """,
                    [group_name, limit],
                )
            else:
                rows = self._db.fetch_all(
                    "SELECT * FROM feature_drift_log ORDER BY created_at DESC LIMIT ?",
                    [limit],
                )
            return [dict(zip([col[0] for col in self._db.description or []], row)) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to query drift log: {e}")
            return []
