import json
from typing import Optional
from datetime import datetime

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
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
        "message": "No cached explanation. Use POST /explain to generate one.",
    }


@router.post("/prediction/{prediction_id}")
async def generate_explanation(
    prediction_id: int,
    db: Session = Depends(get_db),
):
    pred = db.query(PredictionLog).filter(PredictionLog.id == prediction_id).first()
    if not pred:
        raise HTTPException(404, f"Prediction {prediction_id} not found")

    explainer = _get_explainer()
    if explainer is None:
        raise HTTPException(503, "Explainability engine not available. Ensure model is trained.")

    try:
        probs = np.array([[pred.p_sell or 0.0, pred.p_hold or 0.0, pred.p_buy or 0.0]])
        dummy_X = np.zeros((1, len(explainer.feature_names)))

        explanation = explainer.explain_prediction(dummy_X, probs[0])

        pred.shap_values = json.dumps(explanation, cls=_NumpyEncoder)
        pred.top_features = json.dumps(
            explanation.get("top_features", {}), cls=_NumpyEncoder
        )
        pred.explanation_latency = explanation.get("metadata", {}).get("total_latency_seconds")
        db.commit()

        return {
            "prediction_id": prediction_id,
            "symbol": pred.symbol,
            "decision": pred.decision,
            "confidence": pred.confidence,
            "explanation": explanation,
            "cached": False,
        }
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
