from __future__ import annotations

from typing import Any, Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field


class ShiftAnalysisRequest(BaseModel):
    feature_name: str
    baseline_values: list[float]
    current_values: list[float]
    group_name: str = "general"
    window_label: str = ""


class BatchShiftRequest(BaseModel):
    features: dict[str, dict[str, list[float]]]
    group_name: str = "general"


class VarianceAnalysisRequest(BaseModel):
    feature_name: str
    current_values: Optional[list[float]] = None
    group_name: str = "general"


class BatchVarianceRequest(BaseModel):
    feature_values: dict[str, list[float]]
    group_name: str = "general"


class ContributionRequest(BaseModel):
    current_importance: dict[str, float]


class FullPipelineRequest(BaseModel):
    feature_data: dict[str, list[float]]
    baseline_data: Optional[dict[str, list[float]]] = None
    importance_data: Optional[dict[str, float]] = None
    group_name: str = "general"


class InitializeBaselinesRequest(BaseModel):
    baseline_data: dict[str, dict[str, list[float]]]
    group_name: str = "general"


class AlertAcknowledgeRequest(BaseModel):
    alert_id: str
    acknowledge_all: bool = False
    feature_name: Optional[str] = None


class AlertRuleRequest(BaseModel):
    name: str
    drift_type: str = "distribution_shift"
    severity: str = "WARNING"
    metric: str = "psi"
    operator: str = ">="
    threshold: float = 0.25
    cooldown_minutes: int = 60
    enabled: bool = True
    description: str = ""


router = APIRouter(prefix="/drift", tags=["drift"])


def _get_service():
    try:
        from intelligence.drift_detection.service import DriftDetectionService
        return DriftDetectionService()
    except Exception as e:
        logger.warning(f"DriftDetectionService not available: {e}")
        return None


@router.get("/status")
async def get_status():
    service = _get_service()
    if service is None:
        raise HTTPException(503, "Drift detection service not available")
    return service.get_service_status()


@router.post("/baselines/init")
async def initialize_baselines(req: InitializeBaselinesRequest):
    service = _get_service()
    if service is None:
        raise HTTPException(503, "Drift detection service not available")
    service.initialize_baselines(req.baseline_data, req.group_name)
    return {"status": "ok", "features_initialized": len(req.baseline_data)}


@router.post("/baselines/store")
async def store_baseline(
    feature_name: str = Query(...),
    group_name: str = Query("general"),
    label: str = Query("__latest__"),
    values: list[float] = Query(...),
):
    service = _get_service()
    if service is None:
        raise HTTPException(503, "Drift detection service not available")
    service.baseline_manager.store_baseline(feature_name, group_name, values, label=label)
    return {"status": "ok", "feature_name": feature_name, "group_name": group_name}


@router.get("/baselines")
async def list_baselines(group_name: Optional[str] = Query(None)):
    service = _get_service()
    if service is None:
        raise HTTPException(503, "Drift detection service not available")
    return {"baselines": service.baseline_manager.list_baselines(group_name)}


@router.post("/analyze/shift")
async def analyze_shift(req: ShiftAnalysisRequest):
    service = _get_service()
    if service is None:
        raise HTTPException(503, "Drift detection service not available")
    result = service.analyze_feature_shift(
        req.feature_name,
        np.array(req.baseline_values, dtype=np.float64),
        np.array(req.current_values, dtype=np.float64),
        req.group_name,
    )
    return {"shift_result": result.model_dump()}


@router.post("/analyze/batch-shift")
async def analyze_batch_shift(req: BatchShiftRequest):
    service = _get_service()
    if service is None:
        raise HTTPException(503, "Drift detection service not available")
    feature_data = {}
    for fname, data in req.features.items():
        feature_data[fname] = {
            "baseline": np.array(data.get("baseline", []), dtype=np.float64),
            "current": np.array(data.get("current", []), dtype=np.float64),
        }
    results = service.analyze_batch_shift(feature_data, req.group_name)
    return {"shift_results": [r.model_dump() for r in results]}


@router.post("/analyze/variance")
async def analyze_variance(req: VarianceAnalysisRequest):
    service = _get_service()
    if service is None:
        raise HTTPException(503, "Drift detection service not available")
    values = np.array(req.current_values, dtype=np.float64) if req.current_values else None
    snapshot = service.track_feature_variance(req.feature_name, values, req.group_name)
    if snapshot is None:
        raise HTTPException(400, f"Insufficient data for feature '{req.feature_name}'")
    return {"variance_snapshot": snapshot.model_dump()}


@router.post("/analyze/batch-variance")
async def analyze_batch_variance(req: BatchVarianceRequest):
    service = _get_service()
    if service is None:
        raise HTTPException(503, "Drift detection service not available")
    feature_values = {fname: np.array(vals, dtype=np.float64) for fname, vals in req.feature_values.items()}
    report = service.track_batch_variance(feature_values, req.group_name)
    return {"variance_report": report.model_dump()}


@router.post("/analyze/contribution")
async def analyze_contribution(req: ContributionRequest):
    service = _get_service()
    if service is None:
        raise HTTPException(503, "Drift detection service not available")
    report = service.analyze_prediction_contribution(req.current_importance)
    return {"contribution_report": report.model_dump()}


@router.post("/pipeline")
async def run_pipeline(req: FullPipelineRequest):
    service = _get_service()
    if service is None:
        raise HTTPException(503, "Drift detection service not available")
    feature_data = {fname: np.array(vals, dtype=np.float64) for fname, vals in req.feature_data.items()}
    baseline_data = None
    if req.baseline_data:
        baseline_data = {fname: np.array(vals, dtype=np.float64) for fname, vals in req.baseline_data.items()}
    results = service.run_full_pipeline(feature_data, baseline_data, req.importance_data, req.group_name)
    return results


@router.get("/alerts")
async def get_alerts(
    severity: Optional[str] = Query(None),
    limit: int = Query(50),
    unacknowledged_only: bool = Query(False),
):
    service = _get_service()
    if service is None:
        raise HTTPException(503, "Drift detection service not available")
    from intelligence.drift_detection.alerting import DriftSeverity
    sev = DriftSeverity(severity.upper()) if severity else None
    alerts = service.alert_manager.get_alerts(sev, limit, unacknowledged_only)
    return {"alerts": [a.model_dump() for a in alerts]}


@router.post("/alerts/acknowledge")
async def acknowledge_alert(req: AlertAcknowledgeRequest):
    service = _get_service()
    if service is None:
        raise HTTPException(503, "Drift detection service not available")
    if req.acknowledge_all:
        count = service.alert_manager.acknowledge_all(req.feature_name)
        return {"status": "ok", "acknowledged_count": count}
    ok = service.alert_manager.acknowledge_alert(req.alert_id)
    if not ok:
        raise HTTPException(404, f"Alert '{req.alert_id}' not found")
    return {"status": "ok", "alert_id": req.alert_id}


@router.get("/alerts/summary")
async def alert_summary():
    service = _get_service()
    if service is None:
        raise HTTPException(503, "Drift detection service not available")
    return service.alert_manager.get_alert_summary()


@router.post("/rules")
async def add_rule(req: AlertRuleRequest):
    service = _get_service()
    if service is None:
        raise HTTPException(503, "Drift detection service not available")
    from intelligence.drift_detection.alerting import AlertRule, DriftSeverity, DriftType
    rule = AlertRule(
        name=req.name,
        drift_type=DriftType(req.drift_type),
        severity=DriftSeverity(req.severity.upper()),
        metric=req.metric,
        operator=req.operator,
        threshold=req.threshold,
        cooldown_minutes=req.cooldown_minutes,
        enabled=req.enabled,
        description=req.description,
    )
    service.alert_manager.add_rule(rule)
    return {"status": "ok", "rule_id": rule.rule_id}


@router.get("/rules")
async def list_rules(drift_type: Optional[str] = Query(None)):
    service = _get_service()
    if service is None:
        raise HTTPException(503, "Drift detection service not available")
    from intelligence.drift_detection.alerting import DriftType
    dt = DriftType(drift_type) if drift_type else None
    rules = service.alert_manager.get_rules(dt)
    return {"rules": [r.model_dump() for r in rules]}


@router.delete("/rules/{rule_id}")
async def remove_rule(rule_id: str):
    service = _get_service()
    if service is None:
        raise HTTPException(503, "Drift detection service not available")
    ok = service.alert_manager.remove_rule(rule_id)
    if not ok:
        raise HTTPException(404, f"Rule '{rule_id}' not found")
    return {"status": "ok", "rule_id": rule_id}
