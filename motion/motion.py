"""
Raaqib NVR — Motion Detection Process (one per camera)
Runs MOG2 background subtraction on each frame.
Only forwards packets with motion to the detection queue.
"""

from __future__ import annotations
import cv2
import numpy as np
import time
import logging
import multiprocessing as mp

from config import CameraConfig
from camera.camera import FramePacket
from const import (
    MOG2_HISTORY, MOG2_VAR_THRESHOLD, MIN_CONTOUR_AREA, MOTION_COOLDOWN_S
)

logger = logging.getLogger(__name__)


class MOG2MotionDetector:
    """
    Background subtraction using OpenCV's MOG2 algorithm.
    Fast classical CV — runs on every frame with no GPU needed.
    """

    def __init__(
        self,
        history: int = MOG2_HISTORY,
        var_threshold: float = MOG2_VAR_THRESHOLD,
        min_contour_area: int = MIN_CONTOUR_AREA,
    ):
        self.min_contour_area = min_contour_area
        self._subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history,
            varThreshold=var_threshold,
            detectShadows=False
        )
        self._kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    def detect(self, frame: np.ndarray) -> tuple[bool, list[tuple], float]:
        """
        Args:
            frame: BGR numpy array

        Returns:
            motion_detected: bool
            bboxes: list of (x, y, w, h)
            score: fraction of frame covered by motion
        """
        fg = self._subtractor.apply(frame)
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, self._kernel)
        fg = cv2.dilate(fg, self._kernel, iterations=2)

        contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        bboxes = []
        total_area = 0
        frame_area = frame.shape[0] * frame.shape[1]

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area >= self.min_contour_area:
                x, y, w, h = cv2.boundingRect(cnt)
                bboxes.append((x, y, w, h))
                total_area += area

        score = total_area / frame_area if frame_area > 0 else 0.0
        return len(bboxes) > 0, bboxes, score


def motion_process(
    config: CameraConfig,
    in_queue: mp.Queue,          # receives FramePackets from capture
    detection_queue: mp.Queue,   # sends motion packets to detection pool
    record_queue: mp.Queue,      # sends all packets to recorder
    state_dict: dict,
    stop_event: mp.Event,
):
    """
    Motion detection process entry point.
    Forwards ALL packets to record_queue (for pre-buffer).
    Only forwards motion packets to detection_queue.
    """
    logging.basicConfig(level=logging.INFO,
                        format=f"[Motion:{config.id}] %(levelname)s %(message)s")

    detector = MOG2MotionDetector(
        min_contour_area=config.min_contour_area
    )

    last_motion_time = 0.0
    motion_frame_count = 0
    total_frames = 0

    logger.info("Motion detection process started")

    while not stop_event.is_set():
        try:
            packet: FramePacket = in_queue.get(timeout=1.0)
        except Exception:
            continue

        total_frames += 1
        now = time.time()

        # Run classical CV
        motion, boxes, score = detector.detect(packet.frame)

        packet.motion_detected = motion
        packet.motion_boxes = boxes

        # Always feed recorder (for pre-capture buffer)
        try:
            record_queue.put_nowait(packet)
        except Exception:
            pass

        # Update shared state
        try:
            cam_state = state_dict.get(config.id, {})
            cam_state["motion"] = motion
            cam_state["motion_score"] = round(score, 3)
            state_dict[config.id] = cam_state
        except Exception:
            pass

        # Forward to detection pool only if motion (with cooldown)
        if motion and (now - last_motion_time) >= MOTION_COOLDOWN_S:
            last_motion_time = now
            motion_frame_count += 1
            try:
                detection_queue.put_nowait(packet)
            except Exception:
                pass  # drop if detection pool is busy

    logger.info(f"Motion process stopped. "
                f"Processed {total_frames} frames, "
                f"triggered AI {motion_frame_count} times")
