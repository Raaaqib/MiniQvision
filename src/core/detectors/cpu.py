"""
Raaqib NVR — CPU Detector using ONNX Runtime directly.
Runs yolo11n.onnx (or any YOLOv8/11 ONNX) without PyTorch/Ultralytics.
"""

from __future__ import annotations
import numpy as np
import logging
import threading
from pathlib import Path

from src.core.detectors.base import BaseDetector
from src.core.camera.camera import DetectionResult

logger = logging.getLogger(__name__)

COCO_NAMES = [
    "person","bicycle","car","motorcycle","airplane","bus","train","truck","boat",
    "traffic light","fire hydrant","stop sign","parking meter","bench","bird","cat",
    "dog","horse","sheep","cow","elephant","bear","zebra","giraffe","backpack",
    "umbrella","handbag","tie","suitcase","frisbee","skis","snowboard","sports ball",
    "kite","baseball bat","baseball glove","skateboard","surfboard","tennis racket",
    "bottle","wine glass","cup","fork","knife","spoon","bowl","banana","apple",
    "sandwich","orange","broccoli","carrot","hot dog","pizza","donut","cake","chair",
    "couch","potted plant","bed","dining table","toilet","tv","laptop","mouse",
    "remote","keyboard","cell phone","microwave","oven","toaster","sink",
    "refrigerator","book","clock","vase","scissors","teddy bear","hair drier",
    "toothbrush",
]


def _letterbox(img, new_shape=(640, 640)):
    import cv2
    h, w = img.shape[:2]
    r = min(new_shape[0] / h, new_shape[1] / w)
    new_unpad = (int(round(w * r)), int(round(h * r)))
    dw = (new_shape[1] - new_unpad[0]) / 2
    dh = (new_shape[0] - new_unpad[1]) / 2
    resized = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right  = int(round(dw - 0.1)), int(round(dw + 0.1))
    out = cv2.copyMakeBorder(resized, top, bottom, left, right,
                             cv2.BORDER_CONSTANT, value=(114, 114, 114))
    return out, r, (dw, dh)


def _xywh2xyxy(x):
    y = np.copy(x)
    y[..., 0] = x[..., 0] - x[..., 2] / 2
    y[..., 1] = x[..., 1] - x[..., 3] / 2
    y[..., 2] = x[..., 0] + x[..., 2] / 2
    y[..., 3] = x[..., 1] + x[..., 3] / 2
    return y


def _nms(boxes, scores, iou_thr=0.45):
    x1, y1, x2, y2 = boxes[:,0], boxes[:,1], boxes[:,2], boxes[:,3]
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    keep = []
    while order.size:
        i = order[0]; keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0, xx2-xx1) * np.maximum(0, yy2-yy1)
        iou = inter / (areas[i] + areas[order[1:]] - inter)
        order = order[np.where(iou <= iou_thr)[0] + 1]
    return keep


class CPUDetector(BaseDetector):
    """YOLO ONNX inference on CPU using onnxruntime (no PyTorch needed)."""

    def __init__(self, model_name: str = "yolo11n.onnx", confidence: float = 0.45,
                 iou: float = 0.45, device: str = "cpu", target_classes: list = None):
        super().__init__(confidence, iou, target_classes)
        self.model_name = model_name
        self._session = None
        self._input_name = None
        self._input_shape = (640, 640)
        self._lock = threading.Lock()

    def load(self) -> bool:
        try:
            import onnxruntime as ort

            candidates = [
                Path(self.model_name),
                Path("models") / self.model_name,
                Path("/models") / self.model_name,
                Path("/opt/raaqib") / self.model_name,
                Path("/opt/raaqib/models") / self.model_name,
            ]
            model_path = next((p for p in candidates if p.exists()), None)
            if model_path is None:
                logger.error(f"ONNX model not found: {self.model_name}. Searched: {[str(p) for p in candidates]}")
                return False

            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 4          # parallelism within a single op (e.g. matmul)
            opts.inter_op_num_threads = 1          # YOLO is a sequential graph — no benefit from >1
            opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            with self._lock:
                self._session = ort.InferenceSession(
                    str(model_path), sess_options=opts,
                    providers=["CPUExecutionProvider"],
                )
                self._input_name = self._session.get_inputs()[0].name
                shape = self._session.get_inputs()[0].shape
                if isinstance(shape[2], int):
                    self._input_shape = (shape[2], shape[3])
                self._loaded = True

            logger.info(f"ONNX detector ready: {model_path}")
            return True

        except ImportError:
            logger.error("onnxruntime not installed. Run: pip install onnxruntime")
            return False
        except Exception as e:
            logger.error(f"ONNX model load error: {e}")
            return False

    def detect(self, frame: np.ndarray, camera_id: str) -> list[DetectionResult]:
        if not self._loaded or self._session is None:
            return []
        try:
            orig_h, orig_w = frame.shape[:2]
            img, ratio, (dw, dh) = _letterbox(frame, self._input_shape)
            img = img[..., ::-1].astype(np.float32) / 255.0
            img = np.transpose(img, (2, 0, 1))[None]

            with self._lock:
                outputs = self._session.run(None, {self._input_name: img})

            preds = outputs[0][0].T          # [anchors, 84]
            boxes_xywh  = preds[:, :4]
            class_scores = preds[:, 4:]
            class_ids    = class_scores.argmax(axis=1)
            confidences  = class_scores[np.arange(len(class_ids)), class_ids]

            mask = confidences >= self.confidence
            if self.target_classes:
                mask &= np.isin(class_ids, self.target_classes)

            boxes_xywh  = boxes_xywh[mask]
            confidences = confidences[mask]
            class_ids   = class_ids[mask]

            if len(boxes_xywh) == 0:
                return []

            boxes = _xywh2xyxy(boxes_xywh)
            boxes[:, [0, 2]] = (boxes[:, [0, 2]] - dw) / ratio
            boxes[:, [1, 3]] = (boxes[:, [1, 3]] - dh) / ratio
            boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, orig_w)
            boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, orig_h)

            keep = _nms(boxes, confidences, self.iou)
            results = []
            for idx in keep:
                x1, y1, x2, y2 = boxes[idx]
                cid = int(class_ids[idx])
                label = COCO_NAMES[cid] if cid < len(COCO_NAMES) else str(cid)
                results.append(DetectionResult(
                    camera_id=camera_id,
                    label=label,
                    confidence=float(confidences[idx]),
                    bbox=(int(x1), int(y1), int(x2), int(y2)),
                    class_id=cid,
                ))
            return results

        except Exception as e:
            logger.error(f"Inference error: {e}")
            return []
