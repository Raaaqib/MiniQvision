"""
Raaqib NVR — Configuration Parsing & Validation
"""

from __future__ import annotations
import yaml
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from const import (
    DEFAULT_CONFIDENCE, DEFAULT_IOU, DEFAULT_MODEL,
    DEFAULT_PRE_CAPTURE_S, DEFAULT_POST_CAPTURE_S, DEFAULT_MAX_CLIP_S,
    DEFAULT_FPS, DEFAULT_CRF, DEFAULT_CODEC, DEFAULT_RETAIN_DAYS,
    API_HOST, API_PORT, DB_PATH, DIR_RECORDINGS, DIR_SNAPSHOTS,
    DEFAULT_WIDTH, DEFAULT_HEIGHT, MIN_CONTOUR_AREA
)

logger = logging.getLogger(__name__)


# ── Camera Config ─────────────────────────────────────────────────────────────

@dataclass
class CameraConfig:
    id: str
    name: str
    source: str                     # RTSP URL or int (USB index as string)
    enabled: bool = True
    fps_target: int = DEFAULT_FPS
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    # Motion
    min_contour_area: int = MIN_CONTOUR_AREA
    motion_threshold: float = 0.02  # 2% of frame — filters noise, triggers ONNX on real motion
    # Zones (list of polygon dicts: [{name, points: [[x,y], ...]}, ...])
    zones: list = field(default_factory=list)
    # Retain
    retain_days: int = DEFAULT_RETAIN_DAYS

    @property
    def is_rtsp(self) -> bool:
        return str(self.source).startswith("rtsp://")

    @property
    def source_resolved(self):
        if self.is_rtsp:
            return self.source
        return int(self.source)

    def validate(self):
        assert self.id,    f"Camera missing id"
        assert self.name,  f"Camera '{self.id}' missing name"
        assert self.source is not None, f"Camera '{self.id}' missing source"


# ── Detection Config ──────────────────────────────────────────────────────────

@dataclass
class DetectionConfig:
    model: str = DEFAULT_MODEL
    confidence: float = DEFAULT_CONFIDENCE
    iou: float = DEFAULT_IOU
    device: str = "cpu"             # "cpu", "cuda", "mps", "tpu"
    backend: str = "cpu"            # "cpu", "edgetpu"
    pool_size: int = 2
    target_classes: Optional[list] = None


# ── Recording Config ──────────────────────────────────────────────────────────

@dataclass
class RecordingConfig:
    enabled: bool = True
    output_dir: str = DIR_RECORDINGS
    codec: str = DEFAULT_CODEC
    crf: int = DEFAULT_CRF
    fps: int = DEFAULT_FPS
    pre_capture_s: int = DEFAULT_PRE_CAPTURE_S
    post_capture_s: int = DEFAULT_POST_CAPTURE_S
    max_clip_s: int = DEFAULT_MAX_CLIP_S
    retain_days: int = DEFAULT_RETAIN_DAYS


# ── Snapshot Config ───────────────────────────────────────────────────────────

@dataclass
class SnapshotConfig:
    enabled: bool = True
    output_dir: str = DIR_SNAPSHOTS
    jpeg_quality: int = 90
    retain_days: int = DEFAULT_RETAIN_DAYS


# ── MQTT Config ───────────────────────────────────────────────────────────────

@dataclass
class MQTTConfig:
    enabled: bool = False
    host: str = "localhost"
    port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: str = "raaqib_nvr"
    tls: bool = False


# ── API Config ────────────────────────────────────────────────────────────────

@dataclass
class APIConfig:
    host: str = API_HOST
    port: int = API_PORT
    cors_origins: list = field(default_factory=lambda: ["*"])


# ── Root Config ───────────────────────────────────────────────────────────────

@dataclass
class RaaqibConfig:
    cameras: list[CameraConfig] = field(default_factory=list)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)
    snapshots: SnapshotConfig = field(default_factory=SnapshotConfig)
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    api: APIConfig = field(default_factory=APIConfig)
    database: str = DB_PATH
    log_level: str = "INFO"

    def get_camera(self, camera_id: str) -> Optional[CameraConfig]:
        return next((c for c in self.cameras if c.id == camera_id), None)

    @property
    def enabled_cameras(self) -> list[CameraConfig]:
        return [c for c in self.cameras if c.enabled]


# ── Parser ────────────────────────────────────────────────────────────────────

def load_config(path: str = "config.yaml") -> RaaqibConfig:
    """Load and validate config from YAML file."""
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    with open(cfg_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    config = RaaqibConfig()
    config.log_level = raw.get("log_level", "INFO")
    config.database  = raw.get("database", DB_PATH)

    # Cameras
    for cam_raw in raw.get("cameras", []):
        cam = CameraConfig(
            id=cam_raw["id"],
            name=cam_raw["name"],
            source=str(cam_raw["source"]),
            enabled=cam_raw.get("enabled", True),
            fps_target=cam_raw.get("fps_target", DEFAULT_FPS),
            width=cam_raw.get("width", DEFAULT_WIDTH),
            height=cam_raw.get("height", DEFAULT_HEIGHT),
            min_contour_area=cam_raw.get("min_contour_area", MIN_CONTOUR_AREA),
            motion_threshold=cam_raw.get("motion_threshold", 0.5),
            zones=cam_raw.get("zones", []),
            retain_days=cam_raw.get("retain_days", DEFAULT_RETAIN_DAYS),
        )
        cam.validate()
        config.cameras.append(cam)

    # Detection
    det = raw.get("detection", {})
    config.detection = DetectionConfig(
        model=det.get("model", DEFAULT_MODEL),
        confidence=det.get("confidence", DEFAULT_CONFIDENCE),
        iou=det.get("iou", DEFAULT_IOU),
        device=det.get("device", "cpu"),
        backend=det.get("backend", "cpu"),
        pool_size=det.get("pool_size", 2),
        target_classes=det.get("target_classes", None),
    )

    # Recording
    rec = raw.get("recording", {})
    config.recording = RecordingConfig(
        enabled=rec.get("enabled", True),
        output_dir=rec.get("output_dir", DIR_RECORDINGS),
        codec=rec.get("codec", DEFAULT_CODEC),
        crf=rec.get("crf", DEFAULT_CRF),
        fps=rec.get("fps", DEFAULT_FPS),
        pre_capture_s=rec.get("pre_capture_s", DEFAULT_PRE_CAPTURE_S),
        post_capture_s=rec.get("post_capture_s", DEFAULT_POST_CAPTURE_S),
        max_clip_s=rec.get("max_clip_s", DEFAULT_MAX_CLIP_S),
        retain_days=rec.get("retain_days", DEFAULT_RETAIN_DAYS),
    )

    # Snapshots
    snap = raw.get("snapshots", {})
    config.snapshots = SnapshotConfig(
        enabled=snap.get("enabled", True),
        output_dir=snap.get("output_dir", DIR_SNAPSHOTS),
        jpeg_quality=snap.get("jpeg_quality", 90),
        retain_days=snap.get("retain_days", DEFAULT_RETAIN_DAYS),
    )

    # MQTT
    mq = raw.get("mqtt", {})
    config.mqtt = MQTTConfig(
        enabled=mq.get("enabled", False),
        host=mq.get("host", "localhost"),
        port=mq.get("port", 1883),
        username=mq.get("username"),
        password=mq.get("password"),
        client_id=mq.get("client_id", "raaqib_nvr"),
        tls=mq.get("tls", False),
    )

    # API
    api = raw.get("api", {})
    config.api = APIConfig(
        host=api.get("host", API_HOST),
        port=api.get("port", API_PORT),
        cors_origins=api.get("cors_origins", ["*"]),
    )

    logger.info(f"Config loaded: {len(config.cameras)} cameras, "
                f"{len(config.enabled_cameras)} enabled")
    return config
