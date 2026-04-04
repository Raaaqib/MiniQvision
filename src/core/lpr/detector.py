"""
LPR Detector — runs a dedicated YOLO ONNX model to locate license plate
bounding boxes inside a vehicle crop (or full frame).

The model is separate from the main YOLO object detector so it can be
swapped independently (e.g. yolo_lp_nano.onnx → yolo_lp_medium.onnx).

Expected model output format: standard YOLO detection head
  [batch, num_boxes, 5+num_classes]  or  [batch, 5+num_classes, num_boxes]
  box format: cx, cy, w, h, conf  (normalised 0-1)
"""

from __future__ import annotations
import logging
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
import cv2

logger = logging.getLogger(__name__)


@dataclass
class PlateDetection:
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)

    def crop(self, frame: np.ndarray) -> np.ndarray:
        return frame[self.y1:self.y2, self.x1:self.x2]

    def area(self) -> int:
        return max(0, self.x2 - self.x1) * max(0, self.y2 - self.y1)


class LicensePlateDetector:
    """Thin ONNX wrapper around a YOLO license-plate detection model."""

    INPUT_SIZE = (640, 640)

    def __init__(self, model_path: str, confidence: float = 0.50, iou: float = 0.45):
        self.confidence = confidence
        self.iou = iou
        self._session = None
        self._model_path = model_path
        self._load(model_path)

    # ------------------------------------------------------------------
    def _load(self, path: str):
        try:
            import onnxruntime as ort
            providers = ["CPUExecutionProvider"]
            self._session = ort.InferenceSession(path, providers=providers)
            self._input_name = self._session.get_inputs()[0].name
            logger.info(f"[LPR] Plate detector loaded: {path}")
        except Exception as e:
            logger.error(f"[LPR] Failed to load plate detector model '{path}': {e}")
            self._session = None

    # ------------------------------------------------------------------
    def detect(self, frame: np.ndarray) -> List[PlateDetection]:
        """Run inference on a BGR frame. Returns plate detections in pixel coords."""
        if self._session is None:
            return []

        h, w = frame.shape[:2]
        blob, scale_x, scale_y, pad_x, pad_y = self._preprocess(frame)

        try:
            raw = self._session.run(None, {self._input_name: blob})[0]
        except Exception as e:
            logger.warning(f"[LPR] Plate detection inference error: {e}")
            return []

        return self._postprocess(raw, scale_x, scale_y, pad_x, pad_y, w, h)

    # ------------------------------------------------------------------
    def _preprocess(
        self, frame: np.ndarray
    ) -> Tuple[np.ndarray, float, float, int, int]:
        """Letterbox resize → normalise → NCHW float32."""
        target_w, target_h = self.INPUT_SIZE
        h, w = frame.shape[:2]
        scale = min(target_w / w, target_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        pad_x = (target_w - new_w) // 2
        pad_y = (target_h - new_h) // 2
        canvas = np.full((target_h, target_w, 3), 114, dtype=np.uint8)
        canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized

        blob = canvas.astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))[np.newaxis]  # NCHW
        return blob, scale, scale, pad_x, pad_y

    # ------------------------------------------------------------------
    def _postprocess(
        self,
        raw: np.ndarray,
        scale_x: float,
        scale_y: float,
        pad_x: int,
        pad_y: int,
        orig_w: int,
        orig_h: int,
    ) -> List[PlateDetection]:
        # Support both [1, 5+cls, N] and [1, N, 5+cls] layouts
        out = raw[0]
        if out.shape[0] < out.shape[1]:          # [5+cls, N] → [N, 5+cls]
            out = out.T

        boxes, scores = [], []
        for row in out:
            conf = float(row[4])
            if conf < self.confidence:
                continue
            cx, cy, bw, bh = row[:4]
            x1 = int((cx - bw / 2 - pad_x) / scale_x)
            y1 = int((cy - bh / 2 - pad_y) / scale_y)
            x2 = int((cx + bw / 2 - pad_x) / scale_x)
            y2 = int((cy + bh / 2 - pad_y) / scale_y)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(orig_w, x2), min(orig_h, y2)
            if x2 <= x1 or y2 <= y1:
                continue
            boxes.append([x1, y1, x2 - x1, y2 - y1])
            scores.append(conf)

        if not boxes:
            return []

        indices = cv2.dnn.NMSBoxes(boxes, scores, self.confidence, self.iou)
        results = []
        for i in (indices.flatten() if len(indices) else []):
            x, y, bw, bh = boxes[i]
            results.append(PlateDetection(x, y, x + bw, y + bh, scores[i]))

        results.sort(key=lambda d: d.confidence, reverse=True)
        return results
