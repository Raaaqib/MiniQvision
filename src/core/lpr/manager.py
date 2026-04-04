"""
LPR Manager — top-level factory.

Creates one LPRPipeline per camera and exposes a single
`process(camera_id, frame, yolo_detections)` method for the camera loop.

Instantiate once at application startup:

    lpr_manager = LPRManager(config, db_path, mqtt_client)

Then call from the camera processing loop:

    lpr_manager.process("cam1", frame, detections)
"""

from __future__ import annotations
import logging
from typing import Dict, List, Optional

from .zone import build_zones
from .detector import LicensePlateDetector
from .recognizer import PlateRecognizer
from .whitelist import PlateWhitelist
from .pipeline import LPRPipeline, LPRResult
from .db import LPRDatabase
from .mqtt import LPRMQTTPublisher

logger = logging.getLogger(__name__)


class LPRManager:
    """
    Wires LPR components together and manages per-camera pipelines.

    Config shape expected (subset of config_local.yaml):
    ───────────────────────────────────────────────────
    lpr:
      enabled: true
      model: "models/yolo_lp.onnx"
      confidence: 0.50
      iou: 0.45
      ocr_lang: "en"
      ocr_min_confidence: 0.60
      snapshot_dir: "snapshots/lpr"
      cooldown_s: 10
      whitelist:
        - "ABC123"
        - "XYZ999"
      cameras:
        - camera_id: cam1
          zones:
            - id: entry_zone
              polygon: [[100,200],[400,200],[400,400],[100,400]]
        - camera_id: cam2
          zones:
            - id: exit_zone
              polygon: [[50,100],[300,100],[300,350],[50,350]]
    """

    def __init__(
        self,
        config: dict,
        db_path: str,
        mqtt_client=None,
    ):
        lpr_cfg: dict = config.get("lpr", {})

        if not lpr_cfg.get("enabled", False):
            logger.info("[LPR] Disabled in config")
            self._enabled = False
            return

        self._enabled = True

        # ── Shared components ──────────────────────────────────────────
        self.db = LPRDatabase(db_path)
        self.mqtt = LPRMQTTPublisher(mqtt_client)

        # Whitelist: config plates + persisted DB plates
        config_plates = lpr_cfg.get("whitelist", [])
        db_plates = self.db.load_whitelist()
        all_plates = list(set(config_plates) | set(db_plates))
        self.whitelist = PlateWhitelist(all_plates)

        # Plate detector (shared across all cameras)
        model_path = lpr_cfg.get("model", "models/yolo_lp.onnx")
        confidence = float(lpr_cfg.get("confidence", 0.50))
        iou = float(lpr_cfg.get("iou", 0.45))
        self.plate_detector = LicensePlateDetector(model_path, confidence, iou)

        # OCR recognizer (shared — PaddleOCR is heavy to init)
        ocr_lang = lpr_cfg.get("ocr_lang", "en")
        ocr_min_conf = float(lpr_cfg.get("ocr_min_confidence", 0.60))
        self.recognizer = PlateRecognizer(
            lang=ocr_lang,
            min_confidence=ocr_min_conf,
        )

        # ── Per-camera pipelines ───────────────────────────────────────
        snapshot_dir = lpr_cfg.get("snapshot_dir", "snapshots/lpr")
        cooldown_s = float(lpr_cfg.get("cooldown_s", 10.0))

        self._pipelines: Dict[str, LPRPipeline] = {}
        for cam_cfg in lpr_cfg.get("cameras", []):
            cam_id = cam_cfg.get("camera_id")
            if not cam_id:
                logger.warning("[LPR] Camera entry missing 'camera_id', skipped")
                continue

            zones = build_zones(cam_cfg.get("zones", []))
            if not zones:
                logger.warning(f"[LPR] No zones defined for camera '{cam_id}', skipped")
                continue

            pipeline = LPRPipeline(
                camera_id=cam_id,
                zones=zones,
                plate_detector=self.plate_detector,
                recognizer=self.recognizer,
                whitelist=self.whitelist,
                snapshot_dir=snapshot_dir,
                on_result=self._handle_result,
                cooldown_s=cooldown_s,
            )
            self._pipelines[cam_id] = pipeline
            logger.info(
                f"[LPR] Pipeline ready: camera={cam_id} zones={[z.id for z in zones]}"
            )

        logger.info(
            f"[LPR] Manager started — "
            f"{len(self._pipelines)} camera(s), "
            f"{len(self.whitelist)} whitelisted plate(s)"
        )

    # ------------------------------------------------------------------
    def process(
        self, camera_id: str, frame, yolo_detections: list
    ) -> List[LPRResult]:
        """Call this from the camera processing loop."""
        if not self._enabled:
            return []
        pipeline = self._pipelines.get(camera_id)
        if pipeline is None:
            return []
        return pipeline.process(frame, yolo_detections)

    # ------------------------------------------------------------------
    def _handle_result(self, result: LPRResult):
        """Fires after every accepted LPR result: DB → MQTT → log."""
        # 1. Persist to DB
        try:
            row_id = self.db.insert_event(result)
            logger.debug(f"[LPR] DB event id={row_id} plate={result.plate}")
        except Exception as e:
            logger.error(f"[LPR] DB insert failed: {e}")

        # 2. MQTT publish
        self.mqtt.publish(result)

        # 3. Structured log line (easily grep-able)
        level = logging.WARNING if result.alert else logging.INFO
        logger.log(
            level,
            "[LPR] %s | cam=%s zone=%s conf=%.2f known=%s alert=%s snap=%s",
            result.plate,
            result.camera_id,
            result.zone_id,
            result.confidence,
            result.known,
            result.alert,
            result.snapshot_path or "—",
        )

    # ------------------------------------------------------------------
    # Runtime whitelist management (called from API routes)
    # ------------------------------------------------------------------

    def add_plate(self, plate: str, note: str = "") -> bool:
        if not self._enabled:
            return False
        self.whitelist.add(plate)
        return self.db.add_to_whitelist(plate, note)

    def remove_plate(self, plate: str) -> bool:
        if not self._enabled:
            return False
        self.whitelist.remove(plate)
        return self.db.remove_from_whitelist(plate)

    def get_whitelist(self) -> list:
        if not self._enabled:
            return []
        return self.db.get_whitelist()

    def get_events(self, **kwargs) -> list:
        if not self._enabled:
            return []
        return self.db.get_events(**kwargs)

    @property
    def enabled(self) -> bool:
        return self._enabled
