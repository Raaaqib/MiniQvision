"""
LPR API Routes — mount these on the existing Raaqib FastAPI app.

In src/api/app.py add:

    from src.api.lpr_routes import build_lpr_router
    app.include_router(build_lpr_router(lpr_manager), prefix="/api/lpr", tags=["LPR"])

Endpoints
---------
GET  /api/lpr/events                   — paginated event log
GET  /api/lpr/events/{camera_id}       — filtered by camera
GET  /api/lpr/alerts                   — unknown-plate alerts only
GET  /api/lpr/whitelist                — list all whitelisted plates
POST /api/lpr/whitelist                — add a plate
DELETE /api/lpr/whitelist/{plate}      — remove a plate
GET  /api/lpr/zones                    — list configured zones per camera
GET  /api/lpr/stats                    — aggregate stats
"""

from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


# ── Request / Response models ──────────────────────────────────────────────

class WhitelistAddRequest(BaseModel):
    plate: str
    note: Optional[str] = ""


class WhitelistEntry(BaseModel):
    plate: str
    note: Optional[str]
    added_at: str


class LPREventResponse(BaseModel):
    id: int
    camera_id: str
    zone_id: str
    plate: str
    confidence: float
    known: bool
    alert: bool
    snapshot_path: Optional[str]
    created_at: str


# ── Router factory ─────────────────────────────────────────────────────────

def build_lpr_router(lpr_manager) -> APIRouter:
    """
    Parameters
    ----------
    lpr_manager : LPRManager
        The application-level LPRManager instance.
    """
    router = APIRouter()

    # ── Events ────────────────────────────────────────────────────────

    @router.get("/events", summary="List LPR events")
    def list_events(
        camera_id: Optional[str] = Query(None),
        plate: Optional[str] = Query(None),
        alert_only: bool = Query(False),
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        if not lpr_manager.enabled:
            raise HTTPException(status_code=503, detail="LPR is disabled")
        events = lpr_manager.get_events(
            camera_id=camera_id,
            plate=plate,
            alert_only=alert_only,
            limit=limit,
            offset=offset,
        )
        return {"events": events, "count": len(events), "offset": offset}

    @router.get("/events/{camera_id}", summary="Events for a specific camera")
    def events_by_camera(
        camera_id: str,
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ):
        if not lpr_manager.enabled:
            raise HTTPException(status_code=503, detail="LPR is disabled")
        events = lpr_manager.get_events(camera_id=camera_id, limit=limit, offset=offset)
        return {"camera_id": camera_id, "events": events, "count": len(events)}

    @router.get("/alerts", summary="Unknown plate alerts only")
    def list_alerts(
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ):
        if not lpr_manager.enabled:
            raise HTTPException(status_code=503, detail="LPR is disabled")
        events = lpr_manager.get_events(alert_only=True, limit=limit, offset=offset)
        total = lpr_manager.db.count_events(alert_only=True)
        return {"alerts": events, "count": len(events), "total": total, "offset": offset}

    # ── Whitelist ──────────────────────────────────────────────────────

    @router.get("/whitelist", summary="Get all whitelisted plates")
    def get_whitelist():
        if not lpr_manager.enabled:
            raise HTTPException(status_code=503, detail="LPR is disabled")
        return {"whitelist": lpr_manager.get_whitelist()}

    @router.post("/whitelist", summary="Add plate to whitelist", status_code=201)
    def add_plate(body: WhitelistAddRequest):
        if not lpr_manager.enabled:
            raise HTTPException(status_code=503, detail="LPR is disabled")
        if not body.plate.strip():
            raise HTTPException(status_code=422, detail="Plate cannot be empty")
        ok = lpr_manager.add_plate(body.plate, body.note or "")
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to add plate")
        return {"added": body.plate.upper().strip(), "note": body.note}

    @router.delete("/whitelist/{plate}", summary="Remove plate from whitelist")
    def remove_plate(plate: str):
        if not lpr_manager.enabled:
            raise HTTPException(status_code=503, detail="LPR is disabled")
        ok = lpr_manager.remove_plate(plate)
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to remove plate")
        return {"removed": plate.upper().strip()}

    # ── Zones ──────────────────────────────────────────────────────────

    @router.get("/zones", summary="List configured LPR zones per camera")
    def list_zones():
        if not lpr_manager.enabled:
            raise HTTPException(status_code=503, detail="LPR is disabled")
        result = {}
        for cam_id, pipeline in lpr_manager._pipelines.items():
            result[cam_id] = [
                {"id": z.id, "polygon": z.polygon}
                for z in pipeline.zones
            ]
        return {"cameras": result}

    # ── Stats ──────────────────────────────────────────────────────────

    @router.get("/stats", summary="Aggregate LPR statistics")
    def stats():
        if not lpr_manager.enabled:
            raise HTTPException(status_code=503, detail="LPR is disabled")
        total = lpr_manager.db.count_events(alert_only=False)
        alerts = lpr_manager.db.count_events(alert_only=True)
        return {
            "total_events": total,
            "total_alerts": alerts,
            "total_known": total - alerts,
            "active_cameras": list(lpr_manager._pipelines.keys()),
            "whitelisted_count": len(lpr_manager.whitelist),
        }

    return router
