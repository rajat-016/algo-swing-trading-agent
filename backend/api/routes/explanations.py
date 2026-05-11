import json
from typing import Optional, List
from datetime import datetime

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import desc

from core.database import get_db
from core.logging import logger
from core.config import get_settings
from models.prediction_log import PredictionLog
from models.stock import Stock

router = APIRouter(prefix="/explain", tags=["explainability"])


def _get_explainer():
    try:
        from intelligence.explainability.prediction_explainer import PredictionExplainer
        from core.model.registry import ModelRegistry
        registry = ModelRegistry()
        model_data = registry.load()
        model = model_data.get("model")
        feature_names = model_data.get("feature_names", [])
        background = model_data.get("background_samples")
        explainer = PredictionExplainer(
            model=model,
            feature_names=feature_names,
            background_samples=background,
        )
        return explainer
    except Exception as e:
        logger.warning(f"Could not load explainer: {e}")
        return None


def _get_shap_service():
    try:
        from intelligence.explainability.shap_service import SHAPService
        from core.model.registry import ModelRegistry
        registry = ModelRegistry()
        model_data = registry.load()
        model = model_data.get("model")
        feature_names = model_data.get("feature_names", [])
        background = model_data.get("background_samples")
        service = SHAPService(
            model=model,
            feature_names=feature_names,
            background_samples=background,
        )
        return service
    except Exception as e:
        logger.warning(f"Could not load SHAPService: {e}")
        return None


class _NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


@router.get("/prediction/{prediction_id}")
async def explain_prediction(
    prediction_id: int,
    db: Session = Depends(get_db),
):
    pred = db.query(PredictionLog).filter(PredictionLog.id == prediction_id).first()
    if not pred:
        raise HTTPException(404, f"Prediction {prediction_id} not found")

    if pred.shap_values:
        try:
            return {
                "prediction_id": prediction_id,
                "symbol": pred.symbol,
                "decision": pred.decision,
                "confidence": pred.confidence,
                "explanation": json.loads(pred.shap_values),
                "top_features": json.loads(pred.top_features) if pred.top_features else None,
                "cached": True,
            }
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "prediction_id": prediction_id,
        "symbol": pred.symbol,
        "decision": pred.decision,
        "confidence": pred.confidence,
        "message": "No cached explanation. Use POST /explain/prediction/{id} to generate one.",
    }


@router.post("/prediction/{prediction_id}")
async def generate_explanation(
    prediction_id: int,
    db: Session = Depends(get_db),
):
    pred = db.query(PredictionLog).filter(PredictionLog.id == prediction_id).first()
    if not pred:
        raise HTTPException(404, f"Prediction {prediction_id} not found")

    service = _get_shap_service()
    if service is None:
        raise HTTPException(503, "Explainability engine not available. Ensure model is trained.")

    try:
        success = service.generate_and_persist(db, prediction_id)
        if not success:
            raise HTTPException(500, "SHAP generation failed")

        db.refresh(pred)
        explanation = json.loads(pred.shap_values) if pred.shap_values else {}
        top_feat = json.loads(pred.top_features) if pred.top_features else {}

        return {
            "prediction_id": prediction_id,
            "symbol": pred.symbol,
            "decision": pred.decision,
            "confidence": pred.confidence,
            "explanation": explanation,
            "top_features": top_feat,
            "cached": False,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Explanation generation failed: {e}")
        raise HTTPException(500, f"Explanation failed: {str(e)}")


@router.post("/live")
async def explain_live_prediction(
    symbol: str = Query(..., description="Stock symbol"),
    p_buy: float = Query(..., ge=0, le=1),
    p_hold: float = Query(..., ge=0, le=1),
    p_sell: float = Query(..., ge=0, le=1),
):
    explainer = _get_explainer()
    if explainer is None:
        raise HTTPException(503, "Explainability engine not available")

    try:
        probs = np.array([p_sell, p_hold, p_buy])
        dummy_X = np.zeros((1, len(explainer.feature_names)))
        explanation = explainer.explain_prediction(dummy_X, probs)

        return {
            "symbol": symbol,
            "explanation": explanation,
        }
    except Exception as e:
        logger.error(f"Live explanation failed: {e}")
        raise HTTPException(500, f"Explanation failed: {str(e)}")


@router.get("/feature-importance")
async def global_feature_importance(
    top_n: int = Query(default=20, ge=1, le=81),
):
    explainer = _get_explainer()
    if explainer is None:
        raise HTTPException(503, "Explainability engine not available")

    try:
        shap_explainer = explainer.shap_explainer
        dummy_X = np.zeros((1, len(explainer.feature_names)))
        shap_result = shap_explainer.compute_shap_values(dummy_X)

        importance = shap_explainer.feature_importance_from_shap(
            shap_result, class_label="BUY"
        )[:top_n]

        return {
            "feature_importance": importance,
            "total_features": len(importance),
            "model_explainability": "shap.TreeExplainer",
        }
    except Exception as e:
        logger.error(f"Feature importance failed: {e}")
        raise HTTPException(500, f"Feature importance failed: {str(e)}")


@router.get("/recent")
async def recent_explanations(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    predictions = (
        db.query(PredictionLog)
        .filter(PredictionLog.shap_values.isnot(None))
        .order_by(desc(PredictionLog.timestamp))
        .limit(limit)
        .all()
    )

    results = []
    for p in predictions:
        try:
            explanation = json.loads(p.shap_values) if p.shap_values else {}
            top_feat = json.loads(p.top_features) if p.top_features else {}
        except (json.JSONDecodeError, TypeError):
            explanation = {}
            top_feat = {}

        results.append({
            "id": p.id,
            "symbol": p.symbol,
            "decision": p.decision,
            "confidence": p.confidence,
            "timestamp": p.timestamp.isoformat() if p.timestamp else None,
            "latency": p.explanation_latency,
            "top_positive": [f["feature"] for f in top_feat.get("positive", [])[:3]],
            "top_negative": [f["feature"] for f in top_feat.get("negative", [])[:3]],
        })

    return {"explanations": results, "count": len(results)}


@router.post("/batch")
async def batch_generate_explanations(
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Generate SHAP explanations for all predictions missing them."""
    service = _get_shap_service()
    if service is None:
        raise HTTPException(503, "SHAPService not available. Ensure model is trained.")

    try:
        result = service.generate_batch(db, limit=limit)
        return result
    except Exception as e:
        logger.error(f"Batch SHAP generation failed: {e}")
        raise HTTPException(500, f"Batch SHAP generation failed: {str(e)}")


@router.get("/feature-ranking")
async def feature_ranking(
    top_n: int = Query(default=20, ge=1, le=81),
    class_label: str = Query(default="BUY", regex="^(BUY|SELL|HOLD)$"),
    db: Session = Depends(get_db),
):
    """Aggregate SHAP feature importance across all predictions."""
    service = _get_shap_service()
    if service is None:
        raise HTTPException(503, "SHAPService not available. Ensure model is trained.")

    try:
        ranking = service.get_feature_ranking(db, top_n=top_n, class_label=class_label)
        return ranking
    except Exception as e:
        logger.error(f"Feature ranking failed: {e}")
        raise HTTPException(500, f"Feature ranking failed: {str(e)}")


@router.get("/coverage")
async def explanation_coverage(
    db: Session = Depends(get_db),
):
    """Get SHAP explanation coverage stats."""
    total = db.query(PredictionLog).count()
    with_shap = db.query(PredictionLog).filter(PredictionLog.shap_values.isnot(None)).count()
    without_shap = total - with_shap

    coverage_pct = round(with_shap / total * 100, 2) if total > 0 else 0

    return {
        "total_predictions": total,
        "with_explanations": with_shap,
        "without_explanations": without_shap,
        "coverage_pct": coverage_pct,
        "status": "complete" if coverage_pct >= 100 else "incomplete",
    }


@router.get("/cache")
async def cache_stats():
    """Get SHAP explanation cache statistics."""
    service = _get_shap_service()
    if service is None:
        return {"status": "unavailable"}
    return service.cache_stats()


@router.post("/cache/clear")
async def clear_cache():
    """Clear the in-memory SHAP explanation cache."""
    service = _get_shap_service()
    if service is None:
        return {"status": "unavailable"}
    service.clear_cache()
    return {"status": "cleared"}


@router.get("/health")
async def explainability_health():
    explainer = _get_explainer()
    if explainer is None:
        return {
            "status": "unavailable",
            "explainability_enabled": False,
            "message": "SHAP not available or model not loaded",
        }

    return {
        "status": "available",
        "explainability_enabled": True,
        "explainer_type": explainer.shap_explainer.explainer_type,
        "num_features": len(explainer.feature_names),
    }
