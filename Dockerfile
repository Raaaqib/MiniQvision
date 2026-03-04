# ─────────────────────────────────────────────
# Raaqib NVR — Docker Image
# ─────────────────────────────────────────────
FROM python:3.11-slim

LABEL maintainer="Raaqib NVR"
LABEL description="AI-Powered Network Video Recorder"

# ── System dependencies ─────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ───────────────────────────────────────────────────────
WORKDIR /opt/raaqib

# ── Python dependencies ─────────────────────────────────────────────────────
# Uses ONNX Runtime instead of PyTorch (~50MB vs ~2GB)
# Install ultralytics WITHOUT torch (--no-deps), then only the deps we need
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=300 --retries=5 \
    ultralytics --no-deps \
    && pip install --no-cache-dir --timeout=300 --retries=5 -r requirements.txt

# ── Application code ────────────────────────────────────────────────────────
COPY . .

# ── Create data directories ─────────────────────────────────────────────────
RUN mkdir -p /data/recordings /data/snapshots /data/db

# ── Entrypoint ──────────────────────────────────────────────────────────────
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# ── Ports ────────────────────────────────────────────────────────────────────
# 8000 = FastAPI + Web UI
# 8501 = Streamlit Dashboard (optional)
EXPOSE 8000 8501

# ── Health check ─────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/status || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
