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
import time
from typing import Any

from config import load_config
from const import (
    FRAME_QUEUE_SIZE, MOTION_QUEUE_SIZE, DETECTION_QUEUE_SIZE,
    TRACKING_QUEUE_SIZE, EVENT_QUEUE_SIZE, RECORD_QUEUE_SIZE,
    DETECTION_POOL_SIZE
)

logger = logging.getLogger("raaqib")


def setup_logging(level: str):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    # ── Load config ───────────────────────────────────────────────────────────
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
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
    tracking_queue  = mp.Queue(TRACKING_QUEUE_SIZE)
    event_queue     = mp.Queue(EVENT_QUEUE_SIZE)
    mqtt_queue      = mp.Queue(EVENT_QUEUE_SIZE)
    db_queue        = mp.Queue(EVENT_QUEUE_SIZE)

    # Per-camera queues
    motion_queues = {}   # camera_id → Queue
    record_queues = {}   # camera_id → Queue (from motion, pre-AI)

    for cam in config.enabled_cameras:
        motion_queues[cam.id] = mp.Queue(FRAME_QUEUE_SIZE)
        record_queues[cam.id] = mp.Queue(RECORD_QUEUE_SIZE)

    # Shared record queue (from tracking → recorder)
    post_detect_record_queue = mp.Queue(RECORD_QUEUE_SIZE)

    processes = []

    def spawn(target, name, *args, **kwargs):
        p = mp.Process(target=target, args=args, kwargs=kwargs, name=name, daemon=True)
        p.start()
        processes.append(p)
        logger.info(f"Started process: {name} (PID {p.pid})")
        return p

    # ── Spawn: Capture + Motion (per camera) ─────────────────────────────────
    from camera.capture import capture_process
    from motion.motion import motion_process

    for cam in config.enabled_cameras:
        spawn(
            capture_process, f"capture:{cam.id}",
            cam, motion_queues[cam.id], state_dict, stop_event
        )
        spawn(
            motion_process, f"motion:{cam.id}",
            cam,
            motion_queues[cam.id],
            detection_queue,
            record_queues[cam.id],   # pre-detection frames for recorder
            state_dict,
            stop_event,
        )

    # ── Spawn: Detection Workers (pool) ───────────────────────────────────────
    from detectors.pool import detection_worker

    pool_size = config.detection.pool_size
    for i in range(pool_size):
        spawn(
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
    from object_processing import tracking_process

    spawn(
        tracking_process, "tracker",
        tracking_queue,
        event_queue,
        post_detect_record_queue,
        state_dict,
        stop_event,
    )

    # ── Spawn: Recording ──────────────────────────────────────────────────────
    from record.recording import recording_process

    spawn(
        recording_process, "recorder",
        config.recording,
        post_detect_record_queue,
        event_queue,
        state_dict,
        stop_event,
    )

    # ── Spawn: Event Processor ────────────────────────────────────────────────
    from events.event_processor import event_processor

    spawn(
        event_processor, "events",
        event_queue,
        mqtt_queue,
        db_queue,
        state_dict,
        stop_event,
    )

    # ── Spawn: Database Writer ────────────────────────────────────────────────
    from database import database_process

    spawn(
        database_process, "database",
        config.database,
        db_queue,
        stop_event,
    )

    # ── Spawn: MQTT Publisher ─────────────────────────────────────────────────
    from mqtt import mqtt_process

    spawn(
        mqtt_process, "mqtt",
        config.mqtt,
        mqtt_queue,
        stop_event,
    )

    # ── Start: FastAPI (in main process thread) ───────────────────────────────
    import threading
    from api.app import run_api

    api_thread = threading.Thread(
        target=run_api,
        args=(config, state_dict, stop_event, config.database),
        daemon=True,
        name="api"
    )
    api_thread.start()
    logger.info(f"API server started on http://{config.api.host}:{config.api.port}")

    # ── Start: Storage Manager ────────────────────────────────────────────────
    from storage import StorageManager

    storage = StorageManager(config.recording, config.snapshots)
    storage.start()

    # ── Signal Handlers ───────────────────────────────────────────────────────
    def shutdown(sig, frame):
        logger.info("Shutdown signal received...")
        stop_event.set()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # ── Monitor ───────────────────────────────────────────────────────────────
    logger.info("All processes started. Press Ctrl+C to stop.")
    logger.info(f"Dashboard: streamlit run web/dashboard.py")

    try:
        while not stop_event.is_set():
            # Restart dead processes
            for p in list(processes):
                if not p.is_alive() and not stop_event.is_set():
                    logger.warning(f"Process {p.name} died (exit={p.exitcode}). "
                                   f"Restarting is not implemented — check logs.")
                    processes.remove(p)
            time.sleep(5)
    except KeyboardInterrupt:
        stop_event.set()

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Shutting down...")
    storage.stop()

    for p in processes:
        p.join(timeout=5)
        if p.is_alive():
            p.kill()

    manager.shutdown()
    logger.info("Raaqib NVR stopped.")


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    main()
