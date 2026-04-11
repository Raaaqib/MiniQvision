"""
Raaqib NVR — Abstract Detector Base Class
"""

from __future__ import annotations
from abc import ABC, abstractmethod
import numpy as np
from src.core.camera.camera import DetectionResult


_BBOX_CORNER_LEN = 18
_BBOX_THICKNESS = 2
_BBOX_TEXT_SCALE = 0.6
_BBOX_TEXT_THICKNESS = 2
_BBOX_INSET_RATIO = 0.10
_BBOX_ENABLE_INSET = True


def _inset_bbox(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    frame_w: int,
    frame_h: int,
) -> tuple[int, int, int, int]:
    w = max(0, x2 - x1)
    h = max(0, y2 - y1)
    dx = int(round(w * _BBOX_INSET_RATIO))
    dy = int(round(h * _BBOX_INSET_RATIO))

    nx1 = max(0, min(frame_w - 1, x1 + dx))
    ny1 = max(0, min(frame_h - 1, y1 + dy))
    nx2 = max(0, min(frame_w - 1, x2 - dx))
    ny2 = max(0, min(frame_h - 1, y2 - dy))

    if nx2 <= nx1 or ny2 <= ny1:
        return x1, y1, x2, y2
    return nx1, ny1, nx2, ny2


def _draw_corner_brackets(cv, out, x1: int, y1: int, x2: int, y2: int, color):
    w = x2 - x1
    h = y2 - y1
    if w <= 0 or h <= 0:
        return

    corner = max(1, min(_BBOX_CORNER_LEN, w, h))

    # Top-left
    cv.line(out, (x1, y1), (x1 + corner, y1), color, _BBOX_THICKNESS)
    cv.line(out, (x1, y1), (x1, y1 + corner), color, _BBOX_THICKNESS)
    # Top-right
    cv.line(out, (x2, y1), (x2 - corner, y1), color, _BBOX_THICKNESS)
    cv.line(out, (x2, y1), (x2, y1 + corner), color, _BBOX_THICKNESS)
    # Bottom-left
    cv.line(out, (x1, y2), (x1 + corner, y2), color, _BBOX_THICKNESS)
    cv.line(out, (x1, y2), (x1, y2 - corner), color, _BBOX_THICKNESS)
    # Bottom-right
    cv.line(out, (x2, y2), (x2 - corner, y2), color, _BBOX_THICKNESS)
    cv.line(out, (x2, y2), (x2, y2 - corner), color, _BBOX_THICKNESS)


def _draw_compact_label(
    cv,
    out,
    text: str,
    x_anchor: int,
    y_anchor: int,
    color,
    frame_w: int,
    frame_h: int,
):
    (tw, th), baseline = cv.getTextSize(
        text,
        cv.FONT_HERSHEY_SIMPLEX,
        _BBOX_TEXT_SCALE,
        _BBOX_TEXT_THICKNESS,
    )
    label_w = max(1, tw)
    label_h = max(1, th + baseline)

    lx1 = max(0, min(x_anchor, frame_w - label_w))
    ly1 = max(0, y_anchor - label_h - 2)
    lx2 = min(frame_w - 1, lx1 + label_w - 1)
    ly2 = min(frame_h - 1, ly1 + label_h - 1)

    cv.rectangle(out, (lx1, ly1), (lx2, ly2), color, -1)
    cv.putText(
        out,
        text,
        (lx1, ly2 - baseline),
        cv.FONT_HERSHEY_SIMPLEX,
        _BBOX_TEXT_SCALE,
        (0, 0, 0),
        _BBOX_TEXT_THICKNESS,
        cv.LINE_AA,
    )


class BaseDetector(ABC):
    """Abstract interface for all detector backends."""

    def __init__(self, confidence: float = 0.45, iou: float = 0.45,
                 target_classes: list = None):
        self.confidence = confidence
        self.iou = iou
        self.target_classes = target_classes
        self._loaded = False

    @abstractmethod
    def load(self) -> bool:
        """Load model. Returns True on success."""
        ...

    @abstractmethod
    def detect(self, frame: np.ndarray, camera_id: str) -> list[DetectionResult]:
        """Run inference. Returns list of DetectionResult."""
        ...

    @property
    def loaded(self) -> bool:
        return self._loaded

    def draw(self, frame: np.ndarray, detections: list[DetectionResult]) -> np.ndarray:
        """Draw bounding boxes on frame. Can be overridden."""
        import cv2
        out = frame.copy()
        frame_h, frame_w = out.shape[:2]
        palette = {
            "person": (255, 80, 0),
            "car": (0, 200, 255),
            "truck": (0, 160, 220),
            "dog": (0, 255, 120),
            "cat": (255, 0, 200),
            "bicycle": (180, 255, 0),
        }
        for det in detections:
            x1, y1, x2, y2 = [int(v) for v in det.bbox]
            x1 = max(0, min(frame_w - 1, x1))
            y1 = max(0, min(frame_h - 1, y1))
            x2 = max(0, min(frame_w - 1, x2))
            y2 = max(0, min(frame_h - 1, y2))
            if x2 <= x1 or y2 <= y1:
                continue

            if _BBOX_ENABLE_INSET:
                x1, y1, x2, y2 = _inset_bbox(x1, y1, x2, y2, frame_w, frame_h)

            color = palette.get(det.label, (0, 255, 80))
            _draw_corner_brackets(cv2, out, x1, y1, x2, y2, color)
            txt = f"{det.label} {det.confidence:.0%}"
            _draw_compact_label(cv2, out, txt, x1, y1, color, frame_w, frame_h)
        return out
