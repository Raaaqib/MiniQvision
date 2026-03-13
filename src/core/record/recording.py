"""
Raaqib NVR — Recording Process
Pre-buffer + event-triggered clip recording via FFmpeg.
"""

from __future__ import annotations
import time
import logging
import multiprocessing as mp
import threading
from collections import deque
from pathlib import Path
from datetime import datetime

from src.core.camera.camera import FramePacket
from src.core.camera.ffmpeg import FFmpegWriter
from src.config import RecordingConfig

logger = logging.getLogger(__name__)


class CameraRecorder:
    """
    Handles recording for a single camera.
    Maintains a pre-capture ring buffer.
    Starts/extends/stops recording based on detection events.
    """

    def __init__(self, camera_id: str, config: RecordingConfig):
        self.camera_id = camera_id
        self.config = config
        self.out_dir = Path(config.output_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

        # Pre-capture circular buffer
        pre_frames = config.pre_capture_s * config.fps
        self._pre_buffer: deque = deque(maxlen=int(pre_frames))

        self._writer: FFmpegWriter | None = None
        self._lock = threading.Lock()
        self._recording = False
        self._stop_timer: threading.Timer | None = None
        self._current_path: str | None = None
        self._current_labels: list[str] = []
        self.clips_saved = 0

    def feed(self, frame, detections: list):
        """Feed a frame. Called for every frame (recording or not)."""
        with self._lock:
            self._pre_buffer.append(frame.copy())

            if detections:
                labels = list(set(d["label"] for d in detections))
                if self._recording:
                    self._extend(labels)
                else:
                    self._start(labels, frame)

            if self._recording and self._writer:
                self._writer.write(frame)

    def _start(self, labels: list, frame):
        """Start recording with actual frame dimensions."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        label_str = "_".join(labels)
        fname = f"{self.camera_id}_{label_str}_{ts}.mp4"
        path = str(self.out_dir / fname)

        # Get actual frame dimensions
        height, width = frame.shape[:2]

        writer = FFmpegWriter(
            output_path=path,
            width=width,
            height=height,
            fps=self.config.fps,
            codec=self.config.codec,
            crf=self.config.crf,
        )

        if not writer.open():
            logger.error(f"[{self.camera_id}] Failed to open FFmpeg writer")
            return

        # Flush pre-buffer first
        for buffered in list(self._pre_buffer):
            writer.write(buffered)

        self._writer = writer
        self._recording = True
        self._current_path = path
        self._current_labels = labels
        logger.info(f"[{self.camera_id}] Recording started: {fname}")
        self._schedule_stop()

    def _extend(self, labels: list):
        if self._stop_timer:
            self._stop_timer.cancel()
        for lbl in labels:
            if lbl not in self._current_labels:
                self._current_labels.append(lbl)
        self._schedule_stop()

    def _schedule_stop(self):
        self._stop_timer = threading.Timer(
            self.config.post_capture_s, self._stop
        )
        self._stop_timer.daemon = True
        self._stop_timer.start()

    def _stop(self):
        with self._lock:
            if not self._recording:
                return
            self._recording = False
            if self._writer:
                path = self._writer.close()
                self._writer = None
                self.clips_saved += 1
                logger.info(f"[{self.camera_id}] Clip saved: {path}")
            self._current_path = None

    @property
    def is_recording(self) -> bool:
        return self._recording


def recording_process(
    rec_config: RecordingConfig,
    in_queue: mp.Queue,          # receives FramePackets (from motion or tracking)
    event_queue: mp.Queue,       # notify event processor of saved clips
    state_dict: dict,
    stop_event: mp.Event,
):
    """Recording process entry point."""
    from src.core.log_utils import configure_logging
    configure_logging("recorder")

    if not rec_config.enabled:
        logger.info("Recording disabled in config")
        while not stop_event.is_set():
            try:
                in_queue.get(timeout=1.0)
            except Exception:
                pass
        return

    recorders: dict[str, CameraRecorder] = {}

    logger.info("Recording process started")

    while not stop_event.is_set():
        try:
            packet: FramePacket = in_queue.get(timeout=1.0)
        except Exception:
            continue

        cam_id = packet.camera_id
        if cam_id not in recorders:
            recorders[cam_id] = CameraRecorder(cam_id, rec_config)

        recorder = recorders[cam_id]
        det_dicts = [d.to_dict() for d in packet.detections] if packet.detections else []
        recorder.feed(packet.frame, det_dicts)

        # Update state
        try:
            cam_state = state_dict.get(cam_id, {})
            cam_state["recording"] = recorder.is_recording
            cam_state["clips_saved"] = recorder.clips_saved
            state_dict[cam_id] = cam_state
        except Exception:
            pass

    # Stop all recorders
    for rec in recorders.values():
        rec._stop()

    logger.info("Recording process stopped")
