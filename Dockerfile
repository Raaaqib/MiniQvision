# ─────────────────────────────────────────────────────────────────────────────
# Raaqib NVR — Dockerfile
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# ── System dependencies ───────────────────────────────────────────────────────
# ffmpeg: required for RTSP capture and MP4 recording
# libgl1 / libglib2.0-0: required by OpenCV headless
# libgomp1: required by ONNX Runtime (OpenMP threading)
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /opt/raaqib

# ── Python dependencies ───────────────────────────────────────────────────────
# Swap opencv-python (requires display) → opencv-python-headless (Docker-safe)
COPY requirements.txt .
RUN sed \
        -e 's/^opencv-python==/# opencv-python==/g' \
        -e 's/^# opencv-python-headless==/opencv-python-headless==/g' \
        requirements.txt > requirements.docker.txt \
    && pip install --no-cache-dir -r requirements.docker.txt \
    && rm requirements.docker.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY . .

# ── Data directories (overridden by volume mounts at runtime) ─────────────────
RUN mkdir -p recordings snapshots models data

# ── Ports ─────────────────────────────────────────────────────────────────────
# 8000 — FastAPI REST API + MJPEG streams + web UI
EXPOSE 8000

# ── Health check ──────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/status', timeout=5)" || exit 1

# ── Startup command ───────────────────────────────────────────────────────────
# Fail fast if config is missing to avoid silently booting with local defaults.
CMD ["sh", "-c", "CFG=${RAAQIB_CONFIG:-config.yaml}; if [ ! -f \"$CFG\" ]; then echo \"ERROR: Config file not found: $CFG\"; echo \"Hint: mount config.docker.yaml to /opt/raaqib/config.yaml or set RAAQIB_CONFIG\"; exit 64; fi; exec python app.py \"$CFG\""]
