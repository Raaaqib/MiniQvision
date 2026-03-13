"""
Raaqib NVR — Abstract Detector Base Class
"""

from __future__ import annotations
from abc import ABC, abstractmethod
import numpy as np
from src.core.camera.camera import DetectionResult


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
        palette = {
            "person": (255, 80, 0),
            "car": (0, 200, 255),
            "truck": (0, 160, 220),
            "dog": (0, 255, 120),
            "cat": (255, 0, 200),
            "bicycle": (180, 255, 0),
        }
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = palette.get(det.label, (0, 255, 80))
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
            txt = f"{det.label} {det.confidence:.0%}"
            (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(out, (x1, y1 - th - 8), (x1 + tw + 6, y1), color, -1)
            cv2.putText(out, txt, (x1 + 3, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        return out
