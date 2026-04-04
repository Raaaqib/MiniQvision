"""
LPR Database — extends Raaqib's existing SQLite DB with LPR tables.

Tables
------
lpr_events       — every recognised plate event
lpr_whitelist    — persisted known plates (mirrors runtime whitelist)
"""

from __future__ import annotations
import logging
import sqlite3
from datetime import datetime
from typing import List, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
DDL = """
CREATE TABLE IF NOT EXISTS lpr_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_id       TEXT    NOT NULL,
    zone_id         TEXT    NOT NULL,
    plate           TEXT    NOT NULL,
    confidence      REAL    NOT NULL,
    known           INTEGER NOT NULL DEFAULT 0,   -- 0=unknown, 1=known
    alert           INTEGER NOT NULL DEFAULT 0,   -- 0=no alert, 1=alert
    bbox_vehicle    TEXT,                          -- "x1,y1,x2,y2"
    bbox_plate      TEXT,                          -- "x1,y1,x2,y2"
    snapshot_path   TEXT,
    created_at      TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lpr_events_plate      ON lpr_events(plate);
CREATE INDEX IF NOT EXISTS idx_lpr_events_camera     ON lpr_events(camera_id);
CREATE INDEX IF NOT EXISTS idx_lpr_events_created_at ON lpr_events(created_at);
CREATE INDEX IF NOT EXISTS idx_lpr_events_alert      ON lpr_events(alert);

CREATE TABLE IF NOT EXISTS lpr_whitelist (
    plate       TEXT PRIMARY KEY,
    note        TEXT,
    added_at    TEXT NOT NULL
);
"""


# ──────────────────────────────────────────────────────────────────────────────

class LPRDatabase:
    """Thin SQLite wrapper for LPR data."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_schema()

    # ------------------------------------------------------------------
    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    def _ensure_schema(self):
        with self._conn() as conn:
            conn.executescript(DDL)
        logger.info(f"[LPR] DB schema ready: {self.db_path}")

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def insert_event(self, result) -> int:
        """Insert an LPRResult. Returns the new row id."""
        def _fmt_bbox(b):
            return ",".join(map(str, b)) if b else None

        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO lpr_events
                    (camera_id, zone_id, plate, confidence, known, alert,
                     bbox_vehicle, bbox_plate, snapshot_path, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    result.camera_id,
                    result.zone_id,
                    result.plate,
                    result.confidence,
                    int(result.known),
                    int(result.alert),
                    _fmt_bbox(result.bbox_vehicle),
                    _fmt_bbox(result.bbox_plate),
                    result.snapshot_path,
                    result.timestamp.isoformat(),
                ),
            )
            return cur.lastrowid

    def get_events(
        self,
        camera_id: Optional[str] = None,
        plate: Optional[str] = None,
        alert_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        clauses, params = [], []
        if camera_id:
            clauses.append("camera_id = ?"); params.append(camera_id)
        if plate:
            clauses.append("plate LIKE ?"); params.append(f"%{plate.upper()}%")
        if alert_only:
            clauses.append("alert = 1")

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params += [limit, offset]

        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM lpr_events
                {where}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                params,
            ).fetchall()
        return [dict(r) for r in rows]

    def count_events(self, alert_only: bool = False) -> int:
        where = "WHERE alert = 1" if alert_only else ""
        with self._conn() as conn:
            return conn.execute(
                f"SELECT COUNT(*) FROM lpr_events {where}"
            ).fetchone()[0]

    # ------------------------------------------------------------------
    # Whitelist persistence
    # ------------------------------------------------------------------

    def load_whitelist(self) -> List[str]:
        """Return all plates from the persisted whitelist."""
        with self._conn() as conn:
            rows = conn.execute("SELECT plate FROM lpr_whitelist").fetchall()
        return [r["plate"] for r in rows]

    def add_to_whitelist(self, plate: str, note: str = "") -> bool:
        norm = plate.upper().strip()
        if not norm:
            return False
        try:
            with self._conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO lpr_whitelist (plate, note, added_at) VALUES (?,?,?)",
                    (norm, note, datetime.utcnow().isoformat()),
                )
            return True
        except Exception as e:
            logger.error(f"[LPR] DB whitelist add error: {e}")
            return False

    def remove_from_whitelist(self, plate: str) -> bool:
        norm = plate.upper().strip()
        try:
            with self._conn() as conn:
                conn.execute("DELETE FROM lpr_whitelist WHERE plate = ?", (norm,))
            return True
        except Exception as e:
            logger.error(f"[LPR] DB whitelist remove error: {e}")
            return False

    def get_whitelist(self) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT plate, note, added_at FROM lpr_whitelist ORDER BY plate"
            ).fetchall()
        return [dict(r) for r in rows]
