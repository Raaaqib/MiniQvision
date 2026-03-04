"""
Raaqib NVR — Event Processor
Manages detection event lifecycle: start, update, end.
Writes events to SQLite and publishes to MQTT.
"""

from __future__ import annotations
import time
import logging
import multiprocessing as mp
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """A detection event with lifecycle tracking."""
    event_id: str
    camera_id: str
    label: str
    start_time: float
    end_time: Optional[float] = None
    peak_confidence: float = 0.0
    snapshot_path: Optional[str] = None
    clip_path: Optional[str] = None
    update_count: int = 0
    active: bool = True

    @property
    def duration(self) -> float:
        end = self.end_time or time.time()
        return end - self.start_time

    def to_dict(self) -> dict:
        from datetime import datetime
        return {
            "event_id": self.event_id,
            "camera_id": self.camera_id,
            "label": self.label,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": round(self.duration, 2),
            "peak_confidence": round(self.peak_confidence, 3),
            "snapshot": self.snapshot_path,
            "clip": self.clip_path,
            "active": self.active,
        }


def event_processor(
    event_queue: mp.Queue,
    mqtt_queue: mp.Queue,
    db_queue: mp.Queue,
    state_dict: dict,
    stop_event: mp.Event,
    event_timeout_s: float = 15.0,
):
    """
    Event processor entry point.
    Reads events from queue, manages lifecycle, writes to DB, publishes MQTT.
    """
    logging.basicConfig(level=logging.INFO,
                        format="[Events] %(levelname)s %(message)s")

    import uuid
    active_events: dict[str, Event] = {}  # key: f"{camera_id}:{label}"
    all_events: list[dict] = []           # in-memory list for API

    logger.info("Event processor started")

    while not stop_event.is_set():
        # Check for timed-out events
        now = time.time()
        for key in list(active_events.keys()):
            ev = active_events[key]
            if ev.active and (now - (ev.end_time or ev.start_time)) > event_timeout_s:
                ev.active = False
                ev.end_time = now
                logger.info(f"Event ended: {ev.label} on {ev.camera_id} "
                            f"({ev.duration:.1f}s)")
                _publish(mqtt_queue, "event_end", ev.to_dict())
                _write_db(db_queue, ev.to_dict())
                all_events.append(ev.to_dict())
                all_events = all_events[-500:]  # keep last 500
                del active_events[key]

        # Process incoming events
        try:
            msg = event_queue.get(timeout=0.5)
        except Exception:
            continue

        msg_type = msg.get("type")
        cam_id = msg.get("camera_id")
        timestamp = msg.get("timestamp", time.time())

        if msg_type == "detection":
            detections = msg.get("detections", [])
            for det in detections:
                label = det["label"]
                key = f"{cam_id}:{label}"
                conf = det.get("confidence", 0.0)

                if key in active_events:
                    ev = active_events[key]
                    ev.end_time = timestamp
                    ev.update_count += 1
                    ev.peak_confidence = max(ev.peak_confidence, conf)
                    _publish(mqtt_queue, "event_update", ev.to_dict())
                else:
                    ev = Event(
                        event_id=str(uuid.uuid4())[:8],
                        camera_id=cam_id,
                        label=label,
                        start_time=timestamp,
                        end_time=timestamp,
                        peak_confidence=conf,
                    )
                    active_events[key] = ev
                    logger.info(f"Event started: {label} on {cam_id}")
                    _publish(mqtt_queue, "event_start", ev.to_dict())

        elif msg_type == "clip_saved":
            # Update event with clip path
            clip_path = msg.get("clip_path")
            cam_id = msg.get("camera_id")
            for ev in active_events.values():
                if ev.camera_id == cam_id and not ev.clip_path:
                    ev.clip_path = clip_path
                    break

        # Update shared state for API
        try:
            state_dict["events"] = all_events[-50:]
            state_dict["active_events"] = [e.to_dict() for e in active_events.values()]
        except Exception:
            pass

    logger.info("Event processor stopped")


def _publish(mqtt_queue: mp.Queue, event_type: str, data: dict):
    try:
        mqtt_queue.put_nowait({"event_type": event_type, "data": data})
    except Exception:
        pass


def _write_db(db_queue: mp.Queue, event: dict):
    try:
        db_queue.put_nowait({"type": "event", "data": event})
    except Exception:
        pass
