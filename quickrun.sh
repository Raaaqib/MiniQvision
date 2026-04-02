#!/usr/bin/env bash
# quickrun.sh — start Raaqib (backend + optional dashboard)
# Usage: ./quickrun.sh [config_local.yaml]

set -euo pipefail
CONFIG=${1:-config_local.yaml}
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# Kill any existing python runs
echo "Stopping existing Python processes..."
pkill -f "python app.py" || true
sleep 2

# Activate venv
if [ -f .venv/bin/activate ]; then
  echo "Activating .venv"
  # shellcheck source=/dev/null
  . .venv/bin/activate
else
  echo ".venv not found — creating one"
  python3 -m venv .venv
  . .venv/bin/activate
  pip install --upgrade pip setuptools wheel
  pip install -r requirements.txt || true
fi

# Ensure models dir and model file exists
mkdir -p models
if [ ! -f models/yolo11n.onnx ]; then
  echo "Downloading yolo11n.onnx to models/"
  if command -v curl >/dev/null 2>&1; then
    curl -L -o models/yolo11n.onnx "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.onnx"
  elif command -v wget >/dev/null 2>&1; then
    wget -O models/yolo11n.onnx "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.onnx"
  else
    echo "Please download models/yolo11n.onnx manually (curl or wget not found)" >&2
  fi
fi

# Start backend
LOGFILE="logs/raaqib.log"
mkdir -p logs
echo "Starting backend (app.py) — logs -> $LOGFILE"
nohup python app.py "$CONFIG" > "$LOGFILE" 2>&1 &
BACKEND_PID=$!
sleep 2

echo "Backend PID: $BACKEND_PID"

echo "Raaqib should be starting. Give it a few seconds, then open: http://localhost:8000/docs"

echo "To stop: kill $BACKEND_PID or use pkill -f 'python app.py'"
