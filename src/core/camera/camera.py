"""
Raaqib NVR — Camera Object Definition
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class CameraState:
    """Runtime state of a camera — updated by capture process."""
    camera_id: str
    connected: bool = False
    last_frame_time: float = 0.0
    fps: float = 0.0
    motion_detected: bool = False
    motion_score: float = 0.0
    recording: bool = False
    error: Optional[str] = None
    frame_count: int = 0
    detection_count: int = 0

    @property
    def online(self) -> bool:
        if not self.connected:
            return False
        # Consider offline if no frame for 5s
        return (time.time() - self.last_frame_time) < 5.0

    def to_dict(self) -> dict:
        return {
            "camera_id": self.camera_id,
            "connected": self.connected,
            "online": self.online,
            "fps": round(self.fps, 1),
            "motion": self.motion_detected,
            "recording": self.recording,
            "error": self.error,
            "frame_count": self.frame_count,
            "detection_count": self.detection_count,
        }


@dataclass
class FramePacket:
    """
    Unit of data flowing through the pipeline.
    Passed between processes via queues.

    Dual-stream support:
      frame        — full-resolution frame, used for recording & JPEG preview
      detect_frame — optional low-resolution copy, used for motion + ONNX inference
                     If None, pipeline stages fall back to using frame.
    """
    camera_id: str
    frame: np.ndarray
    timestamp: float = field(default_factory=time.time)
    motion_detected: bool = False
    motion_boxes: list = field(default_factory=list)
    detections: list = field(default_factory=list)
    tracked_objects: list = field(default_factory=list)
    detect_frame: Optional[np.ndarray] = None  # low-res copy for motion+AI

    @property
    def has_motion(self) -> bool:
        return self.motion_detected

    @property
    def has_detections(self) -> bool:
        return len(self.detections) > 0


@dataclass
class DetectionResult:
    """Single object detection result."""
    label: str
    confidence: float
    bbox: tuple             # (x1, y1, x2, y2)
    class_id: int
    camera_id: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        x1, y1, x2, y2 = self.bbox
        return {
            "label": self.label,
            "confidence": round(self.confidence, 3),
            "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            "camera_id": self.camera_id,
            "timestamp": self.timestamp,
        }


@dataclass
class TrackedObject:
    """Object with persistent ID across frames."""
    track_id: int
    label: str
    confidence: float
    bbox: tuple
    camera_id: str
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    disappeared: int = 0
    centroid: tuple = (0, 0)

    def update(self, bbox: tuple, confidence: float):
        self.bbox = bbox
        self.confidence = confidence
        self.last_seen = time.time()
        self.disappeared = 0
        x1, y1, x2, y2 = bbox
        self.centroid = ((x1 + x2) // 2, (y1 + y2) // 2)

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "label": self.label,
            "confidence": round(self.confidence, 3),
            "bbox": self.bbox,
            "camera_id": self.camera_id,
            "duration": round(self.last_seen - self.first_seen, 1),
        }
