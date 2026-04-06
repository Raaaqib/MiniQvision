"""
Raaqib NVR — FastAPI Web Server
REST API for cameras, events, clips, snapshots, and system status.
"""

from __future__ import annotations
import time
import logging
import cv2
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)


def create_app(state_dict: dict, db_path: str, config) -> FastAPI:
    """Create and configure FastAPI app."""
    import psutil

    app = FastAPI(
        title="Raaqib NVR API",
        description="AI-powered NVR REST API",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from src.core.database import Database
    db = Database(db_path)

    # Cache startup time for uptime calculation
    _start_time = time.time()

    # Pre-build model-to-camera map (cached at startup)
    _model_camera_map: dict[str, list[str]] = {model_id: [] for model_id in config.models}
    for cam in config.enabled_cameras:
        _model_camera_map.setdefault(cam.model, []).append(cam.id)

    def _build_models_summary() -> dict:
        models = {}
        for model_id, model_cfg in config.models.items():
            models[model_id] = {
                "path": model_cfg.path,
                "device": model_cfg.device,
                "pool_size": model_cfg.pool_size,
                "confidence_threshold": model_cfg.confidence_threshold,
                "classes": model_cfg.classes,
                "cameras": _model_camera_map.get(model_id, []),
            }
        return models

    def _get_system_stats() -> dict:
        """Get system resource usage."""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=None),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent if hasattr(psutil, "disk_usage") else 0,
            }
        except Exception:
            return {"cpu_percent": 0, "memory_percent": 0, "disk_percent": 0}

    def _get_storage_stats() -> dict:
        """Get recording storage statistics."""
        rec_dir = Path(config.recording.output_dir)
        snap_dir = Path(config.snapshots.output_dir)
        try:
            recordings = list(rec_dir.glob("*.mp4")) if rec_dir.exists() else []
            snapshots = list(snap_dir.glob("*.jpg")) if snap_dir.exists() else []
            total_size = sum(f.stat().st_size for f in recordings)
            return {
                "recordings_count": len(recordings),
                "snapshots_count": len(snapshots),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
            }
        except Exception:
            return {"recordings_count": 0, "snapshots_count": 0, "total_size_mb": 0}

    def _camera_payload(camera_id: str) -> dict | None:
        cam_cfg = config.get_camera(camera_id)
        if cam_cfg is None:
            return None

        state = dict(state_dict.get(camera_id, {}))
        model_cfg = config.models.get(cam_cfg.model)
        state.update({
            "id": cam_cfg.id,
            "name": cam_cfg.name,
            "model": cam_cfg.model,
            "model_path": model_cfg.path if model_cfg else None,
            "model_device": model_cfg.device if model_cfg else None,
            "status": "connected" if state.get("connected") else "disconnected",
        })
        return state

    # ── System ────────────────────────────────────────────────────────────────

    @app.get("/api/status")
    def get_status():
        cameras_state = {
            cam.id: _camera_payload(cam.id)
            for cam in config.enabled_cameras
        }
        # Aggregate detection stats from all cameras
        total_detections = sum(
            state_dict.get(cam.id, {}).get("detection_count", 0)
            for cam in config.enabled_cameras
        )
        active_events = state_dict.get("active_events", [])

        return {
            "status": "running",
            "uptime_seconds": round(time.time() - _start_time, 1),
            "timestamp": time.time(),
            "system": _get_system_stats(),
            "cameras": cameras_state,
            "detection": {
                "total_detections": total_detections,
                "active_events": len(active_events),
            },
            "storage": _get_storage_stats(),
            "models": _build_models_summary(),
            "active_events": active_events,
        }

    @app.get("/api/stats")
    def get_stats():
        return db.get_stats()

    # ── Cameras ───────────────────────────────────────────────────────────────

    @app.get("/api/cameras")
    def list_cameras():
        return {
            cam.id: _camera_payload(cam.id)
            for cam in config.enabled_cameras
        }

    @app.get("/api/cameras/{camera_id}")
    def get_camera(camera_id: str):
        camera = _camera_payload(camera_id)
        if camera is None:
            raise HTTPException(404, f"Camera {camera_id} not found")
        return camera

    @app.get("/api/models")
    def list_models():
        return _build_models_summary()

    # ── Live MJPEG stream ─────────────────────────────────────────────────────

    @app.get("/api/cameras/{camera_id}/stream")
    def stream_camera(camera_id: str):
        if camera_id not in [c.id for c in config.enabled_cameras]:
            raise HTTPException(404, f"Camera {camera_id} not found")

        def generate():
            import numpy as np
            blank = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(blank, "NO SIGNAL", (170, 250),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (80, 80, 80), 2)
            _, blank_jpeg = cv2.imencode('.jpg', blank)
            blank_bytes = blank_jpeg.tobytes()

            jpeg_key = f"{camera_id}:jpeg"
            while True:
                payload = state_dict.get(jpeg_key) or blank_bytes
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                       + payload + b'\r\n')
                time.sleep(0.05)  # ~20 fps

        return StreamingResponse(
            generate(),
            media_type='multipart/x-mixed-replace; boundary=frame'
        )

    @app.get("/api/cameras/{camera_id}/snapshot.jpg")
    def latest_snapshot(camera_id: str):
        """Return the latest frame as a single JPEG (for polling)."""
        from fastapi.responses import Response
        jpeg_key = f"{camera_id}:jpeg"
        data = state_dict.get(jpeg_key)
        if data is None:
            raise HTTPException(404, "No frame available yet")
        return Response(content=data, media_type="image/jpeg")

    # ── Events ────────────────────────────────────────────────────────────────

    @app.get("/api/events")
    def list_events(
        camera_id: Optional[str] = Query(None),
        label: Optional[str] = Query(None),
        limit: int = Query(50, le=500),
        offset: int = Query(0),
    ):
        return db.get_events(
            camera_id=camera_id or "",
            label=label or "",
            limit=limit,
            offset=offset,
        )

    @app.get("/api/events/active")
    def list_active_events():
        return state_dict.get("active_events", [])

    # ── Recordings ────────────────────────────────────────────────────────────

    @app.get("/api/recordings")
    def list_recordings(camera_id: Optional[str] = Query(None)):
        rec_dir = Path(config.recording.output_dir)
        clips = sorted(rec_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if camera_id:
            clips = [c for c in clips if c.name.startswith(camera_id)]
        return [
            {
                "filename": c.name,
                "path": str(c),
                "size_mb": round(c.stat().st_size / 1024 / 1024, 2),
                "modified": c.stat().st_mtime,
            }
            for c in clips[:100]
        ]

    @app.get("/api/recordings/{filename}")
    def download_recording(filename: str):
        path = Path(config.recording.output_dir) / filename
        if not path.exists():
            raise HTTPException(404, "Recording not found")
        return FileResponse(str(path), media_type="video/mp4", filename=filename)

    # ── Snapshots ─────────────────────────────────────────────────────────────

    @app.get("/api/snapshots")
    def list_snapshots(camera_id: Optional[str] = Query(None)):
        snap_dir = Path(config.snapshots.output_dir)
        snaps = sorted(snap_dir.glob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)
        if camera_id:
            snaps = [s for s in snaps if s.name.startswith(camera_id)]
        return [
            {
                "filename": s.name,
                "path": str(s),
                "size_kb": round(s.stat().st_size / 1024, 1),
                "modified": s.stat().st_mtime,
            }
            for s in snaps[:200]
        ]

    @app.get("/api/snapshots/{filename}")
    def get_snapshot(filename: str):
        path = Path(config.snapshots.output_dir) / filename
        if not path.exists():
            raise HTTPException(404, "Snapshot not found")
        return FileResponse(str(path), media_type="image/jpeg")

    @app.get("/")
    def root():
        return {
            "service": "Raaqib NVR",
            "api_docs": "/docs",
        }

    # ── LPR Routes ────────────────────────────────────────────────────────────
    if config.lpr.get("enabled", False):
        try:
            from src.core.lpr import LPRManager
            from src.core.lpr.api_routes import build_lpr_router

            lpr_manager = LPRManager(
                config={"lpr": config.lpr},
                db_path=db_path,
                mqtt_client=None,
            )
            app.include_router(
                build_lpr_router(lpr_manager),
                prefix="/api/lpr",
                tags=["LPR"],
            )
            logger.info("[LPR] API routes registered at /api/lpr")
        except Exception as e:
            logger.error(f"[LPR] Failed to register API routes: {e}")

    # ── Serve Web UI static files ─────────────────────────────────────────
    web_dir = Path(__file__).resolve().parent.parent / "web"
    if web_dir.is_dir():
        app.mount("/ui", StaticFiles(directory=str(web_dir), html=True), name="web-ui")
        logger.info(f"Serving Web UI from {web_dir} at /ui")

    return app


def run_api(config, state_dict: dict, stop_event, db_path: str):
    """API server process entry point."""
    import uvicorn
    from src.core.log_utils import configure_logging
    configure_logging("api")

    app = create_app(state_dict, db_path, config)
    uvicorn.run(
        app,
        host=config.api.host,
        port=config.api.port,
        log_level="warning",
    )
