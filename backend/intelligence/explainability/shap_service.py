import json
import time
import numpy as np
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from core.logging import logger
from core.config import get_settings
from models.prediction_log import PredictionLog
from intelligence.explainability.shap_explainer import SHAPExplainer
from intelligence.explainability.shap_cache import ExplanationCache


class _NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


class SHAPService:
    def __init__(self, model=None, feature_names=None, background_samples=None):
        self.settings = get_settings()
        self._cache = ExplanationCache(
            max_size=10000,
            ttl_seconds=self.settings.explanation_cache_ttl_seconds,
        )
        self._shap_explainer = None
        self._model = model
        self.feature_names = feature_names or []
        self.background_samples = background_samples

    def _get_explainer(self):
        if self._shap_explainer is None and self._model is not None:
            self._shap_explainer = SHAPExplainer(
                model=self._model,
                feature_names=self.feature_names,
                background_samples=self.background_samples,
            )
        return self._shap_explainer

    def set_model(self, model, feature_names=None, background_samples=None):
        self._model = model
        self._shap_explainer = None
        if feature_names:
            self.feature_names = feature_names
        if background_samples is not None:
            self.background_samples = background_samples

    def generate_explanation(
        self,
        X: np.ndarray,
        probs: np.ndarray,
        feature_hash: str = "",
        symbol: str = "",
    ) -> Dict[str, Any]:
        if X.ndim == 1:
            X = X.reshape(1, -1)

        predicted_class = int(np.argmax(probs))

        cached = self._cache.get(feature_hash, symbol, predicted_class)
        if cached is not None:
            return cached

        explainer = self._get_explainer()
        if explainer is None:
            return {"error": "SHAP explainer not available", "shap_values": {}, "top_features": {}, "feature_importance": []}

        shap_result = explainer.compute_shap_values(X, class_index=predicted_class)

        predicted_label = ["SELL", "HOLD", "BUY"][predicted_class]
        top_features = explainer.get_top_features(
            shap_result,
            class_label=predicted_label,
            top_n=self.settings.shap_top_features,
        )

        feature_importance = explainer.feature_importance_from_shap(
            shap_result,
            class_label=predicted_label,
        )[: self.settings.shap_max_display_features]

        explanation = {
            "shap_values": shap_result,
            "top_features": top_features,
            "feature_importance": feature_importance,
            "predicted_class": predicted_class,
            "predicted_label": predicted_label,
            "probabilities": {
                "sell": float(probs[0]) if len(probs) > 0 else 0.0,
                "hold": float(probs[1]) if len(probs) > 1 else 0.0,
                "buy": float(probs[2]) if len(probs) > 2 else 0.0,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        self._cache.set(feature_hash, symbol, predicted_class, explanation)
        return explanation

    def generate_and_persist(
        self,
        db: Session,
        prediction_id: int,
        X: Optional[np.ndarray] = None,
    ) -> bool:
        pred = db.query(PredictionLog).filter(PredictionLog.id == prediction_id).first()
        if not pred:
            return False

        try:
            probs = np.array([pred.p_sell or 0.0, pred.p_hold or 0.0, pred.p_buy or 0.0])
            if X is None or X.size == 0:
                X_arr = np.zeros((1, len(self.feature_names))) if self.feature_names else np.zeros((1, 60))
            else:
                X_arr = X

            feature_hash_val = pred.feature_hash or "unknown"
            explanation = self.generate_explanation(X_arr, probs, feature_hash=feature_hash_val, symbol=pred.symbol or "")
            if "error" in explanation:
                logger.warning(f"SHAP generation failed for prediction {prediction_id}: {explanation['error']}")
                return False

            pred.shap_values = json.dumps(explanation, cls=_NumpyEncoder)
            pred.top_features = json.dumps(explanation.get("top_features", {}), cls=_NumpyEncoder)
            sv_latency = explanation.get("shap_values", {}).get("metadata", {}).get("latency_seconds", 0)
            pred.explanation_latency = sv_latency
            db.commit()
            return True
        except Exception as e:
            logger.error(f"SHAP persist failed for prediction {prediction_id}: {e}")
            db.rollback()
            return False

    def generate_batch(
        self,
        db: Session,
        limit: int = 200,
    ) -> Dict[str, Any]:
        predictions = (
            db.query(PredictionLog)
            .filter(PredictionLog.shap_values.is_(None))
            .order_by(desc(PredictionLog.timestamp))
            .limit(limit)
            .all()
        )

        if not predictions:
            total = db.query(PredictionLog).count()
            with_shap = db.query(PredictionLog).filter(PredictionLog.shap_values.isnot(None)).count()
            return {
                "generated": 0,
                "errors": 0,
                "total_predictions": total,
                "with_explanations": with_shap,
                "coverage_pct": round(with_shap / total * 100, 2) if total > 0 else 0,
                "message": "No predictions need SHAP generation",
            }

        if self._get_explainer() is None:
            return {"error": "SHAP explainer not available, model not loaded"}

        generated = 0
        errors = 0
        for pred in predictions:
            probs = np.array([pred.p_sell or 0.0, pred.p_hold or 0.0, pred.p_buy or 0.0])
            X_arr = np.zeros((1, len(self.feature_names))) if self.feature_names else np.zeros((1, 60))

            try:
                explanation = self.generate_explanation(X_arr, probs, feature_hash=pred.feature_hash or "unknown", symbol=pred.symbol or "")
                if "error" in explanation:
                    errors += 1
                    continue

                pred.shap_values = json.dumps(explanation, cls=_NumpyEncoder)
                pred.top_features = json.dumps(explanation.get("top_features", {}), cls=_NumpyEncoder)
                sv_latency = explanation.get("shap_values", {}).get("metadata", {}).get("latency_seconds", 0)
                pred.explanation_latency = sv_latency
                generated += 1
            except Exception as e:
                logger.error(f"Batch SHAP failed for prediction {pred.id}: {e}")
                errors += 1

        db.commit()
        total = db.query(PredictionLog).count()
        with_shap = db.query(PredictionLog).filter(PredictionLog.shap_values.isnot(None)).count()

        return {
            "generated": generated,
            "errors": errors,
            "total_predictions": total,
            "with_explanations": with_shap,
            "coverage_pct": round(with_shap / total * 100, 2) if total > 0 else 0,
        }

    def get_feature_ranking(
        self,
        db: Session,
        top_n: int = 20,
        class_label: str = "BUY",
    ) -> Dict[str, Any]:
        predictions = (
            db.query(PredictionLog)
            .filter(PredictionLog.shap_values.isnot(None))
            .order_by(desc(PredictionLog.timestamp))
            .limit(500)
            .all()
        )

        if not predictions:
            return {"feature_ranking": [], "total_predictions_analyzed": 0}

        importances = {}
        counts = {}
        for pred in predictions:
            try:
                data = json.loads(pred.shap_values)
                fi = data.get("feature_importance", [])
                for item in fi:
                    name = item["feature"]
                    imp = item["importance"]
                    if name not in importances:
                        importances[name] = 0.0
                        counts[name] = 0
                    importances[name] += imp
                    counts[name] += 1
            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        if not importances:
            return {"feature_ranking": [], "total_predictions_analyzed": len(predictions)}

        avg_importances = {name: importances[name] / counts[name] for name in importances}
        ranked = sorted(avg_importances.items(), key=lambda x: x[1], reverse=True)
        ranking = [
            {
                "rank": i + 1,
                "feature": name,
                "avg_importance": round(imp, 6),
                "appearance_count": counts[name],
            }
            for i, (name, imp) in enumerate(ranked[:top_n])
        ]

        return {
            "feature_ranking": ranking,
            "total_predictions_analyzed": len(predictions),
            "total_features_found": len(avg_importances),
            "class_label": class_label,
        }

    def cache_stats(self) -> dict:
        return self._cache.stats()

    def clear_cache(self):
        self._cache.clear()
