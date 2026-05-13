from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.evaluation.base import EvaluationResult, EvalMetric


class EvalMetricsStore:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            try:
                from core.config import get_settings
                settings = get_settings()
                bdir = getattr(settings, "_backend_dir", None)
                if bdir:
                    db_path = str(Path(str(bdir)) / "data" / "eval_metrics.duckdb")
                else:
                    db_path = ":memory:"
            except Exception:
                db_path = ":memory:"
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def _get_conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._init_schema()
        return self._conn

    def _init_schema(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS eval_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evaluator_name TEXT NOT NULL,
                passed INTEGER NOT NULL,
                duration_ms REAL NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS eval_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                value REAL NOT NULL,
                metric_type TEXT NOT NULL,
                threshold REAL,
                passed INTEGER,
                unit TEXT DEFAULT '',
                details TEXT,
                FOREIGN KEY (run_id) REFERENCES eval_runs(id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_eval_runs_timestamp
            ON eval_runs(timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_eval_metrics_name
            ON eval_metrics(name)
        """)
        conn.commit()

    def store_result(self, result: EvaluationResult) -> int:
        conn = self._get_conn()
        cursor = conn.execute(
            "INSERT INTO eval_runs (evaluator_name, passed, duration_ms, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
            [
                result.evaluator_name,
                1 if result.passed else 0,
                result.total_duration_ms,
                result.timestamp,
                json.dumps(result.metadata) if result.metadata else None,
            ],
        )
        run_id = cursor.lastrowid
        for metric in result.metrics:
            conn.execute(
                "INSERT INTO eval_metrics (run_id, name, value, metric_type, threshold, passed, unit, details) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    run_id,
                    metric.name,
                    metric.value,
                    metric.metric_type.value,
                    metric.threshold,
                    1 if metric.passed else 0 if metric.passed is False else None,
                    metric.unit,
                    json.dumps(metric.details) if metric.details else None,
                ],
            )
        conn.commit()
        return run_id

    def get_recent_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM eval_runs ORDER BY timestamp DESC LIMIT ?", [limit]
        ).fetchall()
        columns = [d[1] for d in conn.execute("PRAGMA table_info(eval_runs)").fetchall()]
        return [dict(zip(columns, row)) for row in rows]

    def get_metrics_for_run(self, run_id: int) -> list[dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM eval_metrics WHERE run_id = ?", [run_id]
        ).fetchall()
        columns = [d[1] for d in conn.execute("PRAGMA table_info(eval_metrics)").fetchall()]
        return [dict(zip(columns, row)) for row in rows]

    def get_metric_history(self, metric_name: str, limit: int = 100) -> list[dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT m.value, m.passed, r.timestamp, r.evaluator_name
               FROM eval_metrics m
               JOIN eval_runs r ON m.run_id = r.id
               WHERE m.name = ?
               ORDER BY r.timestamp DESC
               LIMIT ?""",
            [metric_name, limit],
        ).fetchall()
        return [
            {
                "value": row[0],
                "passed": bool(row[1]) if row[1] is not None else None,
                "timestamp": row[2],
                "evaluator": row[3],
            }
            for row in rows
        ]

    def get_latest_by_evaluator(self, evaluator_name: str) -> Optional[EvaluationResult]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM eval_runs WHERE evaluator_name = ? ORDER BY timestamp DESC LIMIT 1",
            [evaluator_name],
        ).fetchone()
        if row is None:
            return None
        run_id = row[0]
        metric_rows = conn.execute(
            "SELECT * FROM eval_metrics WHERE run_id = ?", [run_id]
        ).fetchall()
        metrics = []
        for mr in metric_rows:
            metrics.append(EvalMetric(
                name=mr[2],
                value=mr[3],
                metric_type=mr[4],
                threshold=mr[5],
                passed=bool(mr[6]) if mr[6] is not None else None,
                unit=mr[7] or "",
                details=json.loads(mr[8]) if mr[8] else None,
            ))
        return EvaluationResult(
            evaluator_name=row[1],
            metrics=metrics,
            passed=bool(row[2]),
            total_duration_ms=row[3],
            timestamp=row[4],
            metadata=json.loads(row[5]) if row[5] else None,
        )

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None


MetricsStore = EvalMetricsStore
