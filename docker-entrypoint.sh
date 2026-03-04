#!/bin/bash
set -e

echo "═══════════════════════════════════════════"
echo "  RAAQIB NVR — Starting (Docker)"
echo "═══════════════════════════════════════════"

# ── Symlink data dirs if using mounted volumes ──
# This maps /data/* volumes into the app's working directories
if [ -d "/data/recordings" ]; then
    rm -rf /opt/raaqib/recordings
    ln -sf /data/recordings /opt/raaqib/recordings
fi

if [ -d "/data/snapshots" ]; then
    rm -rf /opt/raaqib/snapshots
    ln -sf /data/snapshots /opt/raaqib/snapshots
fi

if [ -d "/data/db" ]; then
    # Symlink database file into /data/db for persistence
    if [ ! -f "/data/db/raaqib.db" ]; then
        touch /data/db/raaqib.db
    fi
    ln -sf /data/db/raaqib.db /opt/raaqib/raaqib.db
fi

# ── Use mounted config if available ──
if [ -f "/config/config.yaml" ]; then
    echo "[entrypoint] Using mounted config from /config/config.yaml"
    ln -sf /config/config.yaml /opt/raaqib/config.yaml
fi

# ── Use mounted model if available ──
if [ -d "/models" ]; then
    for model_file in /models/*.pt; do
        if [ -f "$model_file" ]; then
            echo "[entrypoint] Found model: $model_file"
            ln -sf "$model_file" "/opt/raaqib/$(basename $model_file)"
        fi
    done
fi

# ── Start Streamlit Dashboard in background (optional) ──
if [ "${ENABLE_DASHBOARD:-false}" = "true" ]; then
    echo "[entrypoint] Starting Streamlit Dashboard on port 8501..."
    streamlit run dashboard.py \
        --server.port 8501 \
        --server.address 0.0.0.0 \
        --server.headless true \
        --browser.gatherUsageStats false \
        &
fi

# ── Start main Raaqib NVR ──
echo "[entrypoint] Starting Raaqib NVR..."
exec python app.py /opt/raaqib/config.yaml
