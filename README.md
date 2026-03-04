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
- [Troubleshooting](#troubleshooting)

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
✅ **Configurable zones** — Detection regions per camera  
✅ **Dual-stream support** — Separate detection and recording streams  

---

## Quick Start

**⚠️ For detailed setup instructions, see [INSTALLATION.md](INSTALLATION.md)**

```bash
# 1. Clone the repository
git clone https://github.com/Raaaqib/MiniQvision
cd MiniQvision/Raaqib

# 2. Install Python 3.10+ and FFmpeg
# See INSTALLATION.md for platform-specific instructions

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Configure your cameras
cp config/config.yaml.example config/config.yaml
nano config/config.yaml  # Edit with your cameras

# 5. Run the system
python app.py

# 6. Access the dashboard
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## Installation Guide

**For complete installation instructions with system prerequisites, see [INSTALLATION.md](INSTALLATION.md)**

### Quick Reference

- **Python**: 3.10 or newer
- **FFmpeg**: 4.4 or newer
- **RAM**: 2GB minimum (4GB+ recommended with GPU)
- **Storage**: Depends on recording retention policy

### Supported Platforms

- 🐧 Linux (Ubuntu 20.04+, Debian 11+)
- 🍎 macOS (Intel & Apple Silicon)
- 🪟 Windows 10/11

---

## Running the System

**For comprehensive startup/shutdown instructions, see [RUNNING.md](RUNNING.md)**

### Start Raaqib

```bash
python app.py
```

### Stop Raaqib

```bash
# Press Ctrl+C in the terminal running app.py
# Or use the process killer script:
python kill_processes.py
```

All processes will gracefully shutdown within ~5 seconds.

---

## Configuration

Edit `config/config.yaml` to configure your cameras:

```yaml
# Example camera configuration
cameras:
  - id: front_door
    name: "Front Door Camera"
    source: "rtsp://admin:password@192.168.1.100:554/stream1"
    enabled: true
    fps_target: 10
    width: 1280
    height: 720
    
  - id: garage
    name: "USB Webcam"
    source: 0  # USB device index
    enabled: false
    fps_target: 5

detection:
  model: "yolo11n.pt"     # nano, small, medium, large
  confidence: 0.45
  device: "cpu"            # cpu, cuda, mps, tpu
  pool_size: 2

recording:
  enabled: true
  pre_capture_s: 3
  post_capture_s: 8
  max_clip_s: 60
```

**For full configuration reference, see [CONFIGURATION.md](CONFIGURATION.md)**

---

## API Documentation

Raaqib provides a comprehensive REST API for integration with other systems.

**Full API docs: [API.md](API.md)**

### Key Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/status` | System health & stats |
| GET | `/api/cameras` | All camera states |
| GET | `/api/events` | Event history |
| GET | `/api/recordings` | List video clips |
| GET | `/api/snapshots` | List detection snapshots |
| GET | `/docs` | Interactive Swagger UI |

**Live API documentation**: `http://localhost:8000/docs`

---

## Project Structure

```
Raaqib-Docker/
│
├── app.py                    # Main entry point (spawns all processes)
├── config.py                 # Config parsing & validation
├── const.py                  # Constants & defaults
├── config.yaml               # Your configuration file
├── requirements.txt          # Python dependencies
│
├── camera/                   # Camera capture module
│   ├── camera.py             # Data models
│   ├── capture.py            # Frame capture process
│   └── ffmpeg.py             # FFmpeg reader/writer
│
├── motion/                   # Motion detection module
│   └── motion.py             # MOG2 background subtraction
│
├── detectors/                # Object detection module
│   ├── base.py               # Abstract interface
│   ├── cpu.py                # YOLO CPU/GPU inference
│   ├── edgetpu.py            # Google Coral TPU
│   └── pool.py               # Detection worker pool
│
├── object_processing.py      # Centroid tracking
├── events/                   # Event pipeline
│   └── event_processor.py    # Event lifecycle management
│
├── record/                   # Recording module
│   └── recording.py          # FFmpeg clip writing
│
├── api/                      # REST API module
│   └── app.py                # FastAPI application
│
├── mqtt.py                   # MQTT publisher
├── database.py               # SQLite interface
├── storage.py                # File retention manager
│
├── web/                      # Web dashboard
│   ├── index.html            # UI
│   ├── style.css             # Styling
│   └── app.js                # Client logic
│
├── models/                   # AI models directory
│   └── yolo11n.onnx          # Pre-downloaded YOLO model
│
├── recordings/               # Video clips (auto-created)
├── snapshots/                # Detection snapshots (auto-created)
└── logs/                     # Application logs (auto-created)
```

---

## Architecture

**For detailed architecture and process flow documentation, see [ARCHITECTURE.md](ARCHITECTURE.md)**

### Process Architecture

Raaqib uses **multiprocessing** for parallel processing of video streams:

```
┌─────────────────────────────────────────────────────────┐
│                     Main Process                         │
│  - Spawns all child processes                          │
│  - Manages IPC queues and shared state                │
│  - Runs FastAPI server (threaded)                     │
│  - Handles graceful shutdown                          │
└─────────────────────────────────────────────────────────┘
         │         │           │         │
         ├─────────┼───────────┼────────┤
         │         │           │        │
    ┌────▼─┐ ┌────▼──┐ ┌─────▼──┐ ┌──▼────┐
    │Camera│ │Motion │ │Detector│ │Tracker│
    │(x n) │ │(x n)  │ │(pool)  │ │       │
    └──────┘ └───────┘ └────────┘ └───────┘
         │
    ┌────▼─────┬─────────┬──────────┐
    │           │         │          │
┌───▼──┐  ┌───▼──┐  ┌───▼──┐  ┌───▼──┐
│Record│  │Event │  │MQTT  │  │DB    │
│      │  │Proc  │  │Pub   │  │Write │
└──────┘  └──────┘  └──────┘  └──────┘
```

---

## Troubleshooting

### System won't start
1. Check Python version: `python --version` (must be 3.10+)
2. Verify FFmpeg: `ffmpeg -version`
3. Check camera connectivity: `ffmpeg -rtsp_transport tcp -i "rtsp://your-camera-url" -t 5 -f null -`
4. Review logs in `logs/` directory

### Poor detection performance
1. Adjust detection FPS lower in config
2. Try a different YOLO model (nano → small → medium)
3. Enable dual-stream if using high-resolution cameras
4. Check GPU usage: `nvidia-smi` (CUDA) or `powermetrics` (macOS)

### FFmpeg streaming issues
1. Verify camera credentials
2. Check camera RTSP URL format
3. Try with `-rtsp_transport tcp` flag
4. Review ffmpeg.py logs

### High CPU usage
1. Reduce frame resolution in config
2. Lower FPS target (fps_target: 5-10)
3. Increase Motion Cooldown (MOTION_COOLDOWN_S in const.py)

---

## MQTT Integration

Publish events to Home Assistant or Node-RED:

```yaml
mqtt:
  enabled: true
  broker: "127.0.0.1"
  port: 1883
  username: "mqtt_user"
  password: "mqtt_pass"
```

### Topics

- `raaqib/{camera_id}/detection` — Object detected
- `raaqib/{camera_id}/motion` — Motion detected
- `raaqib/{camera_id}/recording` — Recording started/stopped
- `raaqib/status` — System status updates

---

## Performance Tuning

### For Low-End Hardware (CPU-only)

```yaml
detection:
  model: "yolo11n.pt"        # Use nano model
  device: "cpu"
  pool_size: 1               # Single detector

cameras:
  - id: cam1
    fps_target: 5            # Lower FPS
    width: 640               # Lower resolution
    height: 480
```

### For High-End Hardware (GPU)

```yaml
detection:
  model: "yolo11l.pt"        # Use large model
  device: "cuda"
  pool_size: 4

cameras:
  - id: cam1
    fps_target: 30           # Higher FPS
    width: 1920
    height: 1080
    detect_width: 640        # Dual-stream optimization
    detect_height: 480
```

---

## License

MIT License — See [LICENSE](LICENSE) for details.

---

## Support & Contributing

- 📖 [Documentation](DOCUMENTATION.md)
- 🐛 [Bug Reports](https://github.com/yourname/raaqib-nvr/issues)
- 🤝 [Contributions Welcome](CONTRIBUTING.md)

**Made with ❤️ for privacy-first surveillance**

API docs available at: `http://localhost:8000/docs`

---

## Project Structure

```
Raaqib/
│
├── app.py                  Main entry point — spawns all processes
├── config.py               Config parsing & validation
├── const.py                Constants & defaults
├── config.yaml             Your configuration file
│
├── camera/
│   ├── camera.py           Camera state & data models (FramePacket, DetectionResult)
│   ├── capture.py          Frame capture process (per camera)
│   └── ffmpeg.py           FFmpeg reader & writer wrappers
│
├── motion/
│   └── motion.py           MOG2 background subtraction (per camera)
│
├── detectors/
│   ├── base.py             Abstract detector interface
│   ├── cpu.py              YOLO via Ultralytics (CPU/GPU/MPS)
│   ├── edgetpu.py          Google Coral TPU support
│   └── pool.py             Detection worker pool process
│
├── object_processing.py    Centroid tracker — persistent object IDs
│
├── events/
│   └── event_processor.py  Event lifecycle (start → update → end)
│
├── record/
│   └── recording.py        FFmpeg clip recording with pre-buffer
│
├── api/
│   └── app.py              FastAPI REST API
│
├── mqtt.py                 MQTT publisher (paho-mqtt)
├── database.py             SQLite interface + writer process
├── storage.py              File retention & cleanup
│
└── web/
    ├── index.html          Dashboard UI
    ├── style.css           Stylesheet
    └── app.js              Dashboard logic
```

---

## Configuration Reference

See [DOCUMENTATION.md](DOCUMENTATION.md) for full config reference.

---

## YOLO Models

Models are downloaded automatically from Ultralytics on first run.

| Model     | Speed    | Accuracy | Best For         |
|-----------|----------|----------|------------------|
| yolo11n   | ⚡⚡⚡⚡  | ★★★      | CPU / edge       |
| yolo11s   | ⚡⚡⚡   | ★★★★     | CPU with GPU     |
| yolo11m   | ⚡⚡     | ★★★★★    | Dedicated GPU    |
| yolo11l   | ⚡       | ★★★★★+   | High-end GPU     |

---

## API Endpoints

| Method | Endpoint                    | Description              |
|--------|-----------------------------|--------------------------|
| GET    | `/api/status`               | System & camera status   |
| GET    | `/api/cameras`              | All camera states        |
| GET    | `/api/cameras/{id}`         | Single camera state      |
| GET    | `/api/events`               | Event history            |
| GET    | `/api/events/active`        | Currently active events  |
| GET    | `/api/recordings`           | List recordings          |
| GET    | `/api/recordings/{file}`    | Download a clip          |
| GET    | `/api/snapshots`            | List snapshots           |
| GET    | `/api/snapshots/{file}`     | Get a snapshot image     |
| GET    | `/api/stats`                | Detection statistics     |

---

## MQTT Topics

| Topic                            | Trigger              |
|----------------------------------|----------------------|
| `raaqib/{camera_id}/detection`   | Object detected      |
| `raaqib/{camera_id}/motion`      | Motion detected      |
| `raaqib/{camera_id}/recording`   | Recording started    |
| `raaqib/status`                  | System status        |

---

## License

MIT — do whatever you want with it.
