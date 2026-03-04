"""
Raaqib NVR — Frame Capture Process (one per camera)
Reads frames from RTSP/USB and pushes FramePackets into the motion queue.
"""

from __future__ import annotations
import cv2
import time
import logging
import multiprocessing as mp
from typing import Optional

from config import CameraConfig
from camera.camera import FramePacket, CameraState
from camera.ffmpeg import FFmpegReader

logger = logging.getLogger(__name__)


def capture_process(
    config: CameraConfig,
    motion_queue: mp.Queue,
    state_dict: dict,           # shared Manager dict
    stop_event: mp.Event,
):
    """
    Entry point for the capture process.
    Reads frames and pushes FramePackets to motion_queue.
    """
    logging.basicConfig(level=logging.INFO,
                        format=f"[Capture:{config.id}] %(levelname)s %(message)s")

    state = CameraState(camera_id=config.id)
    _update_state(state_dict, config.id, state)

    retry_delay = 2.0

    while not stop_event.is_set():
        try:
            if config.is_rtsp:
                _run_rtsp(config, motion_queue, state_dict, state, stop_event)
            else:
                _run_usb(config, motion_queue, state_dict, state, stop_event)
        except Exception as e:
            state.connected = False
            state.error = str(e)
            _update_state(state_dict, config.id, state)
            logger.warning(f"Stream error: {e}. Retrying in {retry_delay}s")
            time.sleep(retry_delay)

    logger.info("Capture process stopped")


def _run_rtsp(config, motion_queue, state_dict, state, stop_event):
    """RTSP capture via FFmpeg pipe."""
    reader = FFmpegReader(config)
    if not reader.open():
        raise ConnectionError(f"FFmpeg failed to open {config.source}")

    state.connected = True
    state.error = None
    _update_state(state_dict, config.id, state)

    fps_counter = _FPSCounter()

    try:
        for frame in reader.frames():
            if stop_event.is_set():
                break

            packet = FramePacket(
                camera_id=config.id,
                frame=frame,
            )

            try:
                motion_queue.put_nowait(packet)
            except Exception:
                pass  # drop frame if queue full

            state.frame_count += 1
            state.fps = fps_counter.tick()
            state.last_frame_time = time.time()
            _update_state(state_dict, config.id, state)

    finally:
        reader.close()
        state.connected = False
        _update_state(state_dict, config.id, state)


def _run_usb(config, motion_queue, state_dict, state, stop_event):
    """USB webcam capture via OpenCV."""
    cap = cv2.VideoCapture(int(config.source))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.height)

    if not cap.isOpened():
        raise ConnectionError(f"Cannot open USB camera {config.source}")

    state.connected = True
    state.error = None
    _update_state(state_dict, config.id, state)

    fps_counter = _FPSCounter()
    frame_interval = 1.0 / config.fps_target

    try:
        while not stop_event.is_set():
            t0 = time.time()
            ret, frame = cap.read()
            if not ret:
                raise ConnectionError("USB camera read failed")

            frame = cv2.resize(frame, (config.width, config.height))
            packet = FramePacket(camera_id=config.id, frame=frame)

            try:
                motion_queue.put_nowait(packet)
            except Exception:
                pass

            state.frame_count += 1
            state.fps = fps_counter.tick()
            state.last_frame_time = time.time()
            _update_state(state_dict, config.id, state)

            elapsed = time.time() - t0
            sleep = frame_interval - elapsed
            if sleep > 0:
                time.sleep(sleep)
    finally:
        cap.release()
        state.connected = False
        _update_state(state_dict, config.id, state)


def _update_state(state_dict, camera_id, state):
    try:
        state_dict[camera_id] = state.to_dict()
    except Exception:
        pass


class _FPSCounter:
    def __init__(self, window: float = 2.0):
        self._window = window
        self._times = []

    def tick(self) -> float:
        now = time.time()
        self._times.append(now)
        self._times = [t for t in self._times if now - t <= self._window]
        return len(self._times) / self._window
