from fastapi import APIRouter, HTTPException, Query

from core.logging import logger
from core.governance import get_governance_manager

router = APIRouter(prefix="/governance", tags=["governance"])


@router.get("/health")
async def governance_health():
    gov = get_governance_manager()
    return {"status": "ok", "governance": gov.check_health()}


@router.get("/audit/logs")
async def audit_logs(
    limit: int = Query(default=100, ge=1, le=1000),
    action: str = Query(default=None),
    component: str = Query(default=None),
    status: str = Query(default=None),
):
    gov = get_governance_manager()
    if not gov.audit.enabled:
        raise HTTPException(503, "Audit logging is disabled")
    try:
        entries = gov.audit.query(
            action=action,
            component=component,
            status=status,
            limit=limit,
        )
        return {"status": "ok", "entries": entries, "count": len(entries)}
    except Exception as e:
        logger.error(f"Failed to retrieve audit logs: {e}")
        raise HTTPException(500, f"Failed to retrieve audit logs: {str(e)}")


@router.get("/audit/stats")
async def audit_stats():
    gov = get_governance_manager()
    if not gov.audit.enabled:
        raise HTTPException(503, "Audit logging is disabled")
    try:
        stats = gov.audit.get_stats()
        return {"status": "ok", "stats": stats}
    except Exception as e:
        logger.error(f"Failed to get audit stats: {e}")
        raise HTTPException(500, f"Failed to get audit stats: {str(e)}")


@router.get("/execution/blocked")
async def execution_blocked_attempts(
    limit: int = Query(default=50, ge=1, le=500),
):
    gov = get_governance_manager()
    blocked = gov.execution.get_blocked_attempts(limit=limit)
    return {"status": "ok", "blocked_attempts": blocked, "count": len(blocked)}


@router.get("/integrity/stats")
async def integrity_stats():
    gov = get_governance_manager()
    return {
        "status": "ok",
        "integrity_validation_enabled": gov.integrity.enabled,
    }
