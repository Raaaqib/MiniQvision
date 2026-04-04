"""
LPR API Routes — FastAPI router for LPR whitelist and events.

Endpoints
---------
GET  /events             — list LPR events (paginated, filterable)
GET  /events/count       — count of LPR events
GET  /whitelist          — list whitelisted plates
POST /whitelist          — add plate to whitelist
DELETE /whitelist/{plate} — remove plate from whitelist
GET  /status             — LPR module status
"""

from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

if TYPE_CHECKING:
    from .manager import LPRManager


class AddPlateRequest(BaseModel):
    plate: str
    note: str = ""


def build_lpr_router(lpr_manager: "LPRManager") -> APIRouter:
    """Factory: build the LPR router with the given manager instance."""
    router = APIRouter()

    @router.get("/status")
    def lpr_status():
        return {
            "enabled": lpr_manager.enabled,
            "whitelist_count": len(lpr_manager.get_whitelist()) if lpr_manager.enabled else 0,
        }

    @router.get("/events")
    def list_lpr_events(
        camera_id: Optional[str] = Query(None),
        plate: Optional[str] = Query(None),
        alert_only: bool = Query(False),
        limit: int = Query(50, le=500),
        offset: int = Query(0),
    ):
        if not lpr_manager.enabled:
            raise HTTPException(503, "LPR module is disabled")
        return lpr_manager.get_events(
            camera_id=camera_id,
            plate=plate,
            alert_only=alert_only,
            limit=limit,
            offset=offset,
        )

    @router.get("/events/count")
    def count_lpr_events(alert_only: bool = Query(False)):
        if not lpr_manager.enabled:
            raise HTTPException(503, "LPR module is disabled")
        return {"count": lpr_manager.db.count_events(alert_only=alert_only)}

    @router.get("/whitelist")
    def list_whitelist():
        if not lpr_manager.enabled:
            raise HTTPException(503, "LPR module is disabled")
        return lpr_manager.get_whitelist()

    @router.post("/whitelist")
    def add_to_whitelist(body: AddPlateRequest):
        if not lpr_manager.enabled:
            raise HTTPException(503, "LPR module is disabled")
        success = lpr_manager.add_plate(body.plate, body.note)
        if not success:
            raise HTTPException(400, "Failed to add plate")
        return {"status": "ok", "plate": body.plate.upper().strip()}

    @router.delete("/whitelist/{plate}")
    def remove_from_whitelist(plate: str):
        if not lpr_manager.enabled:
            raise HTTPException(503, "LPR module is disabled")
        success = lpr_manager.remove_plate(plate)
        if not success:
            raise HTTPException(404, "Plate not found or remove failed")
        return {"status": "ok", "plate": plate.upper().strip()}

    return router
