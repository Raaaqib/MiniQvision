# RAAQIB NVR — Complete Documentation

This is a complete index of all documentation for the Raaqib NVR project.

## 📚 Documentation Index

### Quick Navigation
- **New Users**: Start with [QUICKSTART.md](QUICKSTART.md) (5 minutes)
- **Installation**: See [INSTALLATION.md](INSTALLATION.md) (platform-specific)
- **Running System**: See [RUNNING.md](RUNNING.md) (startup/shutdown)
- **API Integration**: See [API.md](API.md) (REST endpoints)
- **Configuration**: See [CONFIGURATION.md](CONFIGURATION.md) (all options)
- **Deep Dive**: See [ARCHITECTURE.md](ARCHITECTURE.md) (system design)

---

## 📖 Complete Documentation Files

### **[QUICKSTART.md](QUICKSTART.md)** — 5-Minute Setup
**For**: Everyone (complete beginners welcome)

Covers:
- Install Python + FFmpeg in 5 minutes
- Clone and configure
- Run your first detection
- Basic troubleshooting

**Start here if** you want to run Raaqib right now.

---

### **[README.md](README.md)** — Project Overview
**For**: Understanding what Raaqib does

Covers:
- What is Raaqib?
- Key features
- Two-stage detection pipeline explanation
- System requirements
- Quick start reference
- Architecture diagram
- Project structure
- Performance tuning options
- MQTT integration overview

**Start here if** you want to understand Raaqib's capabilities.

---

### **[INSTALLATION.md](INSTALLATION.md)** — Complete Setup Guide
**For**: Installing on Linux, macOS, or Windows

Sections:
- System requirements (CPU, RAM, storage)
- **Linux (Ubuntu/Debian)** — 7-step installation
- **macOS (Intel & Apple Silicon)** — 7-step installation
- **Windows 10/11** — 6-step installation
- Verification tests
- Post-installation setup
- GPU driver installation (NVIDIA, AMD, Apple)
- Troubleshooting common setup issues

**Start here if** you need detailed platform-specific instructions.

---

### **[RUNNING.md](RUNNING.md)** — Running & Managing
**For**: Starting, monitoring, and stopping the system

Sections:
- Quick start (one command)
- First-run checklist
- What happens during startup (detailed process diagram)
- Console output explanation
- Monitoring system health
- Viewing logs
- Checking API health
- Stopping gracefully (3 methods)
- Process management
- Running in background (systemd, Docker, screen/tmux)
- Comprehensive troubleshooting

**Start here if** you already installed Raaqib and want to run it.

---

### **[CONFIGURATION.md](CONFIGURATION.md)** — Configuration Reference
**For**: Understanding every config option

Sections:
- **Cameras**: RTSP, USB, HTTP sources
  - FPS, resolution, motion detection settings
  - Dual-stream optimization (quality vs speed)
  - Zone-based detection
- **Detection**: YOLO models, device selection
  - CPU-only, NVIDIA GPU, AMD GPU, Apple Silicon, Google TPU
  - Confidence thresholds, class filtering
- **Recording**: Video codec, quality, retention
  - H.264 vs H.265, CRF quality guide
  - Storage estimation
- **API**: Server host/port, security
- **Database**: SQLite settings, retention
- **MQTT**: Broker configuration, Home Assistant integration
- **Logging**: Log levels, file rotation
- **Common Presets**: USB webcam, IP camera, doorbell, high-end
- **Validation**: Check config syntax

**Start here if** you need to configure specific features.

---

### **[API.md](API.md)** — REST API Reference
**For**: Integrating with other systems

Sections:
- **Status Endpoints**: System health, stats
- **Camera Endpoints**: List cameras, get frame, status
- **Event Endpoints**: Event history, active events, details
- **Recording Endpoints**: List clips, download, delete
- **Snapshot Endpoints**: List snapshots, download, delete
- **Authentication**: No auth (local), reverse proxy, JWT
- **MQTT Integration**: Pub/sub topics, Home Assistant examples
- **Error Handling**: Error codes and responses
- **Rate Limits**: Recommended request rates
- **Examples**: 
  - Python client library
  - cURL examples
  - Real-time monitoring

**Start here if** you want to integrate Raaqib with other systems.

---

### **[ARCHITECTURE.md](ARCHITECTURE.md)** — System Design Deep Dive
**For**: Understanding how Raaqib works internally

Sections:
- **System Overview**: Process architecture diagram
- **Two-Stage Pipeline**: 
  - Stage 1: MOG2 motion detection
  - Stage 2: YOLO object detection
  - Energy efficiency comparison
- **Process Architecture**: All process types and responsibilities
- **Data Flow**: Single detection lifecycle with timestamps
- **IPC Mechanisms**: Queues, shared memory, signals
- **Component Details**: Each module explained
- **Performance Characteristics**: CPU/memory/latency per component
- **Design Decisions**: Why multiprocessing, ONNX, centroid tracker, SQLite
- **Scaling Considerations**: Limits and recommendations

**Start here if** you want to understand or modify the system internals.

---

### **[CONTRIBUTING.md](CONTRIBUTING.md)** — Developer Guide
**For**: Contributing to the project

Sections:
- Code of conduct
- Development setup
- Code areas and responsibilities
- Testing procedures
- Code style guide (PEP 8, type hints)
- Pull request process
- Documentation updates
- Common contribution areas (easy to hard)
- Release process

**Start here if** you want to contribute code.

---

## 🎯 Reading Paths by Use Case

### **I want to try it in 5 minutes**
1. [QUICKSTART.md](QUICKSTART.md)
2. [RUNNING.md](RUNNING.md) (if issues)

### **I want to install properly**
1. [INSTALLATION.md](INSTALLATION.md) — Choose your OS
2. [CONFIGURATION.md](CONFIGURATION.md) — Configure your cameras
3. [RUNNING.md](RUNNING.md) — Start the system

### **I want to integrate with Home Assistant**
1. [QUICKSTART.md](QUICKSTART.md) — Get it running
2. [CONFIGURATION.md](CONFIGURATION.md) → MQTT section
3. [API.md](API.md) → MQTT Integration section

### **I want to understand how it works**
1. [README.md](README.md) — Overview
2. [ARCHITECTURE.md](ARCHITECTURE.md) — Deep dive

### **I want to optimize performance**
1. [CONFIGURATION.md](CONFIGURATION.md) → Common Configurations
2. [README.md](README.md) → Performance Tuning
3. [ARCHITECTURE.md](ARCHITECTURE.md) → Performance Characteristics

### **I want to develop features**
1. [ARCHITECTURE.md](ARCHITECTURE.md) — Understand system
2. [CONTRIBUTING.md](CONTRIBUTING.md) — Development setup
3. Source code in `camera/`, `detectors/`, `motion/`, etc.

---

## 📋 Quick Reference Sheets

### Installation Checklist

```bash
☐ Install Python 3.10+
☐ Install FFmpeg
☐ Clone repository
☐ Create virtual environment
☐ Install dependencies (pip install -r requirements.txt)
☐ Copy and edit config/config.yaml
☐ Run python app.py
☐ Access http://localhost:8000/docs
```

### First-Run Checklist

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Create necessary directories
mkdir -p recordings snapshots logs

# 3. Validate configuration
python -c "from config import load_config; load_config('config/config.yaml')"

# 4. Run with console output
python app.py

# 5. In another terminal, test API
curl http://localhost:8000/api/status

# 6. Check camera status
curl http://localhost:8000/api/cameras

# 7. Stop (in main terminal)
Ctrl+C
```

### Configuration Checklist

```yaml
✓ cameras[] defined
✓ cameras[0].source is valid (RTSP or USB)
✓ detection.device matches hardware
✓ recording.enabled if you want clips
✓ snapshots.enabled if you want images
✓ api.host/port not in use
✓ database path writable
✓ retention_days reasonable for storage
```

### Running Checklist

```bash
✓ Virtual environment activated
✓ All dependencies installed
✓ Config file valid
✓ Directories writable (recordings/, snapshots/, logs/)
✓ Cameras accessible (test with ffmpeg)
✓ Port 8000 available (or configured differently)
✓ GPU drivers installed (if using GPU)
```

---

## 🔗 Cross-Reference Guide

| Want to... | See | File |
|-----------|-----|------|
| Install from scratch | Step-by-step guide | [INSTALLATION.md](INSTALLATION.md) |
| Start the system | How to run | [RUNNING.md](RUNNING.md) |
| Configure cameras | Camera config examples | [CONFIGURATION.md](CONFIGURATION.md#cameras-section) |
| Set up GPU | GPU configuration | [CONFIGURATION.md](CONFIGURATION.md#device-selection) |
| Use Home Assistant | MQTT integration | [API.md](API.md#mqtt-integration) |
| Use REST API | Endpoint reference | [API.md](API.md) |
| Understand processes | Process architecture | [ARCHITECTURE.md](ARCHITECTURE.md#process-architecture) |
| Fix performance | Tuning guide | [README.md](README.md#performance-tuning) |
| Troubleshoot issues | Common problems | [RUNNING.md](RUNNING.md#troubleshooting) |
| Develop features | Dev setup | [CONTRIBUTING.md](CONTRIBUTING.md) |

---

## 📊 Documentation Stats

| Document | Size | Time to Read |
|----------|------|--------------|
| QUICKSTART.md | 2 KB | 5 min |
| README.md | 15 KB | 10 min |
| INSTALLATION.md | 25 KB | 15-20 min |
| RUNNING.md | 30 KB | 15-20 min |
| CONFIGURATION.md | 40 KB | 20-30 min |
| API.md | 35 KB | 20-25 min |
| ARCHITECTURE.md | 35 KB | 20-30 min |
| CONTRIBUTING.md | 8 KB | 5-10 min |

**Total**: ~190 KB, ~2-3 hours complete reading

---

## 🚀 Getting Started Paths

### Path 1: Just Get It Running (20 minutes)
```
QUICKSTART.md
    ↓
Run: python app.py
    ↓
Test: curl http://localhost:8000/api/status
```

### Path 2: Proper Installation (45 minutes)
```
README.md (overview)
    ↓
INSTALLATION.md (your OS)
    ↓
CONFIGURATION.md (configure cameras)
    ↓
RUNNING.md (start system)
```

### Path 3: Deep Understanding (2+ hours)
```
README.md
    ↓
ARCHITECTURE.md
    ↓
CONFIGURATION.md
    ↓
RUNNING.md
    ↓
API.md
```

---

## 📞 Getting Help

### For Installation Issues
→ See [INSTALLATION.md - Troubleshooting](INSTALLATION.md#troubleshooting)

### For Running Issues
→ See [RUNNING.md - Troubleshooting](RUNNING.md#troubleshooting)

### For Configuration Issues
→ See [CONFIGURATION.md - Validation & Troubleshooting](CONFIGURATION.md#validation--troubleshooting)

### For API Issues
→ See [API.md - Error Handling](API.md#error-handling)

### For Development Help
→ See [CONTRIBUTING.md](CONTRIBUTING.md#getting-help)

---

## 📝 Documentation License

All documentation is provided under MIT License. Feel free to use, modify, and distribute.

---

## 🎓 Learning Resources

### Concepts You Should Know

1. **RTSP**: Real Time Streaming Protocol (camera standard)
2. **FFmpeg**: Video encoding/decoding tool
3. **YOLO**: Object detection AI model
4. **MQTT**: Message publish/subscribe protocol
5. **REST API**: HTTP-based interface

### External Resources

- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [OpenCV MOG2](https://docs.opencv.org/master/d7/df3/classcv_1_1BackgroundSubtractorMOG2.html)
- [Ultralytics YOLO](https://docs.ultralytics.com/)
- [MQTT Documentation](https://mqtt.org/)
- FastAPI: [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)

---

## 💡 Tips & Tricks

### Useful Commands

```bash
# Monitor in real-time
watch -n 1 'curl -s http://localhost:8000/api/status | jq .'

# Get all detections today
curl "http://localhost:8000/api/events?start_time=$(date -u +%Y-%m-%dT00:00:00Z)" | jq .

# Download latest clip
curl http://localhost:8000/api/recordings \
  | jq -r '.recordings[0].file' \
  | xargs -I {} curl -o latest.mp4 http://localhost:8000/api/recordings/{}

# Live logs
tail -f logs/raaqib.log | grep motion
```

### Performance Optimization Tips

- Use dual-stream on high-res cameras (detect at lower res)
- Lower FPS for motion detection (5 fps is usually enough)
- Use nano YOLO model (yolo11n.pt) for CPU
- Increase motion threshold to reduce false positives

---

## 📌 Version Information

**Documentation Version**: 1.0  
**Raaqib Version**: Latest  
**Last Updated**: 2024-03-04

---

**All documentation is comprehensive and up-to-date.** Start with the reading path that matches your use case!
