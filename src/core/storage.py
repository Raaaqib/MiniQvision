"""
Raaqib NVR — Storage & File Retention
Deletes old recordings and snapshots based on retention policy.
"""

from __future__ import annotations
import time
import logging
import threading
from pathlib import Path

from src.config import RecordingConfig, SnapshotConfig

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Periodically cleans up old files based on retain_days config.
    Runs in a background thread.
    """

    def __init__(self, rec_config: RecordingConfig, snap_config: SnapshotConfig,
                 check_interval_s: int = 3600):
        self.rec_config = rec_config
        self.snap_config = snap_config
        self.check_interval_s = check_interval_s
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Storage manager started")

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.cleanup()
            except Exception as e:
                logger.error(f"Storage cleanup error: {e}")
            self._stop.wait(self.check_interval_s)

    def cleanup(self):
        """Delete files older than retain_days."""
        now = time.time()

        # Recordings
        rec_dir = Path(self.rec_config.output_dir)
        rec_cutoff = now - (self.rec_config.retain_days * 86400)
        deleted_clips = self._delete_old(rec_dir, "*.mp4", rec_cutoff)

        # Snapshots
        snap_dir = Path(self.snap_config.output_dir)
        snap_cutoff = now - (self.snap_config.retain_days * 86400)
        deleted_snaps = self._delete_old(snap_dir, "*.jpg", snap_cutoff)

        if deleted_clips or deleted_snaps:
            logger.info(f"Cleanup: removed {deleted_clips} clips, {deleted_snaps} snapshots")

    def _delete_old(self, directory: Path, pattern: str, cutoff: float) -> int:
        if not directory.exists():
            return 0
        count = 0
        for f in directory.glob(pattern):
            try:
                if f.stat().st_mtime < cutoff:
                    f.unlink()
                    count += 1
            except Exception as e:
                logger.warning(f"Could not delete {f}: {e}")
        return count

    def get_usage(self) -> dict:
        """Return disk usage stats."""
        def dir_size(path: Path) -> int:
            if not path.exists():
                return 0
            return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())

        rec_dir = Path(self.rec_config.output_dir)
        snap_dir = Path(self.snap_config.output_dir)

        return {
            "recordings_mb": round(dir_size(rec_dir) / 1024 / 1024, 1),
            "snapshots_mb": round(dir_size(snap_dir) / 1024 / 1024, 1),
            "recordings_count": len(list(rec_dir.glob("*.mp4"))) if rec_dir.exists() else 0,
            "snapshots_count": len(list(snap_dir.glob("*.jpg"))) if snap_dir.exists() else 0,
        }
