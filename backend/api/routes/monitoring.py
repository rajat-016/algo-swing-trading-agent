from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.monitoring import PredictionMonitor
from core.logging import logger

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/predictions")
async def get_predictions(limit: int = 50, db: Session = Depends(get_db)):
    monitor = PredictionMonitor(db)
    predictions = monitor.get_recent_predictions(limit)
    return {"predictions": predictions, "count": len(predictions)}


@router.get("/accuracy")
async def get_live_accuracy(lookback_days: int = 30, db: Session = Depends(get_db)):
    monitor = PredictionMonitor(db)
    accuracy = monitor.get_live_accuracy(lookback_days)
    calibration = monitor.get_confidence_calibration(lookback_days)
    return {
        "lookback_days": lookback_days,
        "accuracy": accuracy,
        "calibration": calibration,
    }


@router.get("/drift")
async def get_drift_status():
    from core.monitoring import DriftDetector
    detector = DriftDetector()
    
    if not detector.baseline:
        return {"status": "NO_BASELINE", "message": "No drift baseline found"}
    
    return {
        "status": "OK",
        "baseline_version": detector.baseline.get("model_version", "unknown"),
        "baseline_created": detector.baseline.get("created_at"),
        "features_count": len(detector.baseline.get("features", {})),
    }


@router.post("/drift/baseline")
async def create_drift_baseline(db: Session = Depends(get_db)):
    """Create drift baseline from current model and recent data."""
    from core.monitoring import DriftDetector
    from services.ai.analyzer import StockAnalyzer
    from services.broker.kite import KiteBroker
    
    try:
        broker = KiteBroker()
        analyzer = StockAnalyzer(broker)
        
        if not analyzer.model or not analyzer.model.is_trained():
            return {"error": "Model not loaded"}
        
        detector = DriftDetector()
        
        # Build baseline from model's training data summary
        # In practice, you'd want to use actual training data
        feature_names = analyzer.model.feature_names
        baseline_stats = detector.build_baseline_from_training(
            np.random.randn(1000, len(feature_names)),  # Placeholder
            feature_names
        )
        
        success = detector.save_baseline(baseline_stats)
        
        return {
            "success": success,
            "features": len(baseline_stats),
            "message": "Baseline saved" if success else "Failed to save baseline"
        }
    except Exception as e:
        logger.error(f"Failed to create baseline: {e}")
        return {"error": str(e)}
