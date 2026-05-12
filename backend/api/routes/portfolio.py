from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core.logging import logger
from core.config import get_settings

router = APIRouter(prefix="/portfolio", tags=["portfolio_intelligence"])


def _get_portfolio_service(db_session=None):
    try:
        from intelligence.portfolio_analysis.service import PortfolioIntelligenceService
        from intelligence.portfolio_analysis.config import PortfolioConfig
        from core.analytics_db import AnalyticsDB

        settings = get_settings()
        config = PortfolioConfig(
            enabled=settings.portfolio_engine_enabled,
        )

        analytics = AnalyticsDB()
        service = PortfolioIntelligenceService(config=config, db=analytics)
        return service
    except Exception as e:
        logger.warning(f"Could not load PortfolioIntelligenceService: {e}")
        return None


@router.get("/risk")
async def get_portfolio_risk(db: Session = Depends(get_db)):
    service = _get_portfolio_service(db)
    if service is None:
        raise HTTPException(503, "Portfolio intelligence engine not available")

    try:
        analysis = service.analyze(db, persist=True)
        return analysis
    except Exception as e:
        logger.error(f"Portfolio risk analysis failed: {e}")
        raise HTTPException(500, f"Portfolio analysis failed: {str(e)}")


@router.get("/risk/no-persist")
async def get_portfolio_risk_no_persist(db: Session = Depends(get_db)):
    service = _get_portfolio_service(db)
    if service is None:
        raise HTTPException(503, "Portfolio intelligence engine not available")

    try:
        analysis = service.analyze(db, persist=False)
        return analysis
    except Exception as e:
        logger.error(f"Portfolio risk analysis failed: {e}")
        raise HTTPException(500, f"Portfolio analysis failed: {str(e)}")


@router.get("/history")
async def get_portfolio_history(
    limit: int = Query(default=20, ge=1, le=100),
):
    service = _get_portfolio_service()
    if service is None:
        raise HTTPException(503, "Portfolio intelligence engine not available")

    try:
        history = service.get_history(limit=limit)
        return {"snapshots": history, "total": len(history)}
    except Exception as e:
        logger.error(f"Failed to get portfolio history: {e}")
        raise HTTPException(500, str(e))


@router.get("/latest")
async def get_latest_portfolio_snapshot():
    service = _get_portfolio_service()
    if service is None:
        raise HTTPException(503, "Portfolio intelligence engine not available")

    try:
        snapshot = service.get_latest_snapshot()
        if snapshot is None:
            return {"status": "no_snapshot", "message": "No portfolio analysis performed yet"}
        return snapshot
    except Exception as e:
        logger.error(f"Failed to get latest portfolio snapshot: {e}")
        raise HTTPException(500, str(e))


@router.get("/health")
async def portfolio_health():
    service = _get_portfolio_service()
    if service is None:
        return {
            "status": "unavailable",
            "portfolio_engine_enabled": False,
        }

    snapshot = service.get_latest_snapshot()
    return {
        "status": "available",
        "portfolio_engine_enabled": True,
        "latest_snapshot": snapshot is not None,
        "num_positions": snapshot["num_positions"] if snapshot else 0,
        "overall_risk_level": snapshot["overall_risk_level"] if snapshot else None,
    }
