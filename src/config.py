"""
Raaqib NVR — Configuration Parsing & Validation
"""

from __future__ import annotations
import yaml
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.core.const import (
    DEFAULT_CONFIDENCE, DEFAULT_IOU, DEFAULT_MODEL,
    DEFAULT_PRE_CAPTURE_S, DEFAULT_POST_CAPTURE_S, DEFAULT_MAX_CLIP_S,
    DEFAULT_FPS, DEFAULT_CRF, DEFAULT_CODEC, DEFAULT_RETAIN_DAYS,
    API_HOST, API_PORT, DB_PATH, DIR_RECORDINGS, DIR_SNAPSHOTS,
    DEFAULT_WIDTH, DEFAULT_HEIGHT, MIN_CONTOUR_AREA
)

logger = logging.getLogger(__name__)


@dataclass
class ZonePoint:
    x: int
    y: int


@dataclass
class Zone:
    id: str
    name: str
    type: str
    polygon: list[ZonePoint]
    active: bool = True
    classes: list[str] = field(default_factory=list)


@dataclass
class ModelConfig:
    path: str
    device: str = "cpu"
    confidence_threshold: float = 0.45
    pool_size: int = 2
    classes: list[str] = field(default_factory=list)


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
    model: str = "default"
    zones: list[Zone] = field(default_factory=list)
    # Retain
    retain_days: int = DEFAULT_RETAIN_DAYS
    # ── Dual-stream (detect vs record) ───────────────────────────────────────
    # detect_width/height: resolution used for motion detection + ONNX inference
    #   Set lower than width/height to trade accuracy for CPU speed.
    #   0 = use the same resolution as the record stream (no downscale).
    detect_width: int = 0
    detect_height: int = 0
    detect_fps: int = 0             # 0 = same as fps_target
    # detect_url: optional RTSP sub-stream URL (e.g. a camera's low-res stream).
    #   When set, a second FFmpeg reader opens this URL for motion+detection.
    #   When empty, frames are downscaled in software from the main stream.
    detect_url: str = ""

    @property
    def is_rtsp(self) -> bool:
        return str(self.source).startswith("rtsp://")

    @property
    def source_resolved(self):
        if self.is_rtsp:
            return self.source
        return int(self.source)

    @property
    def effective_detect_width(self) -> int:
        """Actual width used for detect stream (falls back to record width)."""
        return self.detect_width if self.detect_width > 0 else self.width

    @property
    def effective_detect_height(self) -> int:
        """Actual height used for detect stream (falls back to record height)."""
        return self.detect_height if self.detect_height > 0 else self.height

    @property
    def effective_detect_fps(self) -> int:
        """Actual FPS used for detect stream (falls back to fps_target)."""
        return self.detect_fps if self.detect_fps > 0 else self.fps_target

    @property
    def dual_stream_enabled(self) -> bool:
        """True if detect resolution differs from record resolution."""
        return self.effective_detect_width != self.width or self.effective_detect_height != self.height

    def validate(self):
        assert self.id, "Camera missing id"
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
class AppConfig:
    cameras: list[CameraConfig] = field(default_factory=list)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    models: dict[str, ModelConfig] = field(default_factory=dict)
    recording: RecordingConfig = field(default_factory=RecordingConfig)
    snapshots: SnapshotConfig = field(default_factory=SnapshotConfig)
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    api: APIConfig = field(default_factory=APIConfig)
    database: str = DB_PATH
    log_level: str = "INFO"
    lpr: dict = field(default_factory=dict)  # Raw LPR config dict for LPRManager

    def get_camera(self, camera_id: str) -> Optional[CameraConfig]:
        return next((c for c in self.cameras if c.id == camera_id), None)

    @property
    def enabled_cameras(self) -> list[CameraConfig]:
        return [c for c in self.cameras if c.enabled]


RaaqibConfig = AppConfig


def _parse_zones(raw_zones: list) -> list[Zone]:
    zones: list[Zone] = []
    for z in raw_zones or []:
        zone_id = z.get("id")
        if not zone_id:
            logger.warning("Zone missing id, skipping")
            continue

        zone_type = z.get("type", "trigger")
        if zone_type not in ("trigger", "exclude"):
            logger.warning("Zone '%s' has unknown type '%s', skipping", zone_id, zone_type)
            continue

        raw_polygon = z.get("polygon", [])
        if len(raw_polygon) < 3:
            logger.warning("Zone '%s' has fewer than 3 polygon points, skipping", zone_id)
            continue

        polygon: list[ZonePoint] = []
        polygon_valid = True
        for p in raw_polygon:
            if not isinstance(p, (list, tuple)) or len(p) < 2:
                polygon_valid = False
                break
            try:
                polygon.append(ZonePoint(x=int(p[0]), y=int(p[1])))
            except (TypeError, ValueError):
                polygon_valid = False
                break

        if not polygon_valid:
            logger.warning("Zone '%s' has invalid polygon point(s), skipping", zone_id)
            continue

        classes = z.get("classes", [])
        if classes is None:
            classes = []
        if not isinstance(classes, list):
            classes = [str(classes)]

        zones.append(
            Zone(
                id=zone_id,
                name=z.get("name", zone_id),
                type=zone_type,
                polygon=polygon,
                active=bool(z.get("active", True)),
                classes=[str(c) for c in classes],
            )
        )

    return zones


# ── Parser ────────────────────────────────────────────────────────────────────

def load_config(path: str | Path | None = None) -> AppConfig:
    """Load and validate config from YAML file."""
    if path is None:
        # Default: config/config.yaml relative to this file
        cfg_path = Path(__file__).parent / "config" / "config.yaml"
    else:
        cfg_path = Path(path)

    if not cfg_path.exists():
        raise FileNotFoundError(f"Config not found: {cfg_path}")

    with open(cfg_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    config = AppConfig()
    config.log_level = raw.get("log_level", "INFO")
    config.database  = raw.get("database", DB_PATH)

    # Detection (legacy, kept for backward compatibility)
    det = raw.get("detection", {})
    config.detection = DetectionConfig(
        model=det.get("model", det.get("model_path", DEFAULT_MODEL)),
        confidence=det.get("confidence", det.get("confidence_threshold", DEFAULT_CONFIDENCE)),
        iou=det.get("iou", DEFAULT_IOU),
        device=det.get("device", "cpu"),
        backend=det.get("backend", "cpu"),
        pool_size=det.get("pool_size", 2),
        target_classes=det.get("target_classes", None),
    )

    # Models (new). If absent, use legacy detection block as default model.
    raw_models = raw.get("models")
    if raw_models is None:
        classes = config.detection.target_classes or []
        config.models = {
            "default": ModelConfig(
                path=config.detection.model,
                device=config.detection.device,
                confidence_threshold=config.detection.confidence,
                pool_size=config.detection.pool_size,
                classes=[str(c) for c in classes],
            )
        }
    else:
        for model_id, model_raw in raw_models.items():
            if not isinstance(model_raw, dict):
                logger.warning("Model '%s' config is not a mapping, skipping", model_id)
                continue

            classes = model_raw.get("classes", [])
            if classes is None:
                classes = []
            if not isinstance(classes, list):
                classes = [str(classes)]

            config.models[str(model_id)] = ModelConfig(
                path=str(model_raw.get("path", model_raw.get("model", config.detection.model))),
                device=str(model_raw.get("device", config.detection.device)),
                confidence_threshold=float(
                    model_raw.get("confidence_threshold", model_raw.get("confidence", config.detection.confidence))
                ),
                pool_size=int(model_raw.get("pool_size", config.detection.pool_size)),
                classes=[str(c) for c in classes],
            )

        if not config.models:
            config.models = {
                "default": ModelConfig(
                    path=config.detection.model,
                    device=config.detection.device,
                    confidence_threshold=config.detection.confidence,
                    pool_size=config.detection.pool_size,
                    classes=[str(c) for c in (config.detection.target_classes or [])],
                )
            }

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
            motion_threshold=cam_raw.get("motion_threshold", 0.02),
            model=cam_raw.get("model", "default"),
            zones=_parse_zones(cam_raw.get("zones", [])),
            retain_days=cam_raw.get("retain_days", DEFAULT_RETAIN_DAYS),
            detect_width=cam_raw.get("detect_width", 0),
            detect_height=cam_raw.get("detect_height", 0),
            detect_fps=cam_raw.get("detect_fps", 0),
            detect_url=cam_raw.get("detect_url", ""),
        )
        cam.validate()
        config.cameras.append(cam)

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

    # LPR (store raw dict for LPRManager)
    config.lpr = raw.get("lpr", {})

    logger.info(
        "Config loaded: %s cameras (%s enabled), %s model(s)",
        len(config.cameras),
        len(config.enabled_cameras),
        len(config.models),
    )
    return config


def _is_polygon_degenerate(polygon: list[ZonePoint]) -> bool:
    """
    Check if a polygon is degenerate (all points collinear).
    Uses cross-product to detect collinearity.
    """
    if len(polygon) < 3:
        return True

    # Check if all points are collinear using cross product
    # If cross product of all consecutive edge pairs is zero, points are collinear
    p0 = polygon[0]
    for i in range(1, len(polygon) - 1):
        p1 = polygon[i]
        p2 = polygon[i + 1]
        # Cross product: (p1 - p0) × (p2 - p0)
        cross = (p1.x - p0.x) * (p2.y - p0.y) - (p1.y - p0.y) * (p2.x - p0.x)
        if cross != 0:
            return False  # Non-zero cross product means non-collinear
    return True  # All cross products were zero — degenerate polygon


def validate_config(config: AppConfig, config_path: Path | None = None) -> list[str]:
    errors: list[str] = []

    # Resolve model paths relative to config file if provided
    base_dir = config_path.parent if config_path else Path.cwd()

    # Model assignment validation
    for cam in config.cameras:
        if cam.model not in config.models:
            errors.append(
                f"Camera '{cam.id}' references model '{cam.model}' "
                f"which is not defined in models: {list(config.models.keys())}"
            )

    # Model config validation
    for model_id, model_cfg in config.models.items():
        model_path = Path(model_cfg.path)
        # Try absolute path first, then relative to config directory
        if not model_path.is_absolute():
            model_path = base_dir / model_path
        if not model_path.exists():
            errors.append(f"Model '{model_id}' path not found: {model_cfg.path} (resolved: {model_path})")
        if model_cfg.device not in ("cpu", "cuda", "mps", "tpu"):
            errors.append(f"Model '{model_id}' has unknown device: {model_cfg.device}")
        if not (0.0 < model_cfg.confidence_threshold < 1.0):
            errors.append(f"Model '{model_id}' confidence_threshold must be in (0, 1)")
        if model_cfg.pool_size < 1:
            errors.append(f"Model '{model_id}' pool_size must be >= 1")

    # Zone validation
    for cam in config.cameras:
        for zone in cam.zones:
            if zone.type not in ("trigger", "exclude"):
                errors.append(
                    f"Camera '{cam.id}' zone '{zone.id}': "
                    f"type must be 'trigger' or 'exclude', got '{zone.type}'"
                )
            if len(zone.polygon) < 3:
                errors.append(
                    f"Camera '{cam.id}' zone '{zone.id}': polygon must have >=3 points"
                )
            elif _is_polygon_degenerate(zone.polygon):
                errors.append(
                    f"Camera '{cam.id}' zone '{zone.id}': polygon is degenerate (all points collinear)"
                )

    return errors
