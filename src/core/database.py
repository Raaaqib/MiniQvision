"""
Raaqib NVR — SQLite Database Interface
Stores events, clips metadata, and detection history.
"""

from __future__ import annotations
import sqlite3
import logging
import time
import multiprocessing as mp
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id    TEXT UNIQUE,
    camera_id   TEXT NOT NULL,
    label       TEXT NOT NULL,
    start_time  REAL NOT NULL,
    end_time    REAL,
    duration    REAL,
    confidence  REAL,
    snapshot    TEXT,
    clip        TEXT,
    created_at  REAL DEFAULT (unixepoch('now'))
);

CREATE TABLE IF NOT EXISTS clips (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_id   TEXT NOT NULL,
    path        TEXT NOT NULL,
    labels      TEXT,
    start_time  REAL,
    end_time    REAL,
    size_bytes  INTEGER,
    created_at  REAL DEFAULT (unixepoch('now'))
);

CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_id   TEXT NOT NULL,
    path        TEXT NOT NULL,
    label       TEXT,
    confidence  REAL,
    created_at  REAL DEFAULT (unixepoch('now'))
);

CREATE INDEX IF NOT EXISTS idx_events_camera   ON events(camera_id);
CREATE INDEX IF NOT EXISTS idx_events_label    ON events(label);
CREATE INDEX IF NOT EXISTS idx_events_start    ON events(start_time);
CREATE INDEX IF NOT EXISTS idx_clips_camera    ON clips(camera_id);
"""


class Database:
    """SQLite database interface for Raaqib NVR."""

    def __init__(self, path: str = "raaqib.db"):
        self.path = path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            conn.commit()
        logger.info(f"Database initialized: {self.path}")

    def insert_event(self, event: dict):
        sql = """
        INSERT OR REPLACE INTO events
            (event_id, camera_id, label, start_time, end_time, duration, confidence, snapshot, clip)
        VALUES
            (:event_id, :camera_id, :label, :start_time, :end_time, :duration, :peak_confidence, :snapshot, :clip)
        """
        with self._connect() as conn:
            conn.execute(sql, event)
            conn.commit()

    def get_events(self, camera_id: str = None, label: str = None,
                   limit: int = 100, offset: int = 0) -> list[dict]:
        conditions = []
        params = {}
        if camera_id:
            conditions.append("camera_id = :camera_id")
            params["camera_id"] = camera_id
        if label:
            conditions.append("label = :label")
            params["label"] = label

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"""
        SELECT * FROM events {where}
        ORDER BY start_time DESC LIMIT :limit OFFSET :offset
        """
        params["limit"] = limit
        params["offset"] = offset

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_clips(self, camera_id: str = None, limit: int = 50) -> list[dict]:
        where = "WHERE camera_id = :camera_id" if camera_id else ""
        params = {"limit": limit}
        if camera_id:
            params["camera_id"] = camera_id
        sql = f"SELECT * FROM clips {where} ORDER BY created_at DESC LIMIT :limit"
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def get_stats(self) -> dict:
        with self._connect() as conn:
            total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            total_clips  = conn.execute("SELECT COUNT(*) FROM clips").fetchone()[0]
            by_label = conn.execute(
                "SELECT label, COUNT(*) as count FROM events GROUP BY label ORDER BY count DESC"
            ).fetchall()
        return {
            "total_events": total_events,
            "total_clips": total_clips,
            "by_label": [dict(r) for r in by_label],
        }


def database_process(
    db_path: str,
    db_queue: mp.Queue,
    stop_event: mp.Event,
):
    """Database writer process — consumes from db_queue and writes to SQLite."""
    from log_utils import configure_logging
    configure_logging("database")

    db = Database(db_path)
    logger.info("Database process started")

    while not stop_event.is_set():
        try:
            msg = db_queue.get(timeout=1.0)
        except Exception:
            continue

        try:
            msg_type = msg.get("type")
            data = msg.get("data", {})

            if msg_type == "event":
                db.insert_event(data)
        except Exception as e:
            logger.error(f"DB write error: {e}")

    logger.info("Database process stopped")
