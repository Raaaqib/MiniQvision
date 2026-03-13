"""
Raaqib NVR — Edge TPU Detector (Google Coral)
Requires: pycoral, tflite-runtime
Install: https://coral.ai/docs/accelerator/get-started/
"""

from __future__ import annotations
import numpy as np
import logging
import cv2

from detectors.base import BaseDetector
from camera.camera import DetectionResult

logger = logging.getLogger(__name__)


class EdgeTPUDetector(BaseDetector):
    """
    Object detector using Google Coral Edge TPU.
    Model must be a .tflite file compiled for the Edge TPU.
    Example model: ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite
    """

    def __init__(self, model_path: str, label_path: str,
                 confidence: float = 0.45, target_classes: list = None):
        super().__init__(confidence=confidence, target_classes=target_classes)
        self.model_path = model_path
        self.label_path = label_path
        self._interpreter = None
        self._labels = {}
        self._input_details = None
        self._output_details = None
        self._input_size = (300, 300)  # default SSD input

    def load(self) -> bool:
        try:
            from pycoral.utils.edgetpu import make_interpreter
            from pycoral.adapters import common

            logger.info(f"Loading Edge TPU model: {self.model_path}")
            self._interpreter = make_interpreter(self.model_path)
            self._interpreter.allocate_tensors()

            self._input_details = self._interpreter.get_input_details()
            self._output_details = self._interpreter.get_output_details()

            # Input size
            shape = self._input_details[0]["shape"]
            self._input_size = (shape[2], shape[1])  # (width, height)

            # Load labels
            self._labels = self._load_labels(self.label_path)
            self._loaded = True
            logger.info("Edge TPU detector ready")
            return True

        except ImportError:
            logger.error("pycoral not installed. See https://coral.ai/docs/accelerator/get-started/")
            return False
        except Exception as e:
            logger.error(f"Edge TPU load error: {e}")
            return False

    def _load_labels(self, path: str) -> dict:
        labels = {}
        try:
            with open(path) as f:
                for i, line in enumerate(f):
                    labels[i] = line.strip()
        except Exception as e:
            logger.warning(f"Could not load labels: {e}")
        return labels

    def detect(self, frame: np.ndarray, camera_id: str) -> list[DetectionResult]:
        if not self._loaded or self._interpreter is None:
            return []

        try:
            from pycoral.adapters import detect as coral_detect
            from pycoral.adapters import common

            # Resize to model input
            resized = cv2.resize(frame, self._input_size)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

            common.set_input(self._interpreter, rgb)
            self._interpreter.invoke()

            h, w = frame.shape[:2]
            results = []

            objs = coral_detect.get_objects(self._interpreter, self.confidence)
            for obj in objs:
                if self.target_classes and obj.id not in self.target_classes:
                    continue
                label = self._labels.get(obj.id, str(obj.id))
                # Scale bbox back to original frame size
                bbox = obj.bbox
                x1 = int(bbox.xmin * w / self._input_size[0])
                y1 = int(bbox.ymin * h / self._input_size[1])
                x2 = int(bbox.xmax * w / self._input_size[0])
                y2 = int(bbox.ymax * h / self._input_size[1])
                results.append(DetectionResult(
                    label=label,
                    confidence=float(obj.score),
                    bbox=(x1, y1, x2, y2),
                    class_id=obj.id,
                    camera_id=camera_id,
                ))
            return results

        except Exception as e:
            logger.error(f"Edge TPU inference error: {e}")
            return []
