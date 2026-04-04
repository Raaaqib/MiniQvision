"""
LPR Pipeline — ties together zone gating, plate detection, OCR, whitelist
check and output (DB + MQTT + snapshot + log) for a single camera.

Usage (called from the camera processing loop after YOLO object detection):

    pipeline.process(frame, detections, camera_id)

`detections` is the list of YOLO object detections already produced by the
main detector.  Only vehicle classes (car, truck, bus, motorcycle) are
forwarded to LPR; everything else is skipped.
"""

from __future__ import annotations
import logging
import time
import cv2
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Callable, TYPE_CHECKING

from .zone import LPRZone, point_in_any_zone
from .detector import LicensePlateDetector, PlateDetection
from .recognizer import PlateRecognizer
from .whitelist import PlateWhitelist

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# COCO class IDs that count as vehicles (YOLO default mapping)
VEHICLE_CLASS_IDS = {2, 3, 5, 7}   # car, motorcycle, bus, truck
VEHICLE_CLASS_NAMES = {"car", "truck", "bus", "motorcycle", "vehicle"}


# ──────────────────────────────────────────────────────────────────────────────

class LPRResult:
    """Carries all data produced for one recognised plate."""

    __slots__ = (
        "camera_id", "zone_id", "plate", "confidence",
        "known", "alert", "bbox_vehicle", "bbox_plate",
        "snapshot_path", "timestamp",
    )

    def __init__(
        self,
        camera_id: str,
        zone_id: str,
        plate: str,
        confidence: float,
        known: bool,
        alert: bool,
        bbox_vehicle,
        bbox_plate,
        snapshot_path: Optional[str],
        timestamp: datetime,
    ):
        self.camera_id = camera_id
        self.zone_id = zone_id
        self.plate = plate
        self.confidence = confidence
        self.known = known
        self.alert = alert
        self.bbox_vehicle = bbox_vehicle
        self.bbox_plate = bbox_plate
        self.snapshot_path = snapshot_path
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            "camera_id": self.camera_id,
            "zone_id": self.zone_id,
            "plate": self.plate,
            "confidence": round(self.confidence, 3),
            "known": self.known,
            "alert": self.alert,
            "bbox_vehicle": self.bbox_vehicle,
            "bbox_plate": self.bbox_plate,
            "snapshot_path": self.snapshot_path,
            "timestamp": self.timestamp.isoformat(),
        }


# ──────────────────────────────────────────────────────────────────────────────

class LPRPipeline:
    """
    Per-camera LPR pipeline.

    Parameters
    ----------
    camera_id : str
    zones : list[LPRZone]
        Active LPR zones for this camera.
    plate_detector : LicensePlateDetector
    recognizer : PlateRecognizer
    whitelist : PlateWhitelist
    snapshot_dir : str | Path
    on_result : Callable[[LPRResult], None] | None
        Callback invoked for every accepted LPR result (DB, MQTT, etc.)
    cooldown_s : float
        Minimum seconds between two events for the *same* plate.
    """

    def __init__(
        self,
        camera_id: str,
        zones: List[LPRZone],
        plate_detector: LicensePlateDetector,
        recognizer: PlateRecognizer,
        whitelist: PlateWhitelist,
        snapshot_dir: str | Path = "snapshots/lpr",
        on_result: Optional[Callable[[LPRResult], None]] = None,
        cooldown_s: float = 10.0,
    ):
        self.camera_id = camera_id
        self.zones = zones
        self.plate_detector = plate_detector
        self.recognizer = recognizer
        self.whitelist = whitelist
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.on_result = on_result
        self.cooldown_s = cooldown_s
        self._last_seen: dict[str, float] = {}   # plate → last event ts

    # ------------------------------------------------------------------
    def process(self, frame: np.ndarray, yolo_detections: list) -> List[LPRResult]:
        """
        Main entry point called from the camera loop.

        Parameters
        ----------
        frame : np.ndarray  BGR frame at full resolution
        yolo_detections : list
            Each item must expose .class_id / .class_name and .bbox (x1,y1,x2,y2).
            Compatible with Raaqib's existing detection objects.
        """
        results: List[LPRResult] = []

        if not self.zones:
            return results

        for det in yolo_detections:
            if not self._is_vehicle(det):
                continue

            x1, y1, x2, y2 = self._get_bbox(det)
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

            zone = point_in_any_zone(self.zones, cx, cy)
            if zone is None:
                continue

            # Crop vehicle region with a small margin
            crop = self._safe_crop(frame, x1, y1, x2, y2, margin=10)
            if crop is None:
                continue

            plate_dets = self.plate_detector.detect(crop)
            if not plate_dets:
                continue

            # Use highest-confidence plate detection
            best: PlateDetection = plate_dets[0]
            plate_crop = best.crop(crop)

            text, conf = self.recognizer.read(plate_crop)
            if text is None:
                continue

            # Cooldown — avoid duplicate events for the same plate
            now = time.time()
            if now - self._last_seen.get(text, 0) < self.cooldown_s:
                logger.debug(f"[LPR] Cooldown active for '{text}', skipping")
                continue
            self._last_seen[text] = now

            status = self.whitelist.check(text)
            snap_path = self._save_snapshot(frame, x1, y1, x2, y2, best, crop, text, status["alert"])

            result = LPRResult(
                camera_id=self.camera_id,
                zone_id=zone.id,
                plate=text,
                confidence=conf,
                known=status["known"],
                alert=status["alert"],
                bbox_vehicle=(x1, y1, x2, y2),
                bbox_plate=(best.x1, best.y1, best.x2, best.y2),
                snapshot_path=str(snap_path) if snap_path else None,
                timestamp=datetime.now(timezone.utc),
            )

            logger.info(
                f"[LPR] cam={self.camera_id} zone={zone.id} "
                f"plate={text!r} conf={conf:.2f} "
                f"known={status['known']} alert={status['alert']}"
            )

            if self.on_result:
                try:
                    self.on_result(result)
                except Exception as e:
                    logger.error(f"[LPR] on_result callback error: {e}")

            results.append(result)

        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_vehicle(det) -> bool:
        # Support both class_id and class_name attributes
        if hasattr(det, "class_id") and det.class_id in VEHICLE_CLASS_IDS:
            return True
        if hasattr(det, "class_name") and str(det.class_name).lower() in VEHICLE_CLASS_NAMES:
            return True
        if hasattr(det, "label") and str(det.label).lower() in VEHICLE_CLASS_NAMES:
            return True
        return False

    @staticmethod
    def _get_bbox(det):
        if hasattr(det, "bbox"):
            return det.bbox
        if hasattr(det, "x1"):
            return det.x1, det.y1, det.x2, det.y2
        if hasattr(det, "box"):
            return det.box
        raise AttributeError(f"Cannot extract bbox from {type(det)}")

    @staticmethod
    def _safe_crop(
        frame: np.ndarray,
        x1: int, y1: int, x2: int, y2: int,
        margin: int = 0,
    ) -> Optional[np.ndarray]:
        h, w = frame.shape[:2]
        x1c = max(0, x1 - margin)
        y1c = max(0, y1 - margin)
        x2c = min(w, x2 + margin)
        y2c = min(h, y2 + margin)
        if x2c <= x1c or y2c <= y1c:
            return None
        return frame[y1c:y2c, x1c:x2c].copy()

    def _save_snapshot(
        self,
        frame: np.ndarray,
        vx1: int, vy1: int, vx2: int, vy2: int,
        plate_det: PlateDetection,
        vehicle_crop: np.ndarray,
        plate_text: str,
        alert: bool,
    ) -> Optional[Path]:
        """Save annotated snapshot. Returns path or None on failure."""
        try:
            annotated = frame.copy()

            # Draw zone polygons
            for zone in self.zones:
                zone.draw(annotated)

            # Vehicle bounding box
            v_color = (0, 0, 255) if alert else (0, 200, 80)
            cv2.rectangle(annotated, (vx1, vy1), (vx2, vy2), v_color, 2)

            # Plate bbox — offset into vehicle crop coords
            px1 = vx1 + plate_det.x1
            py1 = vy1 + plate_det.y1
            px2 = vx1 + plate_det.x2
            py2 = vy1 + plate_det.y2
            cv2.rectangle(annotated, (px1, py1), (px2, py2), (255, 200, 0), 2)

            # Plate text label
            label = f"{'⚠ ' if alert else ''}{plate_text}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            bg_x2 = min(frame.shape[1], px1 + tw + 6)
            cv2.rectangle(annotated, (px1, py1 - th - 10), (bg_x2, py1), v_color, -1)
            cv2.putText(
                annotated, label,
                (px1 + 3, py1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA,
            )

            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            safe_plate = plate_text.replace("/", "_").replace("\\", "_")
            fname = self.snapshot_dir / f"{self.camera_id}_{safe_plate}_{ts}.jpg"
            cv2.imwrite(str(fname), annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
            return fname

        except Exception as e:
            logger.warning(f"[LPR] Snapshot save failed: {e}")
            return None
