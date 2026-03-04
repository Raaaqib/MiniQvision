"""
Raaqib NVR — Object Detection Process (shared worker pool)
Pulls motion-flagged packets, runs YOLO, pushes to tracking queue.
"""

from __future__ import annotations
import time
import logging
import multiprocessing as mp
from pathlib import Path
import cv2

from config import DetectionConfig, SnapshotConfig
from camera.camera import FramePacket
from detectors.base import BaseDetector

logger = logging.getLogger(__name__)


def build_detector(config: DetectionConfig) -> BaseDetector:
    """Factory: instantiate the correct detector backend."""
    if config.backend == "edgetpu":
        from detectors.edgetpu import EdgeTPUDetector
        return EdgeTPUDetector(
            model_path=config.model,
            label_path="labels.txt",
            confidence=config.confidence,
            target_classes=config.target_classes,
        )
    else:
        from detectors.cpu import CPUDetector
        return CPUDetector(
            model_name=config.model,
            confidence=config.confidence,
            iou=config.iou,
            device=config.device,
            target_classes=config.target_classes,
        )


def detection_worker(
    worker_id: int,
    det_config: DetectionConfig,
    snap_config: SnapshotConfig,
    in_queue: mp.Queue,          # receives FramePackets with motion
    tracking_queue: mp.Queue,    # sends annotated FramePackets to tracker
    event_queue: mp.Queue,       # sends detection events to event processor
    stop_event: mp.Event,
):
    """
    Single detection worker process.
    Multiple workers can run in parallel (pool_size in config).
    """
    logging.basicConfig(level=logging.INFO,
                        format=f"[Detector:{worker_id}] %(levelname)s %(message)s")

    detector = build_detector(det_config)
    if not detector.load():
        logger.error("Detector failed to load — worker exiting")
        return

    snap_dir = Path(snap_config.output_dir)
    snap_dir.mkdir(parents=True, exist_ok=True)

    processed = 0
    detected = 0

    logger.info("Detection worker ready")

    while not stop_event.is_set():
        try:
            packet: FramePacket = in_queue.get(timeout=1.0)
        except Exception:
            continue

        processed += 1

        # AI inference
        detections = detector.detect(packet.frame, packet.camera_id)
        packet.detections = detections

        if detections:
            detected += len(detections)

            # Draw annotations on frame
            packet.frame = detector.draw(packet.frame, detections)

            # Save snapshot
            if snap_config.enabled:
                _save_snapshot(packet, detections, snap_dir, snap_config.jpeg_quality)

            # Push detection event
            try:
                event_queue.put_nowait({
                    "type": "detection",
                    "camera_id": packet.camera_id,
                    "timestamp": packet.timestamp,
                    "detections": [d.to_dict() for d in detections],
                })
            except Exception:
                pass

        # Forward to tracker regardless (even with no detections)
        try:
            tracking_queue.put_nowait(packet)
        except Exception:
            pass

    logger.info(f"Worker {worker_id} stopped. "
                f"Processed={processed}, Detected={detected}")


def _save_snapshot(packet: FramePacket, detections, snap_dir: Path, quality: int):
    from datetime import datetime
    try:
        ts = datetime.fromtimestamp(packet.timestamp).strftime("%Y%m%d_%H%M%S_%f")
        labels = "_".join(sorted(set(d.label for d in detections)))
        fname = snap_dir / f"{packet.camera_id}_{labels}_{ts}.jpg"
        cv2.imwrite(str(fname), packet.frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    except Exception as e:
        logger.error(f"Snapshot error: {e}")
