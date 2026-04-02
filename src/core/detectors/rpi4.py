"""
Raaqib NVR — Raspberry Pi 4 Detector using NCNN
NCNN provides optimized inference on ARM devices with Vulkan GPU acceleration.
Requires: ncnn (pip install ncnn or build from source)
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
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
    "toothbrush",
]


def _letterbox(img: np.ndarray, new_shape: tuple = (640, 640)) -> tuple:
    """Resize image with letterboxing (padding) to maintain aspect ratio."""
    import cv2
    h, w = img.shape[:2]
    r = min(new_shape[0] / h, new_shape[1] / w)
    new_unpad = (int(round(w * r)), int(round(h * r)))
    dw = (new_shape[1] - new_unpad[0]) / 2
    dh = (new_shape[0] - new_unpad[1]) / 2
    resized = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    out = cv2.copyMakeBorder(resized, top, bottom, left, right,
                             cv2.BORDER_CONSTANT, value=(114, 114, 114))
    return out, r, (dw, dh)


def _xywh2xyxy(x: np.ndarray) -> np.ndarray:
    """Convert [x_center, y_center, width, height] to [x1, y1, x2, y2]."""
    y = np.copy(x)
    y[..., 0] = x[..., 0] - x[..., 2] / 2
    y[..., 1] = x[..., 1] - x[..., 3] / 2
    y[..., 2] = x[..., 0] + x[..., 2] / 2
    y[..., 3] = x[..., 1] + x[..., 3] / 2
    return y


def _nms(boxes: np.ndarray, scores: np.ndarray, iou_thr: float = 0.45) -> list:
    """Non-Maximum Suppression."""
    x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    keep = []
    while order.size:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        order = order[np.where(iou <= iou_thr)[0] + 1]
    return keep


class RPi4Detector(BaseDetector):
    """
    YOLO inference on Raspberry Pi 4 using NCNN framework.
    
    NCNN is optimized for ARM/mobile devices and supports:
    - ARM NEON acceleration (SIMD)
    - Vulkan GPU acceleration (RPi4 VideoCore VI)
    - Quantized INT8 models for faster inference
    
    Model requirements:
    - .param file: Network architecture
    - .bin file: Model weights
    
    Convert ONNX to NCNN:
        pip install onnx2ncnn
        onnx2ncnn yolo11n.onnx yolo11n.param yolo11n.bin
    
    Or use ncnn tools:
        ./onnx2ncnn yolo11n.onnx yolo11n.param yolo11n.bin
    """

    def __init__(self, model_name: str = "yolo11n", confidence: float = 0.45,
                 iou: float = 0.45, use_vulkan: bool = False,
                 num_threads: int = 4, target_classes: list = None):
        """
        Initialize RPi4 NCNN detector.
        
        Args:
            model_name: Base name of model (without extension). 
                       Expects {model_name}.param and {model_name}.bin
            confidence: Confidence threshold for detections
            iou: IoU threshold for NMS
            use_vulkan: Enable Vulkan GPU acceleration (if available)
            num_threads: Number of CPU threads for inference
            target_classes: List of class IDs to detect (None = all)
        """
        super().__init__(confidence, iou, target_classes)
        self.model_name = model_name
        self.use_vulkan = use_vulkan
        self.num_threads = num_threads
        self._net = None
        self._input_name = "images"  # Default YOLO input layer name
        self._output_name = "output0"  # Default YOLO output layer name
        self._input_shape = (640, 640)
        self._lock = threading.Lock()

    def load(self) -> bool:
        """Load NCNN model from .param and .bin files."""
        try:
            import ncnn

            # Search for model files
            search_paths = [
                Path("."),
                Path("models"),
                Path("/models"),
                Path("/opt/raaqib"),
                Path("/opt/raaqib/models"),
                Path.home() / ".raaqib" / "models",
            ]

            param_file = None
            bin_file = None

            for base in search_paths:
                param_candidate = base / f"{self.model_name}.param"
                bin_candidate = base / f"{self.model_name}.bin"
                if param_candidate.exists() and bin_candidate.exists():
                    param_file = param_candidate
                    bin_file = bin_candidate
                    break

            if param_file is None or bin_file is None:
                logger.error(
                    f"NCNN model not found: {self.model_name}.param/.bin. "
                    f"Searched: {[str(p) for p in search_paths]}"
                )
                return False

            # Initialize NCNN
            self._net = ncnn.Net()

            # Configure options
            self._net.opt.use_vulkan_compute = self.use_vulkan and ncnn.get_gpu_count() > 0
            self._net.opt.num_threads = self.num_threads
            self._net.opt.use_fp16_packed = True
            self._net.opt.use_fp16_storage = True
            self._net.opt.use_fp16_arithmetic = True
            self._net.opt.lightmode = True

            # Load model
            with self._lock:
                ret_param = self._net.load_param(str(param_file))
                ret_bin = self._net.load_model(str(bin_file))

                if ret_param != 0 or ret_bin != 0:
                    logger.error(f"Failed to load NCNN model: param={ret_param}, bin={ret_bin}")
                    return False

            self._loaded = True
            vulkan_status = "enabled" if self._net.opt.use_vulkan_compute else "disabled"
            logger.info(
                f"NCNN detector ready: {param_file} "
                f"(threads={self.num_threads}, vulkan={vulkan_status})"
            )
            return True

        except ImportError:
            logger.error(
                "ncnn not installed. Install with: pip install ncnn "
                "or build from source: https://github.com/Tencent/ncnn"
            )
            return False
        except Exception as e:
            logger.error(f"NCNN model load error: {e}")
            return False

    def detect(self, frame: np.ndarray, camera_id: str) -> list[DetectionResult]:
        """Run YOLO inference on frame using NCNN."""
        if not self._loaded or self._net is None:
            return []

        try:
            import ncnn

            orig_h, orig_w = frame.shape[:2]

            # Preprocess: letterbox resize
            img, ratio, (dw, dh) = _letterbox(frame, self._input_shape)

            # Convert BGR to RGB and normalize
            img = img[..., ::-1].astype(np.float32) / 255.0

            # Create NCNN Mat from numpy array (HWC format)
            mat_in = ncnn.Mat.from_pixels(
                img.tobytes(),
                ncnn.Mat.PixelType.PIXEL_RGB,
                self._input_shape[1],
                self._input_shape[0]
            )

            # Normalize (YOLO expects 0-1 range, already done above)
            # If model expects different normalization, adjust here:
            # mean_vals = [0.0, 0.0, 0.0]
            # norm_vals = [1/255.0, 1/255.0, 1/255.0]
            # mat_in.substract_mean_normalize(mean_vals, norm_vals)

            # Run inference
            with self._lock:
                extractor = self._net.create_extractor()
                extractor.set_light_mode(True)
                extractor.set_num_threads(self.num_threads)

                extractor.input(self._input_name, mat_in)
                ret, mat_out = extractor.extract(self._output_name)

                if ret != 0:
                    logger.warning(f"NCNN extraction failed: {ret}")
                    return []

            # Convert output to numpy
            output = np.array(mat_out)

            # Handle different output shapes
            # YOLO outputs: [1, num_classes+4, num_anchors] or [1, num_anchors, num_classes+4]
            if output.ndim == 3:
                if output.shape[1] == 84:  # [1, 84, anchors]
                    preds = output[0].T  # [anchors, 84]
                else:  # [1, anchors, 84]
                    preds = output[0]
            elif output.ndim == 2:
                if output.shape[0] == 84:
                    preds = output.T
                else:
                    preds = output
            else:
                logger.warning(f"Unexpected output shape: {output.shape}")
                return []

            # Parse predictions
            boxes_xywh = preds[:, :4]
            class_scores = preds[:, 4:]
            class_ids = class_scores.argmax(axis=1)
            confidences = class_scores[np.arange(len(class_ids)), class_ids]

            # Filter by confidence
            mask = confidences >= self.confidence
            if self.target_classes:
                target_mask = np.isin(class_ids, self.target_classes)
                mask &= target_mask

            boxes_xywh = boxes_xywh[mask]
            confidences = confidences[mask]
            class_ids = class_ids[mask]

            if len(boxes_xywh) == 0:
                return []

            # Convert to xyxy and scale to original image
            boxes = _xywh2xyxy(boxes_xywh)
            boxes[:, [0, 2]] = (boxes[:, [0, 2]] - dw) / ratio
            boxes[:, [1, 3]] = (boxes[:, [1, 3]] - dh) / ratio
            boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, orig_w)
            boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, orig_h)

            # Apply NMS
            keep = _nms(boxes, confidences, self.iou)

            # Build results
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
            logger.error(f"NCNN inference error: {e}")
            return []

    def set_input_output_names(self, input_name: str, output_name: str) -> None:
        """
        Override default input/output layer names if your model uses different names.
        
        Args:
            input_name: Name of the input layer (e.g., "images", "input", "data")
            output_name: Name of the output layer (e.g., "output0", "output", "detection")
        """
        self._input_name = input_name
        self._output_name = output_name

    def set_input_shape(self, width: int, height: int) -> None:
        """
        Override default input shape if your model uses different dimensions.
        
        Args:
            width: Input width (e.g., 320, 416, 640)
            height: Input height (e.g., 320, 416, 640)
        """
        self._input_shape = (height, width)
