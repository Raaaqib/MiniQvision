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

    from database import Database
    db = Database(db_path)

    # ── System ────────────────────────────────────────────────────────────────

    @app.get("/api/status")
    def get_status():
        cameras_state = {
            k: v for k, v in state_dict.items()
            if k not in ("events", "active_events") and ":" not in k
        }
        return {
            "status": "running",
            "timestamp": time.time(),
            "cameras": cameras_state,
            "active_events": state_dict.get("active_events", []),
        }

    @app.get("/api/stats")
    def get_stats():
        return db.get_stats()

    # ── Cameras ───────────────────────────────────────────────────────────────

    @app.get("/api/cameras")
    def list_cameras():
        return {
            k: v for k, v in state_dict.items()
            if k not in ("events", "active_events") and ":" not in k
        }

    @app.get("/api/cameras/{camera_id}")
    def get_camera(camera_id: str):
        state = state_dict.get(camera_id)
        if state is None:
            raise HTTPException(404, f"Camera {camera_id} not found")
        return state

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
        return db.get_events(camera_id=camera_id, label=label,
                             limit=limit, offset=offset)

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

    # ── Static / Streamlit proxy hint ─────────────────────────────────────────

    @app.get("/")
    def root():
        return {
            "service": "Raaqib NVR",
            "api_docs": "/docs",
            "dashboard": "http://localhost:8501",
        }

    # ── Serve Web UI static files ─────────────────────────────────────────
    web_dir = Path(__file__).resolve().parent.parent / "web"
    if web_dir.is_dir():
        app.mount("/ui", StaticFiles(directory=str(web_dir), html=True), name="web-ui")
        logger.info(f"Serving Web UI from {web_dir} at /ui")

    return app


def run_api(config, state_dict: dict, stop_event, db_path: str):
    """API server process entry point."""
    import uvicorn
    from log_utils import configure_logging
    configure_logging("api")

    app = create_app(state_dict, db_path, config)
    uvicorn.run(
        app,
        host=config.api.host,
        port=config.api.port,
        log_level="warning",
    )
