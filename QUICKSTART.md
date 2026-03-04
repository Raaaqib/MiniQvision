# RAAQIB NVR — Quick Start Guide

Get Raaqib up and running in 5 minutes.

## Step 1: Install Prerequisites (5 minutes)

### macOS

```bash
brew install python@3.10 ffmpeg git
```

### Ubuntu/Debian

```bash
sudo apt update
sudo apt install python3.10 python3-pip ffmpeg git -y
```

### Windows

1. Download Python 3.10+ from [python.org](https://www.python.org/downloads/)
2. Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
3. Download Git from [git-scm.com](https://git-scm.com/)

---

## Step 2: Clone & Setup (2 minutes)

```bash
# Clone repository
git clone https://github.com/yourname/raaqib-nvr.git
cd raaqib-nvr/Raaqib-Docker

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate          # macOS/Linux
# or
.\venv\Scripts\Activate.ps1       # Windows PowerShell

# Install dependencies
pip install -r requirements.txt
```

---

## Step 3: Configure (2 minutes)

### Edit `config/config.yaml`:

**For USB Webcam** (easiest):
```yaml
cameras:
  - id: "camera1"
    name: "My Camera"
    source: 0          # USB camera index
    enabled: true

detection:
  model: "yolo11n.pt"
  device: "cpu"
```

**For IP Camera** (typical):
```yaml
cameras:
  - id: "front_door"
    name: "Front Door"
    source: "rtsp://admin:password@192.168.1.100:554/stream1"
    enabled: true
    fps_target: 10

detection:
  model: "yolo11n.pt"
  device: "cpu"
```

**For Multiple Cameras**:
```yaml
cameras:
  - id: "cam1"
    name: "Camera 1"
    source: "rtsp://admin:password@192.168.1.100:554/stream1"
    enabled: true
  
  - id: "cam2"
    name: "Camera 2"
    source: "rtsp://admin:password@192.168.1.101:554/stream1"
    enabled: true

detection:
  pool_size: 2       # 2 workers for 2 cameras
```

---

## Step 4: Run (1 minute)

```bash
python app.py
```

You should see:
```
============================================================
  RAAQIB NVR — Starting
  Cameras: 1
  Model:   yolo11n.pt
  Device:  cpu
  API:     http://0.0.0.0:8000
============================================================
Started process: capture:camera1 (PID xxxxx)
Started process: motion:camera1 (PID xxxxx)
...
API server started on http://0.0.0.0:8000
All processes started. Press Ctrl+C to stop.
```

---

## Step 5: Use It

### Check Status

```bash
curl http://localhost:8000/api/status
```

### View Dashboard

Open browser:
```
http://localhost:8000/docs
```

### Stop (Press Ctrl+C)

```bash
Ctrl+C
```

Raaqib will gracefully shutdown in ~5 seconds.

---

## Next Steps

- **Troubleshooting**: See [RUNNING.md - Troubleshooting](RUNNING.md#troubleshooting)
- **Advanced Config**: See [CONFIGURATION.md](CONFIGURATION.md)
- **API Integration**: See [API.md](API.md)
- **Full Installation**: See [INSTALLATION.md](INSTALLATION.md)

---

## Common Issues

### Camera Not Found
```bash
# Test camera URL
ffmpeg -rtsp_transport tcp -i "rtsp://admin:pass@192.168.1.100:554/stream1" -t 5 -f null -
```

### Port Already in Use
```yaml
api:
  port: 8001  # Change port
```

### Missing FFmpeg
```bash
# macOS
brew install ffmpeg

# Linux
sudo apt install ffmpeg

# Windows - Restart terminal after installing
```

---

## Performance Tips

**Slow system?**
1. Reduce `fps_target` (10 → 5)
2. Reduce resolution (1280×720 → 640×480)
3. Use nano model: `model: "yolo11n.pt"`
4. Disable recording: `enabled: false`

**GPU available?**
```yaml
detection:
  device: "cuda"        # NVIDIA
  model: "yolo11m.pt"   # Use larger model
  pool_size: 4          # More workers
```

---

## Full Documentation

| Guide | Purpose |
|-------|---------|
| [README.md](README.md) | Overview & features |
| [INSTALLATION.md](INSTALLATION.md) | Detailed setup |
| [RUNNING.md](RUNNING.md) | Running & managing |
| [CONFIGURATION.md](CONFIGURATION.md) | All config options |
| [API.md](API.md) | API reference |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design |

---

## Support

- 📖 Check [README.md](README.md)
- 🐛 Open GitHub issue
- 💬 Start discussion
- 🤝 See [CONTRIBUTING.md](CONTRIBUTING.md)

---

**Ready?** Run `python app.py` and detect some objects! 🎥
