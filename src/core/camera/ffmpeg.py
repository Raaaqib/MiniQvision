"""
Raaqib NVR — FFmpeg Process Handling
Used for reliable RTSP stream ingestion via FFmpeg subprocess → pipe
"""

from __future__ import annotations
import subprocess
import numpy as np
import logging
import time
from typing import Optional, Iterator
from src.config import CameraConfig

logger = logging.getLogger(__name__)


class FFmpegReader:
    """
    Read frames from RTSP (or file) via FFmpeg subprocess piped to stdout.
    More reliable than OpenCV's RTSP backend for streams with packet loss.
    """

    def __init__(self, config: CameraConfig, timeout_s: float = 10.0):
        self.config = config
        self.timeout_s = timeout_s
        self._process: Optional[subprocess.Popen] = None
        self._frame_size: int = config.width * config.height * 3  # BGR24

    def _build_cmd(self) -> list[str]:
        src = self.config.source
        cmd = [
            "ffmpeg",
            "-loglevel", "error",
            "-rtsp_transport", "tcp",
            "-i", src,
            "-vf", f"scale={self.config.width}:{self.config.height}",
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-r", str(self.config.fps_target),
            "-an",          # no audio
            "pipe:1"
        ]
        return cmd

    def open(self) -> bool:
        """Start FFmpeg subprocess."""
        try:
            cmd = self._build_cmd()
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=self._frame_size * 2
            )
            logger.info(f"[{self.config.id}] FFmpeg RTSP reader started")
            return True
        except FileNotFoundError:
            logger.error("ffmpeg not found in PATH")
            return False
        except Exception as e:
            logger.error(f"[{self.config.id}] FFmpeg open error: {e}")
            return False

    def read(self) -> Optional[np.ndarray]:
        """Read one frame. Returns None on EOF or error."""
        if not self._process or not self._process.stdout:
            return None
        try:
            raw = self._process.stdout.read(self._frame_size)
            if len(raw) < self._frame_size:
                return None
            frame = np.frombuffer(raw, dtype=np.uint8).reshape(
                self.config.height, self.config.width, 3
            )
            return frame
        except Exception as e:
            logger.error(f"[{self.config.id}] Frame read error: {e}")
            return None

    def frames(self) -> Iterator[np.ndarray]:
        """Generator: yields frames until stream ends."""
        while True:
            frame = self.read()
            if frame is None:
                break
            yield frame

    def close(self):
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                self._process.kill()
            finally:
                self._process = None
        logger.info(f"[{self.config.id}] FFmpeg reader closed")

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()


class FFmpegWriter:
    """
    Write frames to MP4 file via FFmpeg subprocess pipe from stdin.
    Used by the Recording process.
    """

    def __init__(self, output_path: str, width: int, height: int,
                 fps: int = 10, codec: str = "libx264", crf: int = 23):
        self.output_path = output_path
        self.width = width
        self.height = height
        self.fps = fps
        self.codec = codec
        self.crf = crf
        self._process: Optional[subprocess.Popen] = None
        self._frame_size = width * height * 3

    def _build_cmd(self) -> list[str]:
        return [
            "ffmpeg", "-y",
            "-loglevel", "error",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{self.width}x{self.height}",
            "-pix_fmt", "bgr24",
            "-r", str(self.fps),
            "-i", "pipe:0",
            "-vcodec", self.codec,
            "-crf", str(self.crf),
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            self.output_path
        ]

    def open(self) -> bool:
        try:
            self._process = subprocess.Popen(
                self._build_cmd(),
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except FileNotFoundError:
            logger.error("ffmpeg not found — recording disabled")
            return False
        except Exception as e:
            logger.error(f"FFmpegWriter open error: {e}")
            return False

    def write(self, frame: np.ndarray) -> bool:
        if not self._process or not self._process.stdin:
            return False
        try:
            self._process.stdin.write(frame.tobytes())
            return True
        except BrokenPipeError:
            return False
        except Exception as e:
            logger.error(f"FFmpegWriter write error: {e}")
            return False

    def close(self) -> str:
        """Close writer and return output path."""
        if self._process:
            try:
                if self._process.stdin:
                    self._process.stdin.close()
                self._process.wait(timeout=15)
            except Exception:
                self._process.kill()
            finally:
                self._process = None
        return self.output_path

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()
