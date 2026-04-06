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
from importlib import import_module
from collections.abc import Callable
from pathlib import Path
from typing import Any

_config_module = import_module("src.config")
load_config = _config_module.load_config
validate_config = _config_module.validate_config
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


def _start_api_thread(config: Any, state_dict: Any, stop_event: Any) -> threading.Thread:
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


def _monitor_processes(processes: list[mp.Process], stop_event: Any) -> None:
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


def _graceful_shutdown(processes: list[mp.Process], storage: Any, manager: Any) -> None:
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

    # Pass config path for relative path resolution
    config_path_obj = Path(config_path) if config_path else None
    errors = validate_config(config, config_path_obj)
    if errors:
        for err in errors:
            logger.error("Config error: %s", err)
        raise SystemExit("Aborting: config validation failed. See errors above.")

    logger.info("=" * 60)
    logger.info("  RAAQIB NVR — Starting")
    logger.info("  Cameras: %s", len(config.enabled_cameras))
    logger.info("  Models:  %s", len(config.models))
    logger.info("  API:     http://%s:%s", config.api.host, config.api.port)
    logger.info("=" * 60)

    # ── Shared state & IPC ────────────────────────────────────────────────────
    manager = mp.Manager()
    state_dict = manager.dict()        # camera states + events
    stop_event = mp.Event()

    # Inter-process queues
    tracking_queue: mp.Queue = mp.Queue(TRACKING_QUEUE_SIZE)
    event_queue: mp.Queue = mp.Queue(EVENT_QUEUE_SIZE)
    mqtt_queue: mp.Queue = mp.Queue(EVENT_QUEUE_SIZE)
    db_queue: mp.Queue = mp.Queue(EVENT_QUEUE_SIZE)

    camera_model_map: dict[str, str] = {
        cam.id: cam.model for cam in config.enabled_cameras
    }

    # One detection queue per unique model.
    detection_queues: dict[str, mp.Queue] = {}
    for model_id in set(camera_model_map.values()):
        detection_queues[model_id] = mp.Queue(DETECTION_QUEUE_SIZE)

    camera_zones: dict[str, list] = {
        cam.id: cam.zones
        for cam in config.enabled_cameras
        if cam.zones
    }

    if camera_zones:
        zone_summary = ", ".join(
            f"{cam_id}: {len(zones)} zone(s)"
            for cam_id, zones in camera_zones.items()
        )
        logger.info("Zone filtering active — %s", zone_summary)
    else:
        logger.info("No zones configured — zone filtering disabled")

    logger.info("RAAQIB NVR — Model assignment")
    for cam in config.enabled_cameras:
        model_cfg = config.models[cam.model]
        logger.info(
            "  %-20s -> %-20s (%s, %s, %s worker(s))",
            cam.id,
            cam.model,
            model_cfg.path,
            model_cfg.device,
            model_cfg.pool_size,
        )

    # Per-camera queues (from capture->motion and motion->recording)
    motion_queues, record_queues = _build_per_camera_queues(config.enabled_cameras)

    # Shared record queue (from tracking → recorder)
    post_detect_record_queue: mp.Queue = mp.Queue(RECORD_QUEUE_SIZE)

    processes: list[mp.Process] = []

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
            detection_queues,
            camera_model_map,
            record_queues[cam.id],   # pre-detection frames for recorder
            state_dict,
            stop_event,
        )

    # ── Spawn: Detection Workers (pool) ───────────────────────────────────────
    from src.core.detectors.pool import detection_worker

    for model_id in set(camera_model_map.values()):
        model_cfg = config.models[model_id]
        model_queue = detection_queues[model_id]
        for i in range(model_cfg.pool_size):
            _spawn_process(
                processes,
                detection_worker, f"detector:{model_id}:{i}",
                i,
                model_cfg,
                config.snapshots,
                model_queue,
                tracking_queue,
                event_queue,
                stop_event,
                config.lpr,
                config.database,
                camera_zones,
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
