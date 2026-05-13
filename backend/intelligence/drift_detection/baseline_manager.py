from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
from loguru import logger


class BaselineManager:
    LATEST_LABEL = "__latest__"

    def __init__(self, analytics_db=None):
        self._db = analytics_db
        self._in_memory: dict[str, dict[str, Any]] = {}

    def _key(self, feature_name: str, group_name: str, label: str) -> str:
        return f"{group_name}__{feature_name}__{label}"

    def store_baseline(
        self,
        feature_name: str,
        group_name: str,
        values: list[float],
        metadata: Optional[dict[str, Any]] = None,
        label: str = LATEST_LABEL,
    ):
        key = self._key(feature_name, group_name, label)
        arr = np.asarray(values, dtype=np.float64)
        entry = {
            "feature_name": feature_name,
            "group_name": group_name,
            "label": label,
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "variance": float(np.var(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "p5": float(np.percentile(arr, 5)),
            "p25": float(np.percentile(arr, 25)),
            "p50": float(np.percentile(arr, 50)),
            "p75": float(np.percentile(arr, 75)),
            "p95": float(np.percentile(arr, 95)),
            "count": len(values),
            "values_json": json.dumps([round(v, 6) for v in values]),
            "metadata": json.dumps(metadata or {}),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._in_memory[key] = entry

        if self._db is not None:
            self._persist_to_db(entry)

    def _persist_to_db(self, entry: dict):
        try:
            self._db.execute(
                """INSERT OR REPLACE INTO drift_baselines
                (feature_name, group_name, label, mean, std, variance, min, max,
                 p5, p25, p50, p75, p95, count, values_json, metadata, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [
                    entry["feature_name"], entry["group_name"], entry["label"],
                    entry["mean"], entry["std"], entry["variance"],
                    entry["min"], entry["max"],
                    entry["p5"], entry["p25"], entry["p50"],
                    entry["p75"], entry["p95"],
                    entry["count"], entry["values_json"], entry["metadata"],
                    entry["updated_at"],
                ],
            )
        except Exception as e:
            logger.warning(f"Failed to persist baseline to DB: {e}")

    def get_baseline(
        self,
        feature_name: str,
        group_name: str = "general",
        label: str = LATEST_LABEL,
    ) -> Optional[dict[str, Any]]:
        key = self._key(feature_name, group_name, label)
        entry = self._in_memory.get(key)
        if entry is not None:
            return dict(entry)

        if self._db is not None:
            try:
                row = self._db.fetch_one(
                    "SELECT * FROM drift_baselines WHERE feature_name=? AND group_name=? AND label=?",
                    [feature_name, group_name, label],
                )
                if row:
                    entry = dict(row)
                    self._in_memory[key] = entry
                    return dict(entry)
            except Exception:
                pass
        return None

    def get_baseline_values(self, feature_name: str, group_name: str = "general", label: str = LATEST_LABEL) -> Optional[np.ndarray]:
        entry = self.get_baseline(feature_name, group_name, label)
        if entry is None:
            return None
        try:
            values = json.loads(entry["values_json"])
            return np.asarray(values, dtype=np.float64)
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def list_baselines(self, group_name: Optional[str] = None) -> list[dict[str, Any]]:
        results = []
        for key, entry in self._in_memory.items():
            if group_name is None or entry["group_name"] == group_name:
                results.append({
                    "feature_name": entry["feature_name"],
                    "group_name": entry["group_name"],
                    "label": entry["label"],
                    "count": entry["count"],
                    "mean": entry["mean"],
                    "variance": entry["variance"],
                    "updated_at": entry["updated_at"],
                })

        if self._db is not None and not results:
            try:
                rows = self._db.fetch_all(
                    "SELECT feature_name, group_name, label, count, mean, variance, updated_at FROM drift_baselines"
                    + (" WHERE group_name=?" if group_name else ""),
                    [group_name] if group_name else [],
                )
                for row in rows:
                    results.append(dict(row))
            except Exception:
                pass

        return results

    def remove_baseline(self, feature_name: str, group_name: str = "general", label: str = LATEST_LABEL) -> bool:
        key = self._key(feature_name, group_name, label)
        removed = self._in_memory.pop(key, None) is not None
        if self._db is not None:
            try:
                self._db.execute(
                    "DELETE FROM drift_baselines WHERE feature_name=? AND group_name=? AND label=?",
                    [feature_name, group_name, label],
                )
                removed = True
            except Exception as e:
                logger.warning(f"Failed to remove baseline from DB: {e}")
        return removed

    def ensure_table(self):
        if self._db is None:
            return
        try:
            self._db.execute("""
                CREATE TABLE IF NOT EXISTS drift_baselines (
                    feature_name VARCHAR,
                    group_name VARCHAR DEFAULT 'general',
                    label VARCHAR DEFAULT '__latest__',
                    mean DOUBLE,
                    std DOUBLE,
                    variance DOUBLE,
                    min DOUBLE,
                    max DOUBLE,
                    p5 DOUBLE,
                    p25 DOUBLE,
                    p50 DOUBLE,
                    p75 DOUBLE,
                    p95 DOUBLE,
                    count INTEGER,
                    values_json TEXT,
                    metadata TEXT DEFAULT '{}',
                    updated_at VARCHAR,
                    PRIMARY KEY (feature_name, group_name, label)
                )
            """)
            logger.info("Ensured drift_baselines table exists")
        except Exception as e:
            logger.warning(f"Failed to create drift_baselines table: {e}")
