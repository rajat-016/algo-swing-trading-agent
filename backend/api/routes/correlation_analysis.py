from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core.logging import logger
from core.config import get_settings

router = APIRouter(prefix="/correlation", tags=["correlation_analysis"])


def _get_correlation_service():
    try:
        from core.analytics_db import AnalyticsDB
        from intelligence.portfolio_analysis.correlation.service import CorrelationAnalysisService

        analytics = AnalyticsDB()
        service = CorrelationAnalysisService(db=analytics)
        return service
    except Exception as e:
        logger.warning(f"Could not load CorrelationAnalysisService: {e}")
        return None


@router.post("/analyze")
async def analyze_correlations(db: Session = Depends(get_db)):
    service = _get_correlation_service()
    if service is None:
        raise HTTPException(503, "Correlation analysis engine not available")

    try:
        analysis = service.analyze(db, persist=True)
        return analysis
    except Exception as e:
        logger.error(f"Correlation analysis failed: {e}")
        raise HTTPException(500, f"Correlation analysis failed: {str(e)}")


@router.get("/rolling")
async def get_rolling_correlation(db: Session = Depends(get_db)):
    service = _get_correlation_service()
    if service is None:
        raise HTTPException(503, "Correlation analysis engine not available")

    try:
        analysis = service.analyze(db, persist=False)
        return {
            "rolling": analysis.get("rolling"),
            "regime_label": analysis.get("regime_label"),
            "timestamp": analysis.get("timestamp"),
        }
    except Exception as e:
        logger.error(f"Rolling correlation analysis failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/clusters")
async def get_sector_clusters(db: Session = Depends(get_db)):
    service = _get_correlation_service()
    if service is None:
        raise HTTPException(503, "Correlation analysis engine not available")

    try:
        analysis = service.analyze(db, persist=False)
        return {
            "sector_clustering": analysis.get("sector_clustering"),
            "regime_label": analysis.get("regime_label"),
            "timestamp": analysis.get("timestamp"),
        }
    except Exception as e:
        logger.error(f"Sector clustering analysis failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/instability")
async def get_instability_alerts(db: Session = Depends(get_db)):
    service = _get_correlation_service()
    if service is None:
        raise HTTPException(503, "Correlation analysis engine not available")

    try:
        analysis = service.analyze(db, persist=False)
        return {
            "instability": analysis.get("instability"),
            "regime_label": analysis.get("regime_label"),
            "timestamp": analysis.get("timestamp"),
        }
    except Exception as e:
        logger.error(f"Instability analysis failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/diversification")
async def get_diversification_score(db: Session = Depends(get_db)):
    service = _get_correlation_service()
    if service is None:
        raise HTTPException(503, "Correlation analysis engine not available")

    try:
        analysis = service.analyze(db, persist=False)
        return {
            "diversification": analysis.get("diversification"),
            "regime_label": analysis.get("regime_label"),
            "timestamp": analysis.get("timestamp"),
        }
    except Exception as e:
        logger.error(f"Diversification scoring failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/history")
async def get_correlation_history(
    limit: int = Query(default=20, ge=1, le=100),
):
    service = _get_correlation_service()
    if service is None:
        raise HTTPException(503, "Correlation analysis engine not available")

    try:
        history = service.get_history(limit=limit)
        return {"snapshots": history, "total": len(history)}
    except Exception as e:
        logger.error(f"Failed to get correlation history: {e}")
        raise HTTPException(500, str(e))


@router.get("/latest")
async def get_latest_correlation_snapshot():
    service = _get_correlation_service()
    if service is None:
        raise HTTPException(503, "Correlation analysis engine not available")

    try:
        snapshot = service.get_latest()
        if snapshot is None:
            return {"status": "no_snapshot", "message": "No correlation analysis performed yet"}
        return snapshot
    except Exception as e:
        logger.error(f"Failed to get latest correlation snapshot: {e}")
        raise HTTPException(500, str(e))


@router.get("/health")
async def correlation_health():
    service = _get_correlation_service()
    if service is None:
        return {"status": "unavailable", "correlation_engine": False}

    latest = service.get_latest()
    return {
        "status": "available",
        "correlation_engine": True,
        "latest_snapshot": latest is not None,
        "current_regime": latest.get("correlation_regime") if latest else None,
        "diversification_score": latest.get("diversification_score") if latest else None,
    }
