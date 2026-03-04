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

    Dual-stream support:
      When detect_width/detect_height are configured (and differ from width/height),
      each FramePacket carries:
        .frame        — full-res, used for recording & JPEG preview
        .detect_frame — downscaled, used for motion + ONNX (much faster)
      For RTSP cameras with detect_url set, a second FFmpeg process opens the
      sub-stream and its frames are used as detect_frame directly.
    """
    logging.basicConfig(level=logging.INFO,
                        format=f"[Capture:{config.id}] %(levelname)s %(message)s")

    if config.dual_stream_enabled:
        logger.info(
            f"Dual-stream active: record={config.width}x{config.height} "
            f"detect={config.effective_detect_width}x{config.effective_detect_height}"
        )

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


def _make_detect_frame(frame, config: CameraConfig):
    """
    Return a downscaled frame for motion + ONNX inference.
    Returns None if detect resolution == record resolution (no downscale needed).
    """
    if not config.dual_stream_enabled:
        return None
    return cv2.resize(
        frame,
        (config.effective_detect_width, config.effective_detect_height),
        interpolation=cv2.INTER_LINEAR,
    )


def _run_rtsp(config, motion_queue, state_dict, state, stop_event):
    """RTSP capture via FFmpeg pipe. Dispatches to dual-stream handler when detect_url is set."""
    if config.detect_url:
        _run_rtsp_dual(config, motion_queue, state_dict, state, stop_event)
        return

    reader = FFmpegReader(config)
    if not reader.open():
        raise ConnectionError(f"FFmpeg failed to open {config.source}")

    state.connected = True
    state.error = None
    _update_state(state_dict, config.id, state)

    fps_counter = _FPSCounter()
    jpeg_key = f"{config.id}:jpeg"
    bbox_key = f"{config.id}:bboxes"

    try:
        for frame in reader.frames():
            if stop_event.is_set():
                break

            packet = FramePacket(
                camera_id=config.id,
                frame=frame,
                detect_frame=_make_detect_frame(frame, config),
            )

            try:
                motion_queue.put_nowait(packet)
            except Exception:
                pass  # drop frame if queue full

            # Overlay cached bounding boxes and encode JPEG at full FPS
            try:
                display = _draw_cached_bboxes(frame, state_dict.get(bbox_key))
                _, jpeg_buf = cv2.imencode('.jpg', display, [cv2.IMWRITE_JPEG_QUALITY, 70])
                state_dict[jpeg_key] = jpeg_buf.tobytes()
            except Exception:
                pass

            state.frame_count += 1
            state.fps = fps_counter.tick()
            state.last_frame_time = time.time()
            _update_state(state_dict, config.id, state)

    finally:
        reader.close()
        state.connected = False
        _update_state(state_dict, config.id, state)


def _run_rtsp_dual(config, motion_queue, state_dict, state, stop_event):
    """
    True dual-stream RTSP: simultaneous main (high-res record) + sub (low-res detect).
      config.source     — main RTSP URL, full resolution, used for .frame (recording)
      config.detect_url — sub-stream RTSP URL, low resolution, used for .detect_frame
    A background thread reads the sub-stream continuously; the latest frame is stamped
    into every FramePacket produced by the main stream reader.
    """
    import threading

    detect_cfg = CameraConfig(
        id=config.id, name=config.name,
        source=config.detect_url,
        fps_target=config.effective_detect_fps,
        width=config.effective_detect_width,
        height=config.effective_detect_height,
    )

    latest_detect: list = [None]
    detect_lock = threading.Lock()

    def _sub_stream_thread():
        det_reader = FFmpegReader(detect_cfg)
        if not det_reader.open():
            logger.warning(f"Sub-stream failed to open: {config.detect_url}")
            return
        try:
            for dframe in det_reader.frames():
                if stop_event.is_set():
                    break
                with detect_lock:
                    latest_detect[0] = dframe
        finally:
            det_reader.close()

    sub_thread = threading.Thread(
        target=_sub_stream_thread, daemon=True, name=f"sub:{config.id}"
    )
    sub_thread.start()
    logger.info(f"Sub-stream reader started: {config.detect_url}")

    reader = FFmpegReader(config)
    if not reader.open():
        raise ConnectionError(f"FFmpeg failed to open main stream: {config.source}")

    state.connected = True
    state.error = None
    _update_state(state_dict, config.id, state)

    fps_counter = _FPSCounter()
    jpeg_key = f"{config.id}:jpeg"
    bbox_key = f"{config.id}:bboxes"

    try:
        for frame in reader.frames():
            if stop_event.is_set():
                break

            with detect_lock:
                detect_frame = latest_detect[0]

            packet = FramePacket(
                camera_id=config.id,
                frame=frame,
                detect_frame=detect_frame,
            )

            try:
                motion_queue.put_nowait(packet)
            except Exception:
                pass

            try:
                display = _draw_cached_bboxes(frame, state_dict.get(bbox_key))
                _, jpeg_buf = cv2.imencode('.jpg', display, [cv2.IMWRITE_JPEG_QUALITY, 70])
                state_dict[jpeg_key] = jpeg_buf.tobytes()
            except Exception:
                pass

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
    idx = int(config.source)

    # Try DirectShow first (best for real USB cams on Windows),
    # fall back to default backend (MSMF — works with virtual cams like DroidCam)
    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
    if not cap.isOpened():
        logger.info(f"DSHOW failed for index {idx}, trying default backend...")
        cap = cv2.VideoCapture(idx)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.height)

    if not cap.isOpened():
        raise ConnectionError(f"Cannot open USB camera {config.source}")

    state.connected = True
    state.error = None
    _update_state(state_dict, config.id, state)

    fps_counter = _FPSCounter()
    frame_interval = 1.0 / config.fps_target
    jpeg_key = f"{config.id}:jpeg"
    bbox_key = f"{config.id}:bboxes"

    try:
        while not stop_event.is_set():
            t0 = time.time()
            ret, frame = cap.read()
            if not ret:
                raise ConnectionError("USB camera read failed")

            frame = cv2.resize(frame, (config.width, config.height))
            packet = FramePacket(
                camera_id=config.id,
                frame=frame,
                detect_frame=_make_detect_frame(frame, config),
            )

            try:
                motion_queue.put_nowait(packet)
            except Exception:
                pass

            # Overlay cached bounding boxes and encode JPEG at full FPS
            try:
                display = _draw_cached_bboxes(frame, state_dict.get(bbox_key))
                _, jpeg_buf = cv2.imencode('.jpg', display, [cv2.IMWRITE_JPEG_QUALITY, 70])
                state_dict[jpeg_key] = jpeg_buf.tobytes()
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


# ── Bounding-box colour palette (matches detector draw style) ──────────────
_BBOX_PALETTE = {
    "person": (255, 80, 0),
    "car": (0, 200, 255),
    "truck": (0, 160, 220),
    "dog": (0, 255, 120),
    "cat": (255, 0, 200),
    "bicycle": (180, 255, 0),
}


def _draw_cached_bboxes(frame, bbox_data):
    """
    Draw cached bounding boxes on a copy of the frame.
    bbox_data format: {"timestamp": float, "objects": [{"label","confidence","bbox","track_id"}, ...]}
    Returns the annotated frame (or the original if nothing to draw).
    """
    if not bbox_data:
        return frame
    # Expire stale boxes (>2 seconds old)
    age = time.time() - bbox_data.get("timestamp", 0)
    objects = bbox_data.get("objects", [])
    if age > 2.0 or not objects:
        return frame

    out = frame.copy()
    for obj in objects:
        x1, y1, x2, y2 = obj["bbox"]
        label = obj["label"]
        conf = obj["confidence"]
        track_id = obj.get("track_id", "")
        color = _BBOX_PALETTE.get(label, (0, 255, 80))

        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        txt = f"{label} {conf:.0%}" + (f" #{track_id}" if track_id != "" else "")
        (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(out, (x1, y1 - th - 8), (x1 + tw + 6, y1), color, -1)
        cv2.putText(out, txt, (x1 + 3, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    return out


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
