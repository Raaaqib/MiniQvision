# RAAQIB NVR — Configuration Reference

Complete reference for all configuration options in `config.yaml`.

## Table of Contents

- [File Overview](#file-overview)
- [Cameras Section](#cameras-section)
- [Detection Section](#detection-section)
- [Recording Section](#recording-section)
- [API Section](#api-section)
- [Database Section](#database-section)
- [MQTT Section](#mqtt-section)
- [Snapshots Section](#snapshots-section)
- [Logging Section](#logging-section)
- [Common Configurations](#common-configurations)

---

## File Overview

Configuration file: `config/config.yaml`

Basic structure:

```yaml
cameras: []          # List of camera configurations
detection: {}        # YOLO detection settings
recording: {}        # Recording settings
snapshots: {}        # Snapshot saving settings
api: {}              # FastAPI server settings
database: {}         # SQLite database settings
mqtt: {}             # MQTT publishing settings
logging: {}          # Logging configuration
```

---

## Cameras Section

### Basic Camera Configuration

```yaml
cameras:
  - id: "camera1"                    # Unique ID (alphanumeric, no spaces)
    name: "Front Door"               # Display name
    source: "rtsp://..."             # RTSP URL or USB index
    enabled: true                    # Enable/disable camera
```

### Full Camera Options

```yaml
cameras:
  - id: "camera1"
    name: "Front Door"
    source: "rtsp://admin:password@192.168.1.100:554/stream1"
    enabled: true
    
    # ── Capture Settings ──────────────────────────────────────
    fps_target: 10                   # Target FPS for capture (1-30)
    width: 1280                      # Frame width for recording
    height: 720                      # Frame height for recording
    
    # ── Motion Detection Settings ─────────────────────────────
    motion_threshold: 0.02           # Motion % to trigger detection (0.01-0.5)
    min_contour_area: 1500           # Minimum contour size in pixels
    
    # ── Dual-Stream Optimization ──────────────────────────────
    # Optional: Lower resolution for motion/detection, full resolution for recording
    detect_width: 640                # Resolution for detection (0 = same as width)
    detect_height: 480               # Resolution for detection (0 = same as height)
    detect_fps: 5                    # FPS for detection stream (0 = same as fps_target)
    detect_url: ""                   # Alternative RTSP URL for detection stream
    
    # ── Retention ─────────────────────────────────────────────
    retain_days: 7                   # Keep clips/snapshots for N days
    
    # ── Zones (Optional) ──────────────────────────────────────
    zones:
      - name: "entrance"
        points:
          - [100, 100]
          - [500, 100]
          - [500, 400]
          - [100, 400]
      - name: "driveway"
        points:
          - [600, 200]
          - [1280, 200]
          - [1280, 720]
          - [600, 720]
```

### Camera Source Types

#### RTSP Stream

```yaml
source: "rtsp://admin:password@192.168.1.100:554/stream1"
```

Options:
- `rtsp://` — Standard RTSP
- `rtsps://` — Secure RTSP (TLS)
- Check camera manual for stream URL

#### USB Webcam

```yaml
source: 0                # USB device index (0 = first camera)
source: 1                # (1 = second camera)
```

#### HTTP/MJPEG Stream

```yaml
source: "http://192.168.1.100:8080/video"
```

### Camera Presets

#### Raspberry Pi Camera (CSI)

```yaml
- id: "rpi_cam"
  name: "Raspberry Pi Camera"
  source: 0
  fps_target: 5
  width: 1640
  height: 1232
```

#### IP Camera (Hikvision/Dahua)

```yaml
- id: "hikvision"
  name: "Hikvision IP Camera"
  source: "rtsp://admin:password@192.168.100.64:554/Streaming/Channels/101"
  fps_target: 10
  width: 1920
  height: 1080
  detect_width: 640
  detect_height: 480
```

#### USB Webcam (Logitech, etc.)

```yaml
- id: "usb_cam"
  name: "USB Webcam"
  source: 0
  fps_target: 30
  width: 1920
  height: 1080
```

#### Doorbell Camera

```yaml
- id: "doorbell"
  name: "Front Door Doorbell"
  source: "rtsp://admin:password@192.168.1.50:554/stream"
  fps_target: 10
  width: 2560
  height: 1440
  detect_width: 1024
  detect_height: 576
  motion_threshold: 0.01  # Sensitive for doorbell
```

---

## Detection Section

### YOLO Configuration

```yaml
detection:
  model: "yolo11n.pt"              # Model size
  confidence: 0.45                 # Detection confidence threshold
  iou: 0.45                        # IoU threshold for NMS
  device: "cpu"                    # Device: cpu, cuda, mps, tpu
  backend: "cpu"                   # Inference engine: cpu, edgetpu
  pool_size: 2                     # Number of detection workers
  target_classes: []               # Empty = all classes
```

### Model Selection

| Model | Speed | Memory | Best For |
|-------|-------|--------|----------|
| `yolo11n.pt` | ⚡⚡⚡⚡ | ~100 MB | Low-power devices (RPi) |
| `yolo11s.pt` | ⚡⚡⚡ | ~200 MB | CPU with 4GB+ RAM |
| `yolo11m.pt` | ⚡⚡ | ~400 MB | GPU-accelerated systems |
| `yolo11l.pt` | ⚡ | ~700 MB | High-end GPU (RTX 3080+) |

### Device Selection

#### CPU-Only
```yaml
detection:
  model: "yolo11n.pt"
  device: "cpu"
  pool_size: 1
```

**Best for**: Single camera, budget systems

#### NVIDIA GPU (CUDA)
```yaml
detection:
  model: "yolo11m.pt"
  device: "cuda"
  pool_size: 4
```

**Requirements**: CUDA 11.8+, cuDNN 8.6+, NVIDIA Driver

#### AMD GPU (ROCm)
```yaml
detection:
  model: "yolo11m.pt"
  device: "cuda"  # Uses ROCM backend automatically
  pool_size: 2
```

**Requirements**: ROCm 5.0+, AMD GPU (Radeon RX)

#### Apple Silicon (Metal)
```yaml
detection:
  model: "yolo11m.pt"
  device: "mps"   # Metal Performance Shaders
  pool_size: 2
```

**Best for**: M1/M2/M3 Macs

#### Google Coral TPU
```yaml
detection:
  model: "yolo11n.pt"
  device: "cpu"
  backend: "edgetpu"
  pool_size: 1
```

**Requirements**: Coral USB Accelerator, tflite model

### Class Filtering

Detect only specific object classes:

```yaml
detection:
  target_classes:
    - "person"
    - "car"
    - "dog"
```

Available COCO classes:
- Objects: `person`, `bicycle`, `car`, `motorcycle`, `bus`, `truck`
- Animals: `bird`, `cat`, `dog`, `horse`, `sheep`, `cow`, `elephant`
- Other: `traffic light`, `fire hydrant`, `stop sign`, etc.

Leave empty `[]` to detect all classes.

---

## Recording Section

### Recording Settings

```yaml
recording:
  enabled: true                     # Enable clip recording
  pre_capture_s: 3                  # Seconds before detection
  post_capture_s: 8                 # Seconds after last detection
  max_clip_s: 60                    # Maximum clip length
  
  # ── Video Encoding ─────────────────────────────────────────
  fps: 10                           # Clip FPS (independent of capture FPS)
  codec: "libx264"                  # Video codec
  crf: 23                           # Quality (0-51, lower=better, 18-28 typical)
  bitrate: ""                       # Bitrate (e.g., "5000k", empty = auto CRF)
```

### CRF Quality Guide

| CRF | Quality | Bitrate (1080p) | Use Case |
|-----|---------|-----------------|----------|
| 18 | Visually lossless | ~8-12 Mbps | Archive |
| 23 | High quality (default) | ~5-8 Mbps | Typical |
| 28 | Medium quality | ~2-4 Mbps | Low storage |
| 32 | Lower quality | ~1-2 Mbps | Minimal storage |

### Codec Options

- `libx264` — H.264 (compatibility, slower encoding)
- `libx265` — H.265/HEVC (better compression, faster encoding)

**Recommendation**: libx265 for new systems, libx264 for compatibility

### Storage Estimate

**Formula**: `bitrate × duration / 8`

Example:
```
Resolution: 1280x720
FPS: 10
Codec: H.264 (CRF 23)
Bitrate: ~5 Mbps (estimate)
Duration: 10 seconds

Size = 5 Mbps × 10 sec / 8 = 6.25 MB per clip
```

With typical motion (2 clips/hour × 10s each):
- Per day: 24 × 2 × 6.25 MB = 300 MB
- Per month: 9 GB
- Per year: 110 GB

---

## API Section

### FastAPI Server Configuration

```yaml
api:
  host: "0.0.0.0"                  # Listen on all interfaces
  port: 8000                       # HTTP port
  reload: false                    # Auto-reload on code changes (dev only)
  workers: 4                       # ASGI worker threads
```

### Access from Remote Host

To access API from other machines:

```yaml
api:
  host: "0.0.0.0"                  # Listen on all interfaces
  port: 8000                       # Or any available port
```

Then access from remote:
```bash
curl http://<machine-ip>:8000/api/status
```

### Security

For remote access, use reverse proxy with authentication:

```nginx
# /etc/nginx/sites-available/raaqib
server {
    listen 80;
    server_name raaqib.local;
    
    auth_basic "Raaqib API";
    auth_basic_user_file /etc/nginx/raaqib.htpasswd;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
}
```

---

## Database Section

### SQLite Configuration

```yaml
database:
  path: "raaqib.db"                # Database file location
  retention_days: 30               # Keep events for N days
  checkpoint_interval: 100         # Commit after N events
```

### Backup Strategy

```bash
# Manual backup
cp raaqib.db raaqib.db.backup

# Automated backup (daily cron job)
0 2 * * * cp /path/to/raaqib.db /backup/raaqib.db.$(date +\%Y-\%m-\%d)
```

---

## MQTT Section

### MQTT Broker Integration

```yaml
mqtt:
  enabled: false                   # Enable MQTT publishing
  broker: "127.0.0.1"              # Broker hostname/IP
  port: 1883                       # Standard MQTT port (8883 for TLS)
  username: ""                     # Broker username
  password: ""                     # Broker password
  retain: true                     # Retain messages on broker
  prefix: "raaqib"                 # Topic prefix
```

### Home Assistant Configuration

Add to `configuration.yaml`:

```yaml
mqtt:
  broker: 192.168.1.50

automation:
  - alias: "Front door person detected"
    trigger:
      platform: mqtt
      topic: "raaqib/camera1/detection"
    condition:
      template: >
        {{ trigger.payload_json.objects | 
           selectattr('class', 'equalto', 'person') | 
           list | length > 0 }}
    action:
      - service: notify.mobile_app_phone
        data:
          message: "Person detected at front door!"
          data:
            image: >
              http://192.168.1.50:8000/api/cameras/camera1/frame
```

### Mosquitto Broker (Docker)

```bash
docker run -d \
  --name mosquitto \
  -p 1883:1883 \
  -p 9001:9001 \
  eclipse-mosquitto:latest
```

---

## Snapshots Section

### Detection Snapshot Configuration

```yaml
snapshots:
  enabled: true                    # Save snapshots on detection
  quality: 85                      # JPEG quality (1-100)
  draw_boxes: true                 # Draw detection boxes
  draw_labels: true                # Draw class labels
  draw_confidence: true            # Draw confidence scores
```

### Storage Location

Snapshots saved to: `snapshots/{camera_id}/YYYY-MM-DD/`

Example:
```
snapshots/
├── camera1/
│   └── 2024-03-04/
│       ├── 10-30-45_person_0.92.jpg
│       ├── 10-31-22_car_0.88.jpg
│       └── 10-32-10_person_0.95.jpg
│
└── camera2/
    └── 2024-03-04/
        └── 10-30-50_dog_0.76.jpg
```

---

## Logging Section

### Log Configuration

```yaml
logging:
  level: "INFO"                    # Log level: DEBUG, INFO, WARNING, ERROR
  format: "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
  file: "logs/raaqib.log"          # Log file path
  max_bytes: 10485760              # Max file size (10 MB)
  backup_count: 5                  # Keep 5 backup files
```

### Log Levels

| Level | Usage | Example |
|-------|-------|---------|
| DEBUG | Detailed diagnostics | Frame processing details |
| INFO | General information | Process started, camera connected |
| WARNING | Warning conditions | Low disk space, dropped frames |
| ERROR | Error conditions | Camera disconnected, detection failed |

### View Logs

```bash
# Real-time monitoring
tail -f logs/raaqib.log

# Search for errors
grep ERROR logs/raaqib.log

# Last 50 lines
tail -50 logs/raaqib.log

# By component
grep "\[motion" logs/raaqib.log
grep "\[detector" logs/raaqib.log
```

---

## Common Configurations

### Single USB Webcam (Budget Setup)

```yaml
cameras:
  - id: "usb_cam"
    name: "My Camera"
    source: 0
    enabled: true
    fps_target: 5
    width: 640
    height: 480
    motion_threshold: 0.03

detection:
  model: "yolo11n.pt"
  device: "cpu"
  pool_size: 1

recording:
  enabled: true
  pre_capture_s: 2
  post_capture_s: 5
  max_clip_s: 30
  crf: 28

api:
  host: "127.0.0.1"
  port: 8000
```

### Multi-Camera Residential (Typical)

```yaml
cameras:
  - id: "front_door"
    name: "Front Door"
    source: "rtsp://admin:pass@192.168.1.100:554/stream1"
    fps_target: 10
    width: 1280
    height: 720
    
  - id: "back_porch"
    name: "Back Porch"
    source: "rtsp://admin:pass@192.168.1.101:554/stream1"
    fps_target: 10
    width: 1280
    height: 720

detection:
  model: "yolo11s.pt"
  device: "cuda"
  pool_size: 2

recording:
  enabled: true
  pre_capture_s: 5
  post_capture_s: 10
  crf: 23

database:
  retention_days: 14

mqtt:
  enabled: true
  broker: "192.168.1.50"
  port: 1883
```

### High-End Setup (GPU-Accelerated)

```yaml
cameras:
  - id: "front_4k"
    name: "Front Door 4K"
    source: "rtsp://admin:pass@192.168.1.100:554/stream1"
    fps_target: 30
    width: 3840
    height: 2160
    detect_width: 1280   # Dual-stream optimization
    detect_height: 720
    detect_fps: 10
    
  - id: "back_4k"
    name: "Back Porch 4K"
    source: "rtsp://admin:pass@192.168.1.101:554/stream1"
    fps_target: 30
    width: 3840
    height: 2160
    detect_width: 1280
    detect_height: 720

detection:
  model: "yolo11l.pt"
  device: "cuda"
  pool_size: 4

recording:
  enabled: true
  pre_capture_s: 10
  post_capture_s: 15
  codec: "libx265"
  crf: 18

database:
  retention_days: 30
```

### Minimal (Low-Power Device - RPI Zero)

```yaml
cameras:
  - id: "cam"
    name: "Camera"
    source: 0
    fps_target: 3
    width: 320
    height: 240

detection:
  model: "yolo11n.pt"
  device: "cpu"
  pool_size: 1

recording:
  enabled: false

snapshots:
  quality: 60

logging:
  level: "WARNING"
```

---

## Validation & Troubleshooting

### Validate Configuration

```bash
# Check syntax errors
python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"

# Validate with Raaqib
python -c "from config import load_config; c = load_config('config/config.yaml'); print('✓ Valid')"
```

### Check Configuration Values

```bash
python -c "
from config import load_config
c = load_config('config/config.yaml')
print(f'Cameras: {len(c.cameras)}')
print(f'Model: {c.detection.model}')
print(f'Device: {c.detection.device}')
print(f'API: {c.api.host}:{c.api.port}')
"
```

### Common Configuration Errors

**Missing quotes in RTSP URL**:
```yaml
# ❌ WRONG
source: rtsp://admin:pass@192.168.1.100/stream

# ✅ CORRECT
source: "rtsp://admin:pass@192.168.1.100/stream"
```

**Invalid camera ID**:
```yaml
# ❌ WRONG
id: Front Door   # Has space

# ✅ CORRECT
id: front_door   # Alphanumeric + underscore
```

**Port already in use**:
```bash
# Check port
lsof -i :8000    # Linux/macOS
netstat -ano | findstr :8000  # Windows

# Use different port
api:
  port: 8001
```

---

## Environment Variables (Optional)

Override config with environment variables:

```bash
# Bash
export RAAQIB_API_PORT=9000
export RAAQIB_DETECTION_DEVICE=cuda

python app.py
```

Or in `.env` file:
```
RAAQIB_API_PORT=9000
RAAQIB_DETECTION_DEVICE=cuda
```

---

## Next Steps

- [Installation Guide](INSTALLATION.md)
- [Running Raaqib](RUNNING.md)
- [API Reference](API.md)
- [Architecture Details](ARCHITECTURE.md)
