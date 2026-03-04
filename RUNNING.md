# RAAQIB NVR — Running & Management Guide

Complete guide for starting, monitoring, and stopping Raaqib with detailed process descriptions.

## Table of Contents

- [Quick Start](#quick-start)
- [Running for the First Time](#running-for-the-first-time)
- [Detailed Startup Process](#detailed-startup-process)
- [Monitoring the System](#monitoring-the-system)
- [Stopping the System](#stopping-the-system)
- [Process Management](#process-management)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### The Simplest Way

```bash
# Navigate to project directory
cd Raaqib-Docker

# Activate virtual environment
source venv/bin/activate          # Linux/macOS
.\venv\Scripts\Activate.ps1       # Windows

# Run
python app.py

# To stop: Press Ctrl+C
```

That's it! All processes start automatically.

---

## Running for the First Time

### Checklist

- [ ] Install Python 3.10+ → [See INSTALLATION.md](INSTALLATION.md)
- [ ] Install FFmpeg → [See INSTALLATION.md](INSTALLATION.md)
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Configure cameras in `config/config.yaml`

### First Run Steps

```bash
# 1. Activate virtual environment
source venv/bin/activate          # Linux/macOS
.\venv\Scripts\Activate.ps1       # Windows (PowerShell)

# 2. Start with verbose logging
python app.py

# You should see:
# ============================================================
#   RAAQIB NVR — Starting
#   Cameras: 1
#   Model:   yolo11n.pt
#   Device:  cpu
#   API:     http://0.0.0.0:8000
# ============================================================
```

### Access the System

Once started, access these services:

| Service              | URL                          | Purpose          |
|----------------------|------------------------------|------------------|
| FastAPI Docs         | http://localhost:8000/docs   | API exploration  |
| REST API             | http://localhost:8000/api/   | Programmatic     |
| Status Check         | http://localhost:8000/api/status | Health check   |

---

## Detailed Startup Process

### What Happens When You Run `python app.py`

```
┌─────────────────────────────────────────────────────────────┐
│ 1. MAIN PROCESS STARTS                                      │
│    - Loads config.yaml                                      │
│    - Sets up logging                                        │
│    - Creates shared IPC queues and state                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────┴─────────────────┐
        │                                   │
┌───────▼──────────┐             ┌─────────▼─────────┐
│ PER-CAMERA       │             │ SHARED PROCESSES  │
│ PROCESSES        │             │                   │
│                  │             │                   │
├──────────────────┤             ├───────────────────┤
│ 1. Capture       │             │ 1. Detectors      │
│    - Opens video │             │    - YOLO workers │
│    - Read frames │             │    - Process queue│
│                  │             │                   │
│ 2. Motion        │             │ 2. Tracker        │
│    - MOG2        │             │    - Object ID    │
│    - Detect flow │             │    - Persistence  │
│                  │             │                   │
│ (repeats per cam)│             │ 3. Recorder       │
│                  │             │    - FFmpeg write │
│                  │             │    - Pre-capture  │
│                  │             │                   │
│                  │             │ 4. Events         │
│                  │             │    - Lifecycle    │
│                  │             │    - Database pub │
│                  │             │                   │
│                  │             │ 5. MQTT           │
│                  │             │    - Home Assist  │
│                  │             │    - Node-RED     │
│                  │             │                   │
│                  │             │ 6. Database       │
│                  │             │    - SQLite write │
│                  │             │    - Retention    │
│                  │             │                   │
│                  │             │ 7. FastAPI        │
│                  │             │    - REST server  │
│                  │             │    - Serve web UI │
└──────────────────┘             └───────────────────┘
```

### Console Output Explained

```
Main Process Starting...
Started process: capture:camera1 (PID 12345)      ← Frame capture
Started process: motion:camera1 (PID 12346)       ← Motion detection
Started process: detector:0 (PID 12347)           ← YOLO worker 1
Started process: detector:1 (PID 12348)           ← YOLO worker 2
Started process: tracker (PID 12349)              ← Object tracking
Started process: recorder (PID 12350)             ← Video recording
Started process: events (PID 12351)               ← Event processing
Started process: database (PID 12352)             ← Database writer
Started process: mqtt (PID 12353)                 ← MQTT publishing
API server started on http://0.0.0.0:8000         ← Web server
All processes started. Press Ctrl+C to stop.     ✓ READY
```

---

## Monitoring the System

### View System Health

```bash
# Check if system is running
curl http://localhost:8000/api/status

# Example response:
# {
#   "status": "running",
#   "cpu_percent": 15.2,
#   "memory_percent": 8.5,
#   "cameras": {
#     "camera1": {"status": "connected", "fps": 10, "detections": 5}
#   }
# }
```

### View Process Activity

#### Linux/macOS

```bash
# Monitor processes in real-time
top -p $(pgrep -f app.py -d ',')

# Or use htop (install: brew install htop / apt install htop)
htop

# View logs
tail -f logs/raaqib.log

# Watch for specific events
grep "detection\|motion" logs/raaqib.log
```

#### Windows

```powershell
# View Python processes
Get-Process python

# Monitor system resources (Task Manager alternative)
Get-Process | Select-Object Name, CPU, WorkingSet | Sort-Object -Property CPU -Descending

# View logs
Get-Content logs\raaqib.log -Tail 50 -Wait
```

### Check API Health

```bash
# Test API is responding
curl -s http://localhost:8000/api/status | python -m json.tool

# List all cameras
curl -s http://localhost:8000/api/cameras | python -m json.tool

# Get active events
curl -s http://localhost:8000/api/events/active | python -m json.tool
```

### Monitor Camera Feeds

```bash
# Check camera status via API
curl http://localhost:8000/api/cameras/camera1

# Expected response:
# {
#   "id": "camera1",
#   "name": "Front Door",
#   "source": "rtsp://192.168.1.100:554/stream1",
#   "connected": true,
#   "fps": 10,
#   "dropped_frames": 0,
#   "detections_count": 42
# }
```

---

## Stopping the System

### Method 1: Graceful Shutdown (Recommended)

In the terminal running Raaqib, press:

```bash
Ctrl+C
```

You should see:

```
Shutdown signal received...
Shutting down...
Stopping process: capture:camera1
Stopping process: motion:camera1
[... other processes ...]
✓ All processes stopped gracefully
Raaqib NVR stopped.
```

**Wait time**: 5-10 seconds for full shutdown.

### Method 2: Kill Script (Windows)

If Ctrl+C doesn't work, use the provided script:

```powershell
# Windows
python kill_processes.py

# Or
.\kill_processes.bat
```

### Method 3: Manual Process Termination

#### Linux/macOS

```bash
# Find main process
ps aux | grep app.py

# Kill main process (replace XXXX with PID)
kill -TERM XXXX

# Or kill all Python processes (careful!)
pkill -f "python app.py"
```

#### Windows

```powershell
# Find process
Get-Process python

# Kill process (replace XXXX with PID)
Stop-Process -Id XXXX -Force

# Or kill all raaqib processes
Stop-Process -Name python -Force
Get-Process | Where-Object {$_.ProcessName -like "*python*"} | Stop-Process -Force
```

### Verify Shutdown

```bash
# Linux/macOS
ps aux | grep app.py | grep -v grep

# Windows
Get-Process python

# If no processes shown, shutdown was successful
```

### Cleanup After Shutdown

```bash
# Check for orphaned processes
lsof -i :8000                    # Linux/macOS

# Delete old recordings (optional)
rm -rf recordings/*              # Keep only recent

# View logs of last run
tail -100 logs/raaqib.log
```

---

## Process Management

### Understanding the Process Tree

Each component runs as a separate process for isolation and stability:

```
Main Process (app.py) — PID: 12340
├─ Capture Process (camera1) — PID: 12345
├─ Motion Process (camera1) — PID: 12346
├─ Detector Worker 1 — PID: 12347
├─ Detector Worker 2 — PID: 12348
├─ Tracker Process — PID: 12349
├─ Recorder Process — PID: 12350
├─ Event Processor — PID: 12351
├─ Database Writer — PID: 12352
└─ MQTT Publisher — PID: 12353
```

### Restart Individual Process (if crashed)

If a single process crashes, Raaqib will NOT automatically restart it in the current version. You must restart the entire system:

```bash
# Stop everything
Ctrl+C

# Wait 5 seconds

# Start again
python app.py
```

### Monitor Process Memory

```bash
# Linux/macOS - memory per process
ps aux --sort=-%mem | grep python | head -10

# Windows PowerShell - memory usage
Get-Process python | Select-Object Name, @{Name="Mem(MB)";Expression={[math]::round($_.WorkingSet/1MB)}} | Sort-Object -Property "Mem(MB)" -Descending
```

### Process Recovery Notes

- **Graceful Shutdown**: All processes have ~5 seconds to clean up resources
- **Hard Kill**: May leave temporary files or locks (usually safe to ignore)
- **Restart After Crash**: Always wait 5 seconds before restarting

---

## Stopping Services in Different Environments

### Running in Background (systemd - Linux)

If you've set up systemd service:

```bash
# Stop the service
sudo systemctl stop raaqib

# Check status
sudo systemctl status raaqib

# View service logs
sudo journalctl -u raaqib -f
```

### Running in Screen/tmux Session

```bash
# Detach from session (Ctrl+A then D for screen, Ctrl+B then D for tmux)

# List sessions
screen -ls
tmux list-sessions

# Re-attach
screen -r raaqib
tmux attach-session -t raaqib

# Kill session
screen -X -S raaqib quit
tmux kill-session -t raaqib
```

### Running in Docker

```bash
# Stop container
docker compose down

# Stop and remove volumes
docker compose down -v

# View Docker logs
docker compose logs -f
```

---

## Troubleshooting

### System Won't Start

**Problem**: `ModuleNotFoundError: No module named 'cv2'`

**Solution**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\Activate.ps1  # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### API Not Responding

**Problem**: `curl: (7) Failed to connect to localhost port 8000`

**Solution**:
```bash
# Check if port 8000 is in use
lsof -i :8000  # Linux/macOS
netstat -ano | findstr :8000  # Windows

# If port in use, change in config.yaml:
# api:
#   port: 8001

# Or kill process using the port
kill -9 <PID>  # Linux/macOS
Stop-Process -Id <PID> -Force  # Windows
```

### Processes Stuck After Shutdown

**Problem**: `ps aux | grep app.py` still shows processes

**Solution**:
```bash
# Force kill all Python processes (careful!)
pkill -9 -f "python app.py"

# Wait 5 seconds, then verify
sleep 5
ps aux | grep app.py
```

### Out of Memory (OOM)

**Problem**: System hangs or kills process due to memory usage

**Solution**:
1. Reduce number of detector workers:
   ```yaml
   detection:
     pool_size: 1  # From 2 to 1
   ```

2. Reduce camera resolution:
   ```yaml
   cameras:
     - id: camera1
       width: 640    # From 1280
       height: 480   # From 720
   ```

3. Lower FPS target:
   ```yaml
   cameras:
     - id: camera1
       fps_target: 5  # From 10
   ```

### High CPU Usage

**Problem**: CPU at 90-100% even with no motion

**Solution**:
1. Lower motion detection FPS in `const.py`:
   ```python
   MOTION_COOLDOWN_S = 0.5  # Increase from 0.2
   ```

2. Reduce resolution for motion detection (dual-stream):
   ```yaml
   cameras:
     - id: camera1
       detect_width: 640
       detect_height: 480
   ```

3. Use smaller YOLO model:
   ```yaml
   detection:
     model: "yolo11n.pt"  # From yolo11s
   ```

### FFmpeg Streaming Errors

**Problem**: `ffmpeg: Permission denied` or `Camera disconnected`

**Solution**:
```bash
# Test camera connection
ffmpeg -rtsp_transport tcp -i "rtsp://user:pass@camera:554/stream" -t 5 -f null -

# Check credentials
ping <camera-ip>

# Try with username/password URL encoding for special characters
# Example: password "p@ss" → "p%40ss"
```

### Database Locked

**Problem**: `sqlite3.OperationalError: database is locked`

**Solution**:
```bash
# This is usually temporary. The database writer locks the DB briefly.

# If persistent, remove lock file
rm raaqib.db-journal

# Restart system
python app.py
```

---

## Best Practices

✅ **Do**:
- Use Ctrl+C for graceful shutdown
- Monitor logs via `tail -f logs/raaqib.log`
- Check API health regularly
- Back up recordings periodically
- Restart after config changes

❌ **Don't**:
- Kill process with -9 unless necessary
- Edit config while system is running
- Delete raaqib.db while system is running (data loss)
- Run multiple instances in same directory (lock conflicts)

---

## Next Steps

- [Monitor with MQTT](README.md#mqtt-integration)
- [Use the REST API](API.md)
- [Advanced Configuration](CONFIGURATION.md)
- [Troubleshoot Issues](README.md#troubleshooting)
