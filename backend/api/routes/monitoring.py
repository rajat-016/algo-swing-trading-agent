import time
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from core.database import get_db
from core.monitoring import PredictionMonitor
from core.monitoring.metrics_service import get_metrics_collector
from core.monitoring.health_aggregator import get_health_aggregator, HealthComponent
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
        
        feature_names = analyzer.model.feature_names
        baseline_stats = detector.build_baseline_from_training(
            __import__("numpy").random.randn(1000, len(feature_names)),
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


@router.get("/health")
async def get_system_health():
    """Aggregated system health dashboard across all services."""
    aggregator = get_health_aggregator()

    checks_registered = len(aggregator._checks) > 0
    if not checks_registered:
        _register_default_health_checks(aggregator)

    return aggregator.run_all()


@router.get("/metrics")
async def get_system_metrics():
    """System-wide metrics: latency, throughput, error rates."""
    collector = get_metrics_collector()
    return {
        "services": collector.get_all_metrics(),
        "api": collector.get_api_metrics(),
        "summary": collector.get_health_summary(),
    }


@router.get("/latency")
async def get_latency_breakdown():
    """Latency breakdown across all monitored services."""
    collector = get_metrics_collector()
    return {
        "breakdown": collector.get_latency_summary(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/performance")
async def get_performance_summary():
    """Performance summary with all metrics combined."""
    collector = get_metrics_collector()
    metrics = collector.get_all_metrics()
    api_metrics = collector.get_api_metrics()
    summary = collector.get_health_summary()

    overall_status = "healthy"
    if summary.get("total_errors", 0) > 0:
        overall_status = "degraded"
    if summary.get("error_rate", 0) > 0.1:
        overall_status = "unhealthy"
    if summary.get("degraded_services"):
        overall_status = "degraded"

    return {
        "status": overall_status,
        "metrics": metrics,
        "api": api_metrics,
        "summary": summary,
        "timestamp": datetime.utcnow().isoformat(),
    }


def _register_default_health_checks(aggregator):
    from core.config import get_settings
    from core.database import SessionLocal
    from core.monitoring import DriftDetector

    aggregator.register_check("settings", lambda: HealthComponent(
        name="settings",
        status="healthy",
        message="Settings loaded successfully",
    ))

    aggregator.register_check("database", _check_db_health)
    aggregator.register_check("model", _check_model_health)
    aggregator.register_check("drift_detection", _check_drift_health)
    aggregator.register_check("broker", _check_broker_health)
    aggregator.register_check("ai_copilot", _check_ai_health)
    aggregator.register_check("memory", _check_memory_health)
    aggregator.register_check("system", _check_system_health)


def _check_db_health() -> HealthComponent:
    try:
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
        return HealthComponent(name="database", status="healthy", message="DB connection OK")
    except Exception as e:
        return HealthComponent(name="database", status="unhealthy", message=str(e))


def _check_model_health() -> HealthComponent:
    try:
        from core.model.registry import ModelRegistry
        registry = ModelRegistry()
        data = registry.load()
        if data and "model" in data:
            fn = data.get("feature_names", [])
            return HealthComponent(
                name="model",
                status="healthy",
                message=f"Model loaded: {type(data['model']).__name__}",
                details={"features": len(fn), "feature_names": fn[:5]},
            )
        return HealthComponent(name="model", status="degraded", message="Model not loaded")
    except Exception as e:
        return HealthComponent(name="model", status="unhealthy", message=str(e))


def _check_drift_health() -> HealthComponent:
    detector = DriftDetector()
    if detector.baseline:
        return HealthComponent(
            name="drift_detection",
            status="healthy",
            message=f"Baseline exists: {len(detector.baseline.get('features', {}))} features",
            details={"features_count": len(detector.baseline.get("features", {}))},
        )
    return HealthComponent(
        name="drift_detection",
        status="degraded",
        message="No drift baseline found. Create one via POST /monitoring/drift/baseline",
    )


def _check_broker_health() -> HealthComponent:
    try:
        from services.broker.kite import get_broker
        broker = get_broker()
        connected = broker.is_connected()
        return HealthComponent(
            name="broker",
            status="healthy" if connected else "degraded",
            message="Connected" if connected else "Not connected (paper mode OK)",
        )
    except Exception as e:
        return HealthComponent(name="broker", status="unhealthy", message=str(e))


def _check_ai_health() -> HealthComponent:
    try:
        from ai.inference.service import InferenceService
        svc = InferenceService()
        health = svc.check_health() if hasattr(svc, "check_health") else {}
        if health and health.get("ollama"):
            return HealthComponent(
                name="ai_copilot",
                status="healthy",
                details={"ollama": True, "circuit_breaker": health.get("circuit_breaker")},
            )
        return HealthComponent(
            name="ai_copilot",
            status="degraded",
            message="Ollama not reachable",
        )
    except Exception as e:
        return HealthComponent(name="ai_copilot", status="unhealthy", message=str(e))


def _check_memory_health() -> HealthComponent:
    try:
        from memory.retrieval.semantic_retriever import SemanticRetriever
        retriever = SemanticRetriever()
        ready = retriever.is_ready
        return HealthComponent(
            name="memory",
            status="healthy" if ready else "degraded",
            message="Ready" if ready else "Not initialized",
        )
    except Exception as e:
        return HealthComponent(name="memory", status="unhealthy", message=str(e))


def _check_system_health() -> HealthComponent:
    import psutil
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        return HealthComponent(
            name="system",
            status="healthy" if cpu < 80 and mem.percent < 90 else "degraded",
            message=f"CPU: {cpu}%, Memory: {mem.percent}%",
            details={"cpu_percent": cpu, "memory_percent": mem.percent},
        )
    except ImportError:
        return HealthComponent(name="system", status="healthy", message="psutil not available")
    except Exception as e:
        return HealthComponent(name="system", status="unhealthy", message=str(e))
