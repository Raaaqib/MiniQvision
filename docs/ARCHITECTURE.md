# RAAQIB NVR — Architecture & Design

Deep dive into Raaqib's system architecture, data flow, and process communication.

## Table of Contents

- [System Overview](#system-overview)
- [Two-Stage Detection Pipeline](#two-stage-detection-pipeline)
- [Process Architecture](#process-architecture)
- [Data Flow](#data-flow)
- [Inter-Process Communication (IPC)](#inter-process-communication-ipc)
- [Component Details](#component-details)
- [Performance Characteristics](#performance-characteristics)
- [Design Decisions](#design-decisions)

---

## System Overview

Raaqib is built on **distributed multiprocessing architecture** where each component runs as an isolated process, communicating through queues and shared memory.

```
┌──────────────────────────────────────────────────────────────┐
│                    MAIN PROCESS (app.py)                    │
│  Spawns children, manages state, provides graceful shutdown │
└──────────────────────────────────────────────────────────────┘
         │              │              │               │
         ├──────────────┼──────────────┼───────────────┤
         │              │              │               │
    ┌────▼──────┐  ┌───▼────┐  ┌────▼──────┐  ┌───▼────┐
    │  CAPTURE  │  │ MOTION │  │ DETECTION │  │TRACKING│
    │ Processes │  │ Processes─ Pool Proc │  │Process │
    │ (per cam) │  │        │  │           │  │        │
    └───────────┘  └────────┘  └───────────┘  └────────┘
         │              │              │               │
         └──────────────┴──────────────┴───────────────┘
                        │
            ┌───────────┴────────────┬──────────────┬──────────┐
            │                        │              │          │
        ┌───▼────┐            ┌────▼──┐      ┌───▼──┐    ┌──▼────┐
        │RECORDER│            │ EVENTS│      │ MQTT │    │ DATABASE
        │Process │            │Processor     │ Pub  │    │Writer
        │        │            │              │      │    │
        └────────┘            └───────┘      └──────┘    └───────┘
```

---

## Two-Stage Detection Pipeline

The core innovation of Raaqib is its **two-stage detection pipeline**, optimizing for both speed and accuracy.

### Stage 1: Motion Detection (OpenCV MOG2)

```
┌─────────────────────────────────────────────────┐
│ INPUT: Raw camera frame @ target FPS     (10fps)│
└──────────────────────┬──────────────────────────┘
                       │
                ┌──────▼───────┐
                │ MOG2 BG Sub  │  ← Mixture of Gaussians
                │              │     Learns background
                │ cost: ~2ms   │     per frame
                └──────┬───────┘
                       │
                ┌──────▼─────────────────────┐
                │ Calculate contour flow     │
                │ - Area filtering           │ ← MIN_CONTOUR_AREA
                │ - Motion threshold check   │ ← 2% of frame
                └──────┬────────────────────└
                       │
                    ┌──▼──────────────────────┐
                    │ DECISION: Motion Found? │
                    └──┬─────────────────┬────┘
             YES       │                 │       NO
            ┌──────────▼──┐         ┌────▼──────────┐
            │ Send frame  │         │ Discard frame │
            │  to Stage 2 │         │ Save to buffer│
            └─────────────┘         └───────────────┘
```

**Cost**: ~2-5ms per frame (CPU-bound, O(1) on GPU)

### Stage 2: Object Detection (YOLO 11)

```
┌─────────────────────────────────────────┐
│ INPUT: Frames with motion detected  (1-5fps avg)
└──────────────────┬──────────────────────┘
                   │
           ┌───────▼────────┐
           │ YOLO Inference │  ← Only when needed!
           │ ~ 50-500ms     │    (depends on hardware)
           │ per frame      │
           └───────┬────────┘
                   │
        ┌──────────▼──────────────┐
        │ Post-processing         │
        │ - NMS (remove overlaps) │
        │ - Confidence filtering  │
        │ - Class mapping         │
        └──────────┬─────────────┘
                   │
        ┌──────────▼──────────────┐
        │ OUTPUT: Detections     │
        │ {class, confidence,    │
        │  bbox, timestamp}      │
        └────────────────────────┘
```

**Cost**: 50-500ms per detection (GPU-bound, varies by model)

### Energy Efficiency Example

With a typical camera:
- **10 FPS capture rate**
- **2 motion events per hour** (typical residential)

**Without two-stage** (continuous YOLO):
```
600 frames/min × 60 min/hour × 0.3s = 180 GPU-seconds/hour
```

**With two-stage** (YOLO only on motion):
```
2 events × 1 second average = 2 GPU-seconds/hour
Savings: 98% reduction in GPU load
```

---

## Process Architecture

### Main Process (app.py)

**Responsibilities**:
- Load and validate configuration
- Create shared IPC mechanisms (manager, queues, events)
- Spawn all child processes
- Monitor process health
- Graceful shutdown

**Key Components**:
```python
manager = mp.Manager()              # Shared state dict
state_dict = manager.dict()         # Camera states + events
stop_event = mp.Event()             # Shutdown signal

# Queues for communication
detection_queue = mp.Queue()        # Frame → Detectors
tracking_queue = mp.Queue()         # Detections → Tracker
event_queue = mp.Queue()            # Events → processing
mqtt_queue = mp.Queue()             # Events → MQTT
db_queue = mp.Queue()               # Events → Database
```

### Per-Camera Processes

#### Capture Process
```
RTSP/USB Stream
     │
     ├─→ [FFmpeg Reader]
     │
     ├─→ [Frame Decoder]
     │
     ├─→ [Frame Packet Creation]
     │         {frame, timestamp, camera_id}
     │
     └─→ [Motion Queue]
```

**Purpose**: Decode video stream into frames  
**Language**: Python with OpenCV  
**Resources**: ~1-2% CPU per stream (depends on codec)

#### Motion Process
```
[Motion Queue] ← frames from Capture
     │
     ├─→ [MOG2 Background Model]
     │      {history: 500 frames, variance: 16}
     │
     ├─→ [Foreground Mask]
     │      {binary mask of changed pixels}
     │
     ├─→ [Contour Detection]
     │      {find connected foreground regions}
     │
     ├─→ [Area Filter]
     │      {only contours > MIN_CONTOUR_AREA}
     │
     ├─→ Decision: Motion?
     │      │
     │      ├─ YES: Flow to Detection Queue
     │      │        + Pre-capture buffer → Recording Queue
     │      │
     │      └─ NO:  Pre-capture buffer only
     │             (used if future motion detected)
```

**Purpose**: Efficient motion detection before expensive YOLO inference  
**Cost**: ~2-5ms per frame (background subtraction is CPU-efficient)  
**Cooldown**: Motion events throttled to ~5 FPS (configurable)

### Shared Processes

#### Detection Worker Pool

```
[ Detection Queue ]
        │
    ┌───┴───┬───────┬───────┬─────────┐
    │       │       │       │         │
┌───▼───┐ ┌─▼───┐ ┌─▼───┐ ┌─▼───┐ ┌─▼────┐
│Worker0│ │Worker1│ │Worker2│ │Worker3│ │...Workerᵢ│
│(ONNX) │ │(ONNX) │ │(ONNX) │ │(ONNX) │ │(ONNX)   │
└───┬───┘ └─┬───┘ └─┬───┘ └─┬───┘ └─┬────┘
    │       │       │       │       │
    └───┬───┴───┬───┴───┬───┴───────┘
        │       │       │
        └───┬───┴───┬───┘
            │       │
        [ Tracking Queue ]
```

**Purpose**: Parallel YOLO inference (bottleneck resource)  
**Design**: Worker pool prevents frame queue from backing up  
**Scaling**: `pool_size: 2` default (tunable per hardware)

#### Tracking Process

```
[ Tracking Queue ]  ← Detections from workers
        │
        ├─→ [Centroid Computation]
        │      {compute center of each detection bbox}
        │
        ├─→ [Centroid Matching]
        │      {find closest previous centroids (distance < TRACK_MAX_DISTANCE)}
        │
        ├─→ [Object ID Assignment]
        │      {new ID or update existing object}
        │
        ├─→ [Persistence Check]
        │      {remove objects not seen in > TRACK_MAX_DISAPPEARED frames}
        │
        ├─→ [Output]
        │      {frame_id: {id: 5, class: "person", confidence: 0.87, ...}}
        │
        └─→ [ Reporting Queue ]
               {event_queue, record_queue}
```

**Purpose**: Maintain persistent object IDs across frames  
**Latency**: ~10ms per batch  
**Algorithm**: Centroid tracker (simple, CPU-efficient)

#### Recording Process

```
[ Pre-capture Buffer ]  ← frames from Motion
        │
        ├─→ [Sliding Window Buffer]
        │      {keep last N seconds of video}
        │
[ Post-detection Queue ]  ← tracking results
        │
        ├─→ [Merge with Buffer]
        │
        ├─→ [FFmpeg H.264 Encoding]
        │      {CRF 23, ~5-10 Mbps}
        │
        ├─→ [File Writing]
        │      {recordings/{camera_id}/YYYY-MM-DD/HH-MM-SS.mp4}
        │
        └─→ [Event System]
               {notify when clip complete}
```

**Purpose**: Record clips around detections  
**Storage Efficiency**: Pre-capture buffer reduces video count, CRF 23 compresses  
**Output**: ~1.5-2 MiB per minute (H.264, "good" quality)

---

## Data Flow

### Single Detection Lifecycle

```
TIME: 0ms
↓
[Capture] reads frame from RTSP
│ frame_id: 0, timestamp: 1000ms, camera_id: "cam1"
│
├─→ [Motion Queue]
    │
    TIME: 2ms
    ↓
    [Motion] computes MOG2 background subtraction
    │ motion_detected: true (3% flow)
    │
    ├─→ [Detection Queue] + [Recording Queue]
        │
        TIME: 4ms
        ├─→ [Recording] receives frame
        │   Adds to pre-capture buffer (circular)
        │
        └─→ [Detection Worker] picks up frame
            │
            TIME: 50ms (GPU inference)
            ↓
            YOLO output:
            [
              {x: 100, y: 200, w: 50, h: 100, class: "person", conf: 0.92},
              {x: 400, y: 300, w: 80, h: 60, class: "car", conf: 0.88}
            ]
            │
            ├─→ [Tracking Queue]
                │
                TIME: 65ms
                ↓
                [Tracker] assigns IDs
                [
                  {id: 5, class: "person", conf: 0.92, bbox: {...}},
                  {id: 3, class: "car", conf: 0.88, bbox: {...}}
                ]
                │
                ├─→ [Event Queue]
                    │
                    TIME: 70ms
                    ├─→ [Event Processor]
                    │   │
                    │   ├─→ [MQTT Queue] → Home Assistant
                    │   ├─→ [DB Queue] → SQLite insert
                    │   └─→ [Snapshot] save detection image
                    │
                    └─→ [Record Queue]
                        │
                        TIME: 100ms
                        ├─→ [Recorder] writes clip segment
                        │   Uses pre-capture buffer + current + post-capture
                        │
                        └─→ [Retention] checks + cleans old files
```

**Total Latency**: Frame capture → MQTT/DB event: ~70-100ms

---

## Inter-Process Communication (IPC)

### Queues (Producer → Consumer)

| Queue Name | Producer | Consumer | Size | Purpose |
|------------|----------|----------|------|---------|
| `motion_queues[cam_id]` | Capture | Motion | 10 | Raw frames |
| `detection_queue` | Motion | Detector Pool | 20 | MOG2-detected frames |
| `post_detect_record_queue` | Tracking | Recording | 50 | Tracking results for recording |
| `record_queues[cam_id]` | Motion | Recording | 50 | Pre-capture buffer |
| `tracking_queue` | Detector | Tracker | 20 | YOLO detections |
| `event_queue` | Tracker | Event Proc | 50 | Event lifecycle |
| `mqtt_queue` | Event Proc | MQTT Pub | 50 | Events for MQTT |
| `db_queue` | Event Proc | DB Writer | 50 | Events for database |

### Shared State (state_dict)

```python
state_dict = {
    "camera1": {
        "status": "connected",
        "fps": 10.0,
        "frames_captured": 3600,
        "frames_dropped": 2,
        "detections_total": 87,
        "detections_active": 3,
        "last_frame": {img binary},
    },
    "events_active": [
        {
            "id": "evt_001",
            "camera_id": "camera1",
            "start_time": 1000.0,
            "objects": [
                {"id": 5, "class": "person", "confidence": 0.92, ...}
            ]
        }
    ]
}
```

### Signal Communication (stop_event)

```python
stop_event = mp.Event()

# Main process receives Ctrl+C
signal_handler() → stop_event.set()

# Child processes check periodically
while not stop_event.is_set():
    # Process work...
    time.sleep(0.1)

# Graceful shutdown sequence
stop_event.set()
# → All children stop work loops
# → All children clean up resources
# → Main process joins with timeout
# → Remaining processes force-killed
```

---

## Component Details

### Detector Pool Architecture

**Why a pool?**
- YOLO inference is the bottleneck (50-500ms per frame)
- Multiple workers prevent queue overflow during bursts
- Workers run independently, preventing deadlocks

**Configuration**:
```yaml
detection:
  pool_size: 2  # Number of workers
```

**Internal Queuing**:
```python
# Each worker processes independently
while not stop_event.is_set():
    frame_packet = detection_queue.get(timeout=1)
    detections = yolo_model(frame_packet.frame)
    tracking_queue.put(detections)
```

### Motion Threshold Algorithm

```python
# From motion.py
motion_score = np.sum(foreground_mask) / (height × width)
motion_detected = motion_score > motion_threshold  # e.g., 0.02 = 2%
```

**Tuning**:
- Increase threshold → fewer false positives, miss real motion
- Decrease threshold → catch all motion, more false positives

### Centroid Tracker

Simple but effective algorithm:

```python
# Compute centroid of each detection
centroids = [bbox.center() for bbox in new_detections]

# Match to previous frame
for new_centroid in centroids:
    # Find closest existing centroid
    distances = [distance(new_centroid, prev_centroid) 
                 for prev_centroid in previous_centroids]
    
    if min(distances) < TRACK_MAX_DISTANCE:
        # Update existing object
        object_id = id_map[closest_index]
    else:
        # New object
        object_id = next_id()
```

---

## Performance Characteristics

### CPU Usage by Component

| Component | Load | Frequency |
|-----------|------|-----------|
| Capture (1 cam) | ~1-2% | Continuous |
| Motion (1 cam) | ~2-5% | Continuous |
| YOLO Detector | ~50-80% | Only on motion |
| Tracker | <1% | Sporadic |
| Recorder | ~5-10% | During recording |
| API | <1% | On request |

### Memory Usage by Component

| Component | Memory | Notes |
|-----------|--------|-------|
| Capture (1 cam) | ~50-100 MiB | Frame buffers |
| Motion (1 cam) | ~20-50 MiB | MOG2 model |
| YOLO Worker | ~300-800 MiB | Model weight + batch |
| Database | ~10-50 MiB | Depends on retention |
| **Total (2 cam, 2 workers)** | **~1-1.5 GiB** | Typical setup |

### Latency Breakdown (per frame with motion)

```
Capture          → Motion
    2ms             2-5ms
                        ↓
                    [Decision: Motion?]
                        ↓
                    Detection Worker (inference)
                     50-500ms (depends on GPU)
                        ↓
                    Tracker
                     10ms
                        ↓
                    Event Processor
                     5ms

TOTAL: 70-520ms depending on GPU availability
```

---

## Design Decisions

### Why Multiprocessing (not Threading)?

**Problem**: Python's GIL (Global Interpreter Lock) prevents true parallelism

**Solution**: Separate processes bypass GIL
- Each camera capture runs independently
- YOLO inference workers don't block each other
- Motion detection doesn't wait for tracking

**Trade-off**: Higher memory overhead but better CPU scaling

### Why ONNX (not PyTorch)?

**Reason 1: Smaller Download**
- PyTorch: ~2 GB
- ONNX: ~50-100 MB

**Reason 2: Faster Inference**
- ONNX Runtime optimized for inference
- Native CPU parallelization
- Better memory management

### Why Centroid Tracker (not Deep SORT)?

**Reason 1: Simplicity**
- Centroid: ~50 lines of code
- Deep SORT: Complex neural network

**Reason 2: CPU Efficiency**
- Centroid: <1ms per frame
- Deep SORT: 50-100ms per frame

**Reason 3: Adequate for Surveillance**
- Most objects move linearly
- Camera feeds are high FPS
- Objects rarely cross paths quickly

### Why SQLite (not PostgreSQL)?

**Reason 1: Zero Setup**
- PostgreSQL requires server setup
- SQLite is file-based

**Reason 2: Single Machine**
- Raaqib is designed for local deployment
- No distributed requirements

**Reason 3: Sufficient Performance**
- ~1000 events/day = easy for SQLite
- Retention policy limits DB size

---

## Scaling Considerations

### Single Machine Scaling

**More Cameras**:
```yaml
cameras:
  - id: cam1
    fps_target: 5      # Lower FPS
    detect_width: 640  # Lower resolution
```

**Better GPU**:
```yaml
detection:
  model: "yolo11l.pt"  # Larger model
  pool_size: 4         # More workers
```

### Not Designed For

- **Distributed surveillance** (multiple PCs)
- **Cloud-based inference** (Internet dependency)
- **24/7 pure YOLO** (use motion detection!)
- **Real-time* stream viewing** (designed for events)

---

## Next Steps

- [Running the System](RUNNING.md)
- [API Documentation](API.md)
- [Configuration Reference](CONFIGURATION.md)
- [Performance Tuning](README.md#performance-tuning)
