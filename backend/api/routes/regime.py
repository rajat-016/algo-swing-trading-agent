import json
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from core.logging import logger
from core.config import get_settings

router = APIRouter(prefix="/regime", tags=["market_regime"])


def _get_regime_service():
    try:
        from intelligence.market_regime.service import RegimeService
        from intelligence.market_regime.config import RegimeConfig
        from core.analytics_db import AnalyticsDB

        settings = get_settings()
        config = RegimeConfig(
            enabled=settings.regime_engine_enabled,
            ema_short=settings.regime_ema_short,
            ema_long=settings.regime_ema_long,
            sideways_threshold_pct=settings.regime_sideways_threshold_pct,
            adx_trend_threshold=settings.regime_adx_trend_threshold,
            high_vol_atr_pct=settings.regime_high_vol_atr_pct,
            low_vol_atr_pct=settings.regime_low_vol_atr_pct,
            breakout_volume_ratio=settings.regime_breakout_volume_ratio,
            event_volume_spike_ratio=settings.regime_event_volume_spike_ratio,
            stability_lookback=settings.regime_stability_lookback,
        )

        db = AnalyticsDB()
        service = RegimeService(config=config)
        from intelligence.market_regime.persistence import RegimePersistence
        persistence = RegimePersistence(config, db)
        persistence.initialize(db)
        service.persistence = persistence
        return service
    except Exception as e:
        logger.warning(f"Could not load RegimeService: {e}")
        return None


@router.get("/current")
async def get_current_regime():
    service = _get_regime_service()
    if service is None:
        raise HTTPException(503, "Regime engine not available")

    current = service.get_current_regime()
    if current is None:
        return {
            "regime": "unknown",
            "confidence": 0.0,
            "message": "No regime analysis performed yet. Use POST /regime/analyze to run analysis.",
        }

    return current.to_dict()


@router.post("/analyze")
async def analyze_regime(
    ohlcv_data: Optional[str] = Query(None, description="JSON array of OHLCV data"),
):
    service = _get_regime_service()
    if service is None:
        raise HTTPException(503, "Regime engine not available")

    if ohlcv_data:
        try:
            import pandas as pd
            data = json.loads(ohlcv_data)
            df = pd.DataFrame(data)
            required = {"close"}
            if not required.issubset(df.columns):
                raise HTTPException(400, f"OHLCV data must contain at least 'close' column")
            output = service.analyze(df)
            return output.to_dict()
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid JSON in ohlcv_data parameter")
        except Exception as e:
            logger.error(f"Regime analysis failed: {e}")
            raise HTTPException(500, f"Regime analysis failed: {str(e)}")

    return {
        "message": "No OHLCV data provided. Use ohlcv_data parameter with JSON array of OHLCV records.",
        "usage": {
            "ohlcv_data": "JSON array of dicts with keys: close, high, low, volume (at minimum 'close' required)",
        },
    }


@router.get("/history")
async def get_regime_history(
    limit: int = Query(default=100, ge=1, le=1000),
):
    service = _get_regime_service()
    if service is None:
        raise HTTPException(503, "Regime engine not available")

    return {"regimes": service.get_regime_history(limit=limit)}


@router.get("/stats")
async def get_regime_stats():
    service = _get_regime_service()
    if service is None:
        raise HTTPException(503, "Regime engine not available")

    return service.get_regime_stats()


@router.get("/transitions")
async def get_transitions(
    n: int = Query(default=10, ge=1, le=100),
):
    service = _get_regime_service()
    if service is None:
        raise HTTPException(503, "Regime engine not available")

    return {"transitions": service.get_transitions(n=n)}


@router.get("/distribution")
async def get_regime_distribution(
    days: int = Query(default=30, ge=1, le=365),
):
    service = _get_regime_service()
    if service is None:
        raise HTTPException(503, "Regime engine not available")

    return {"distribution": service.get_regime_distribution(days=days)}


@router.get("/health")
async def regime_health():
    service = _get_regime_service()
    if service is None:
        return {
            "status": "unavailable",
            "regime_engine_enabled": False,
            "message": "Regime engine not available",
        }

    stats = service.get_regime_stats()
    current = service.get_current_regime()
    return {
        "status": "available",
        "regime_engine_enabled": True,
        "current_regime": current.regime.value if current else None,
        "current_confidence": current.confidence if current else None,
        "tracker_total_transitions": stats.get("total_transitions", 0),
        "persistence_ready": stats.get("persistence_ready", False),
    }
