"""
Raaqib NVR — Centralised logging setup.

Call configure_logging() once at the top of every process entry-point function.
Because each spawned process has a blank logging state (spawn start-method),
every process must configure its own handlers.

Two handlers are attached:
  1. StreamHandler        — output to stdout (visible in terminal / Docker logs)
  2. RotatingFileHandler  — writes to logs/raaqib.log

The file handler survives process crashes: logs are still readable after the
fact, and old files are rotated automatically (10 MB × 5 files = 50 MB max).
"""
from __future__ import annotations
import logging
import logging.handlers
from pathlib import Path

# All log files land in <project_root>/logs/
_LOG_DIR  = Path(__file__).parent / "logs"
_LOG_FILE = _LOG_DIR / "raaqib.log"

_MAX_BYTES    = 10 * 1024 * 1024   # 10 MB per file
_BACKUP_COUNT = 5                   # keep up to 5 rotated files → 50 MB total


def configure_logging(process_name: str, level: str = "INFO") -> None:
    """
    Configure logging for the calling process.

    Parameters
    ----------
    process_name:
        A short label embedded in every log line so you can identify which
        subprocess produced the message (e.g. "capture:cam0", "detector:0").
    level:
        Minimum log level as a string ("DEBUG", "INFO", "WARNING", "ERROR").
    """
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        fmt=f"%(asctime)s [{process_name}] %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()

    # Avoid duplicate handlers if called more than once in the same process
    if root.handlers:
        root.handlers.clear()

    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # ── 1. stdout ─────────────────────────────────────────────────────────────
    # Explicitly use sys.stdout so PowerShell doesn't colour lines red
    # (StreamHandler defaults to sys.stderr, which PowerShell treats as errors).
    import sys
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # ── 2. rotating file ──────────────────────────────────────────────────────
    # delay=True: file is only opened on the first actual write, which avoids
    # Windows file-lock problems when many processes start simultaneously.
    fh = logging.handlers.RotatingFileHandler(
        _LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
        delay=True,
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)
