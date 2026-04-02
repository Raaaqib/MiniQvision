# ⬡ RAAQIB NVR

> A self-hosted AI-powered Network Video Recorder with intelligent two-stage detection

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?style=flat-square)](https://fastapi.tiangolo.com)
[![YOLO](https://img.shields.io/badge/YOLO-Ultralytics-red?style=flat-square)](https://ultralytics.com)
[![ONNX](https://img.shields.io/badge/ONNX-Runtime-orange?style=flat-square)](https://onnxruntime.ai/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

## Table of Contents

- [What is Raaqib?](#what-is-raaqib)
- [Features](#features)
- [Quick Start](#quick-start)
- [Installation Guide](#installation-guide)
- [Running the System](#running-the-system)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Performance Tuning](#performance-tuning)
- [Integration Examples](#integration-examples)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Support](#support)

---

## What is Raaqib?

**Raaqib** is a self-hosted Network Video Recorder (NVR) designed for **local privacy** and **efficiency**. It processes video from multiple cameras using an intelligent **two-stage detection pipeline**:

### Two-Stage Pipeline

1. **Stage 1 — Motion Detection** (OpenCV MOG2)
   - Runs on every frame
   - Zero GPU cost
   - Detects any motion in the video

2. **Stage 2 — Object Identification** (YOLO 11)
   - Only activates when motion is detected
   - Uses GPU/TPU for inference
   - Identifies what object is moving (person, car, dog, etc.)

**Result**: Your GPU only works when something is actually moving — not 24/7.

---

## Features

✅ **Multi-camera support** — RTSP streams and USB webcams  
✅ **Smart two-stage pipeline** — Motion detection + AI classification  
✅ **Persistent object tracking** — Centroid-based tracker with unique IDs  
✅ **Intelligent recording** — Clips with configurable pre/post-capture buffer  
✅ **Snapshot saving** — High-quality snapshots on every detection  
✅ **REST API** — FastAPI with comprehensive endpoints  
✅ **MQTT integration** — Publish to Home Assistant, Node-RED, etc.  
✅ **Event database** — SQLite with retention policies  
✅ **Web dashboard** — Real-time monitoring (no framework bloat)  
✅ **Edge TPU support** — Optional Google Coral acceleration  
✅ **ONNX inference** — ~50MB model vs 2GB PyTorch  
✅ **Hardware acceleration** — CUDA, MPS, TPU support  
✅ **Configurable zones** — Detection regions per camera  

---

## Quick Start

### Prerequisites

- **Python 3.10+** - [Download](https://www.python.org/downloads/)
- **FFmpeg** - [Download](https://ffmpeg.org/download.html) (ensure in PATH)

### Installation Steps (Cross-Platform)

#### 1. Create Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux (Bash/Zsh):**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### 2. Upgrade pip and Install Dependencies

```bash
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

#### 3. Download YOLO Model

**Windows (PowerShell):**
```powershell
if (!(Test-Path models)) { mkdir models }
if (!(Test-Path models/yolo11n.onnx)) {
    Invoke-WebRequest -Uri "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.onnx" -OutFile "models/yolo11n.onnx"
}
```

**macOS / Linux:**
```bash
mkdir -p models
if [ ! -f models/yolo11n.onnx ]; then
    curl -L -o models/yolo11n.onnx "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.onnx"
fi
```

#### 4. Create Configuration File

Copy the template and customize:
```bash
cp src/config/config.yaml config_local.yaml
```

Edit `config_local.yaml` with your camera settings (see [Configuration](#configuration) section below).

#### 5. Start the Application

```bash
python app.py config_local.yaml
```

### Quick Run Script (Unix/macOS)

Alternatively, use the automated setup script:

```bash
chmod +x quickrun.sh
./quickrun.sh
```

**Access the API**: http://localhost:8000/docs

---

## Installation Guide

### System Requirements

| Item | Requirement |
|------|-------------|
| **Python** | 3.10 or newer |
| **FFmpeg** | 4.4+ (with libx264, libx265) |
| **RAM** | 2GB minimum (4GB+ with GPU) |
| **Storage** | Variable (recording dependent) |

### Supported Platforms

- 🐧 **Linux** (Ubuntu 20.04+, Debian 11+)
- 🍎 **macOS** (Intel & Apple Silicon)
- 🪟 **Windows** (10/11 with PowerShell)

### Optional Hardware

- **NVIDIA GPU**: CUDA 11.8+ support
- **Apple Silicon**: Metal Performance Shaders
- **Google Coral TPU**: ARM/Raspberry Pi support

---

## Running the System

### Start

```bash
python app.py config_local.yaml
```

### Stop

Press **Ctrl+C** in the terminal. Graceful shutdown in ~5 seconds.

---

## Configuration

### Getting Started with Configuration

1. **Copy the default template:**
   ```bash
   cp src/config/config.yaml config_local.yaml
   ```

2. **Edit `config_local.yaml` with your settings:**

   ```yaml
   # Cameras
   cameras:
     - id: front_door
       name: "Front Door"
       source: "rtsp://admin:pass@192.168.1.100:554/stream"
       # or for USB webcam: "0" (device index)
       enabled: true
       fps_target: 10
       width: 1280
       height: 720

   # Detection
   detection:
     model_path: "models/yolo11n.onnx"
     confidence_threshold: 0.45
     device: "cpu"  # Options: cpu | cuda | mps | tpu

   # Recording
   recording:
     enabled: true
     pre_capture_seconds: 3
     post_capture_seconds: 8
     max_clip_seconds: 60

   # MQTT (optional)
   mqtt:
     enabled: false
     broker: "127.0.0.1"
     port: 1883
   ```

3. **Start with your config:**
   ```bash
   python app.py config_local.yaml
   ```

---

## API Documentation

### Interactive Docs

Open: http://localhost:8000/docs

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/status | System health |
| GET | /api/cameras | Camera states |
| GET | /api/events | Event history |
| GET | /api/recordings | Video clips |
| GET | /api/snapshots | Snapshots |

---

## Project Structure

```
Raaqib/
├── app.py                    # Entry point
├── config_local.yaml         # Configuration (create from template)
├── requirements.txt          # Dependencies
├── quickrun.sh              # Quick start script
│
├── src/
│   ├── api/
│   │   └── app.py           # FastAPI routes
│   ├── core/
│   │   ├── config.py        # Config parsing
│   │   ├── database.py      # SQLite
│   │   ├── mqtt.py          # MQTT
│   │   ├── camera/          # Camera capture
│   │   ├── motion/          # Motion detection
│   │   ├── detectors/       # Object detection
│   │   ├── record/          # Recording
│   │   └── events/          # Event handling
│   ├── bin/                 # Utilities
│   ├── web/                 # Dashboard
│   └── config/              # Config templates
│       └── config.yaml      # Default configuration template
│
├── models/                   # AI models (create if not exists)
│   └── yolo11n.onnx        # YOLO 11 Nano model
├── recordings/              # Video clips (auto-created)
├── snapshots/               # Snapshots (auto-created)
├── logs/                    # Logs (auto-created)
│
└── docs/                    # Documentation
    ├── DOCUMENTATION.md
    ├── API.md
    ├── ARCHITECTURE.md
    ├── GETTING_STARTED.md
    └── CONTRIBUTING.md
```

---

## Architecture

### Multiprocessing Model

```
Main Process
├─ Camera Processes (per camera)
├─ Motion Detection (per camera)
├─ Object Detection (pooled workers)
├─ Event Processor
├─ Recorder
├─ FastAPI Server
└─ Database Writer
```

### Detection Pipeline

1. **Motion Detection** (every frame, CPU)
2. **Object Detection** (YOLO, on motion, GPU/TPU)
3. **Event Publishing** (MQTT, DB, recording)

---

## Performance Tuning

### CPU-Only

```yaml
detection:
  device: "cpu"
  model_path: "models/yolo11n.onnx"

cameras:
  - fps_target: 5
    width: 640
    height: 480
```

### GPU (NVIDIA CUDA)

```yaml
detection:
  device: "cuda"

cameras:
  - fps_target: 15
    width: 1280
    height: 720
```

### Edge TPU

```yaml
detection:
  device: "tpu"
  model_path: "models/yolo11n_edge_tpu.tflite"
```

---

## Integration Examples

### Home Assistant + MQTT

```yaml
mqtt:
  enabled: true
  broker: "192.168.1.100"
  port: 1883
```

Topics:
- `raaqib/{camera_id}/detection`
- `raaqib/{camera_id}/motion`

### Node-RED

Use REST API: http://localhost:8000/api/events

---

## Development

```bash
git clone https://github.com/belliliabdelaziz/Raaqib.git
cd Raaqib
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pytest black flake8

pytest tests/
black src/
```

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for contribution guidelines.

---

## Troubleshooting

### System Won't Start

```bash
python --version          # Must be 3.10+
ffmpeg -version          # Verify installed
ls -la models/yolo11n.onnx
tail -f logs/app.log     # Check errors
```

### Camera Issues

```bash
ffmpeg -rtsp_transport tcp -i "rtsp://..." -t 5 -f null -
```

### Poor Detection

1. Lower FPS: `fps_target: 5`
2. Reduce resolution: `width: 640`
3. Adjust confidence: `confidence_threshold: 0.5`

### High CPU

- Reduce cameras/FPS
- Lower resolution
- Use GPU if available

---

## License

MIT License — Free and open source.

---

## Support & Community

- **Issues**: https://github.com/belliliabdelaziz/Raaqib/issues
- **Docs**: [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md)

Made with ❤️ for privacy-first, self-hosted surveillance.
