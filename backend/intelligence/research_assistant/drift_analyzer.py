from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field
from loguru import logger


class DriftedFeature(BaseModel):
    feature_name: str
    group_name: str
    psi: float
    status: str
    first_detected: Optional[str] = None
    direction: str = "unknown"


class DriftReport(BaseModel):
    total_features_checked: int = 0
    drifted_features: list[DriftedFeature] = Field(default_factory=list)
    warning_features: list[DriftedFeature] = Field(default_factory=list)
    normal_features: int = 0
    drift_ratio: float = 0.0
    most_unstable_group: Optional[str] = None
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    summary: str = ""


class DriftAnalyzer:
    def __init__(self, drift_logger=None, regime_feature_pipeline=None):
        self._drift_logger = drift_logger
        self._pipeline = regime_feature_pipeline
        self._ready = False

    def initialize(self, drift_logger=None, regime_feature_pipeline=None):
        if drift_logger is not None:
            self._drift_logger = drift_logger
        if regime_feature_pipeline is not None:
            self._pipeline = regime_feature_pipeline
        self._ready = self._drift_logger is not None or self._pipeline is not None
        logger.info(f"DriftAnalyzer initialized (ready={self._ready})")

    async def analyze_feature_drift(
        self,
        group_name: Optional[str] = None,
        lookback_days: int = 90,
        min_psi_threshold: float = 0.1,
    ) -> DriftReport:
        if not self._ready:
            return DriftReport(summary="DriftAnalyzer not initialized")

        rows = await self._get_drift_history(group_name, lookback_days)
        if not rows:
            return DriftReport(summary="No drift history available")

        feature_map: dict[str, dict[str, Any]] = {}
        for r in rows:
            key = f"{r.get('group_name', 'unknown')}__{r.get('feature_name', 'unknown')}"
            if key not in feature_map:
                feature_map[key] = {
                    "feature_name": r.get("feature_name", ""),
                    "group_name": r.get("group_name", ""),
                    "psi": r.get("psi", 0.0),
                    "status": r.get("status", "NORMAL"),
                    "first_detected": r.get("created_at", None),
                }
            else:
                existing = feature_map[key]
                if r.get("psi", 0) > existing["psi"]:
                    existing["psi"] = r.get("psi", 0)
                    existing["status"] = r.get("status", "NORMAL")

        drifted = []
        warning = []
        normal_count = 0

        for entry in feature_map.values():
            if entry["status"] == "DRIFT":
                drifted.append(DriftedFeature(**entry))
            elif entry["status"] == "WARNING":
                warning.append(DriftedFeature(**entry))
            else:
                normal_count += 1

        total = len(feature_map)
        drift_ratio = len(drifted) / total if total > 0 else 0.0

        group_drift_counts: dict[str, int] = {}
        for d in drifted:
            group_drift_counts[d.group_name] = group_drift_counts.get(d.group_name, 0) + 1
        most_unstable = max(group_drift_counts, key=group_drift_counts.get) if group_drift_counts else None

        summary_parts = []
        if drifted:
            summary_parts.append(f"{len(drifted)} features drifted (PSI>{min_psi_threshold})")
        if warning:
            summary_parts.append(f"{len(warning)} features in warning zone")
        summary_parts.append(f"{drift_ratio:.0%} drift ratio")
        if most_unstable:
            summary_parts.append(f"most unstable group: {most_unstable}")

        return DriftReport(
            total_features_checked=total,
            drifted_features=drifted,
            warning_features=warning,
            normal_features=normal_count,
            drift_ratio=round(drift_ratio, 4),
            most_unstable_group=most_unstable,
            summary=" | ".join(summary_parts),
        )

    async def _get_drift_history(self, group_name: Optional[str] = None, lookback_days: int = 90) -> list[dict]:
        if self._drift_logger is not None:
            try:
                rows = self._drift_logger.get_recent_drift(group_name=group_name, limit=500)
                return rows
            except Exception as e:
                logger.debug(f"DriftLogger query failed: {e}")

        if self._pipeline is not None and hasattr(self._pipeline, "drift_logger"):
            try:
                rows = self._pipeline.drift_logger.get_recent_drift(group_name=group_name, limit=500)
                return rows
            except Exception as e:
                logger.debug(f"Pipeline drift query failed: {e}")
        return []

    async def get_unstable_features(self, top_n: int = 10) -> list[dict]:
        report = await self.analyze_feature_drift()
        all_issues = sorted(
            [d.model_dump() for d in report.drifted_features],
            key=lambda x: x["psi"],
            reverse=True,
        )
        return all_issues[:top_n]

    @property
    def is_ready(self) -> bool:
        return self._ready
