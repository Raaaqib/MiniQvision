"""
Raaqib NVR — Main Entry Point
Spawns and manages all processes:
  - Camera Capture  (per camera)
  - Motion Detection (per camera)
  - Object Detection (shared pool)
  - Object Tracking  (shared)
  - Recording        (shared)
  - Event Processor  (shared)
  - Database Writer  (shared)
  - FastAPI Server   (shared)
  - MQTT Publisher   (shared)
"""

from __future__ import annotations

import logging
import multiprocessing as mp
import signal
import sys
import threading
import time
from collections.abc import Callable
from typing import Any

from src.config import load_config
from src.core.const import (
    DETECTION_QUEUE_SIZE,
    EVENT_QUEUE_SIZE,
    FRAME_QUEUE_SIZE,
    RECORD_QUEUE_SIZE,
    TRACKING_QUEUE_SIZE,
)

logger = logging.getLogger("raaqib")


MONITOR_INTERVAL_SECONDS = 5


def setup_logging(level: str) -> None:
    from src.core.log_utils import configure_logging

    configure_logging("main", level)


def _build_per_camera_queues(enabled_cameras: list[Any]) -> tuple[dict[str, mp.Queue], dict[str, mp.Queue]]:
    motion_queues: dict[str, mp.Queue] = {}
    record_queues: dict[str, mp.Queue] = {}

    for cam in enabled_cameras:
        motion_queues[cam.id] = mp.Queue(FRAME_QUEUE_SIZE)
        record_queues[cam.id] = mp.Queue(RECORD_QUEUE_SIZE)

    return motion_queues, record_queues


def _spawn_process(
    processes: list[mp.Process],
    target: Callable[..., Any],
    name: str,
    *args: Any,
    **kwargs: Any,
) -> mp.Process:
    process = mp.Process(target=target, args=args, kwargs=kwargs, name=name, daemon=True)
    process.start()
    processes.append(process)
    logger.info("Started process: %s (PID %s)", name, process.pid)
    return process


def _start_api_thread(config: Any, state_dict: Any, stop_event: mp.Event) -> threading.Thread:
    from src.api.app import run_api

    api_thread = threading.Thread(
        target=run_api,
        args=(config, state_dict, stop_event, config.database),
        daemon=True,
        name="api",
    )
    api_thread.start()
    logger.info("API server started on http://%s:%s", config.api.host, config.api.port)
    return api_thread


def _monitor_processes(processes: list[mp.Process], stop_event: mp.Event) -> None:
    while not stop_event.is_set():
        for process in list(processes):
            if not process.is_alive() and not stop_event.is_set():
                logger.warning(
                    "Process %s died (exit=%s). Restarting is not implemented - check logs.",
                    process.name,
                    process.exitcode,
                )
                processes.remove(process)
        time.sleep(MONITOR_INTERVAL_SECONDS)


def _graceful_shutdown(processes: list[mp.Process], storage: Any, manager: mp.Manager) -> None:
    logger.info("Shutting down...")
    storage.stop()

    for process in processes:
        process.join(timeout=5)
        if process.is_alive():
            process.kill()

    manager.shutdown()
    logger.info("Raaqib NVR stopped.")


def main() -> None:

    # ── Load config ───────────────────────────────────────────────────────────
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    config = load_config(config_path)
    setup_logging(config.log_level)

    logger.info("=" * 60)
    logger.info("  RAAQIB NVR — Starting")
    logger.info(f"  Cameras: {len(config.enabled_cameras)}")
    logger.info(f"  Model:   {config.detection.model}")
    logger.info(f"  Device:  {config.detection.device}")
    logger.info(f"  API:     http://{config.api.host}:{config.api.port}")
    logger.info("=" * 60)

    # ── Shared state & IPC ────────────────────────────────────────────────────
    manager = mp.Manager()
    state_dict = manager.dict()        # camera states + events
    stop_event = mp.Event()

    # Inter-process queues
    detection_queue = mp.Queue(DETECTION_QUEUE_SIZE)
    tracking_queue = mp.Queue(TRACKING_QUEUE_SIZE)
    event_queue = mp.Queue(EVENT_QUEUE_SIZE)
    mqtt_queue = mp.Queue(EVENT_QUEUE_SIZE)
    db_queue = mp.Queue(EVENT_QUEUE_SIZE)

    # Per-camera queues (from capture->motion and motion->recording)
    motion_queues, record_queues = _build_per_camera_queues(config.enabled_cameras)

    # Shared record queue (from tracking → recorder)
    post_detect_record_queue = mp.Queue(RECORD_QUEUE_SIZE)

    processes = []

    # ── Spawn: Capture + Motion (per camera) ─────────────────────────────────
    from src.core.camera.capture import capture_process
    from src.core.motion.motion import motion_process

    for cam in config.enabled_cameras:
        _spawn_process(
            processes,
            capture_process, f"capture:{cam.id}",
            cam, motion_queues[cam.id], state_dict, stop_event
        )
        _spawn_process(
            processes,
            motion_process, f"motion:{cam.id}",
            cam,
            motion_queues[cam.id],
            detection_queue,
            record_queues[cam.id],   # pre-detection frames for recorder
            state_dict,
            stop_event,
        )

    # ── Spawn: Detection Workers (pool) ───────────────────────────────────────
    from src.core.detectors.pool import detection_worker

    pool_size = config.detection.pool_size
    for i in range(pool_size):
        _spawn_process(
            processes,
            detection_worker, f"detector:{i}",
            i,
            config.detection,
            config.snapshots,
            detection_queue,
            tracking_queue,
            event_queue,
            stop_event,
        )

    # ── Spawn: Tracking ───────────────────────────────────────────────────────
    from src.core.object_processing import tracking_process

    _spawn_process(
        processes,
        tracking_process, "tracker",
        tracking_queue,
        event_queue,
        post_detect_record_queue,
        state_dict,
        stop_event,
    )

    # ── Spawn: Recording ──────────────────────────────────────────────────────
    from src.core.record.recording import recording_process

    _spawn_process(
        processes,
        recording_process, "recorder",
        config.recording,
        post_detect_record_queue,
        event_queue,
        state_dict,
        stop_event,
    )

    # ── Spawn: Event Processor ────────────────────────────────────────────────
    from src.core.events.event_processor import event_processor

    _spawn_process(
        processes,
        event_processor, "events",
        event_queue,
        mqtt_queue,
        db_queue,
        state_dict,
        stop_event,
    )

    # ── Spawn: Database Writer ────────────────────────────────────────────────
    from src.core.database import database_process

    _spawn_process(
        processes,
        database_process, "database",
        config.database,
        db_queue,
        stop_event,
    )

    # ── Spawn: MQTT Publisher ─────────────────────────────────────────────────
    from src.core.mqtt import mqtt_process

    _spawn_process(
        processes,
        mqtt_process, "mqtt",
        config.mqtt,
        mqtt_queue,
        stop_event,
    )

    # ── Start: FastAPI (thread in main process) ──────────────────────────────
    _start_api_thread(config, state_dict, stop_event)

    # ── Start: Storage Manager ────────────────────────────────────────────────
    from src.core.storage import StorageManager

    storage = StorageManager(config.recording, config.snapshots)
    storage.start()

    # ── Signal Handlers ───────────────────────────────────────────────────────
    def shutdown(sig: int, _frame: Any) -> None:
        logger.info("Shutdown signal received...")
        stop_event.set()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # ── Monitor ───────────────────────────────────────────────────────────────
    logger.info("All processes started. Press Ctrl+C to stop.")

    try:
        _monitor_processes(processes, stop_event)
    except KeyboardInterrupt:
        stop_event.set()

    # ── Shutdown ─────────────────────────────────────────────────────────────
    _graceful_shutdown(processes, storage, manager)


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    main()
