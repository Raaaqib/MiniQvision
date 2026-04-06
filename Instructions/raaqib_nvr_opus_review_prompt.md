# Raaqib NVR — Code Review Request for Opus 4.5

You are doing a **deep correctness review** of a Python multiprocessing NVR codebase. Two features were just implemented by an AI model on top of an existing production codebase. Your job is to find every bug, race condition, architectural violation, silent failure, and inconsistency — not to rewrite, just to report precisely what is wrong, where, and why.

---

## The Existing Codebase (what was there before)

This is a self-hosted AI-powered NVR with a two-stage detection pipeline running in Python multiprocessing. You need to understand the real architecture before reviewing the new code.

### Real Queue Names (from architecture docs — use these exact names)

| Queue | Producer | Consumer | maxsize | Purpose |
|-------|----------|----------|---------|---------|
| `motion_queues[cam_id]` | CaptureProcess | MotionProcess | 10 | Raw frames |
| `detection_queue` | MotionProcess | DetectorPool | 20 | MOG2-triggered frames |
| `tracking_queue` | DetectorPool | TrackingProcess | 20 | YOLO detections |
| `record_queues[cam_id]` | MotionProcess | RecordingProcess | 50 | Pre-capture buffer |
| `post_detect_record_queue` | TrackingProcess | RecordingProcess | 50 | Post-tracking clips |
| `event_queue` | TrackingProcess | EventProcessor | 50 | Event lifecycle |
| `mqtt_queue` | EventProcessor | MQTTPublisher | 50 | MQTT events |
| `db_queue` | EventProcessor | DatabaseWriter | 50 | DB writes |

### Real Shared State Structure

```python
state_dict = manager.dict()   # mp.Manager() shared dict

# Per camera key: state_dict[camera_id]
{
    "status": "connected",        # "connected" | "disconnected" | "error"
    "fps": 10.0,
    "frames_captured": 3600,
    "frames_dropped": 2,
    "detections_total": 87,
    "detections_active": 3,
    "last_frame": <img binary>,
}

# Global key: state_dict["events_active"]
[
    {
        "id": "evt_001",
        "camera_id": "camera1",
        "start_time": 1000.0,
        "objects": [{"id": 5, "class": "person", "confidence": 0.92, ...}]
    }
]
```

### Real Detection Object Format (from API docs)

The YOLO worker produces detection dicts (NOT objects) with these keys:
```python
{
    "class": "person",        # key is "class", not "label" or "class_name"
    "confidence": 0.89,
    "bbox": [100, 200, 150, 320],   # [x1, y1, x2, y2]
    "timestamp": "2024-03-04T10:30:45.123Z"
}
```

### Real DetectorPool Worker Loop (existing pattern)

```python
while not stop_event.is_set():
    frame_packet = detection_queue.get(timeout=1)   # BLOCKING get with timeout
    detections = yolo_model(frame_packet.frame)
    tracking_queue.put(detections)
```

Workers use **blocking `get(timeout=1)`**, not `get_nowait()`.

### Real API Response Shape for Cameras (from API.md)

```json
{
  "id": "camera1",
  "name": "Front Door",
  "source": "rtsp://...",
  "enabled": true,
  "status": "connected",
  "fps": 10.0,
  "resolution": "1280x720",
  "frames_captured": 36000,
  "frames_dropped": 5,
  "last_frame_time": "...",
  "detections_count": 42,
  "last_detection": "..."
}
```

### Real GET /api/status Shape (from API.md)

```json
{
  "status": "running",
  "uptime_seconds": 3600,
  "system": { "cpu_percent": 15.2, "memory_percent": 28.5, ... },
  "cameras": { "camera1": { "status": "connected", "fps": 10.0, ... } },
  "detection": { "total_detections": 127, "active_events": 2 },
  "storage": { "recordings_count": 42, "total_size_mb": 2340.5 }
}
```

---

## What Was Implemented (the two new features)

### Feature 1: Per-Camera Model Assignment

Each camera references a named model in `AppConfig.models`. Each unique model gets its own `mp.Queue` (maxsize=20) and `DetectorPool`. Cameras sharing the same model share one queue+pool.

**New config dataclasses:**
```python
@dataclass
class ModelConfig:
    path: str
    device: str = "cpu"
    confidence_threshold: float = 0.45
    pool_size: int = 2
    classes: list[str] = field(default_factory=list)

@dataclass
class CameraConfig:
    # ... existing fields ...
    model: str = "default"
    zones: list[Zone] = field(default_factory=list)

@dataclass
class AppConfig:
    cameras: list[CameraConfig]
    models: dict[str, ModelConfig]   # NEW
    # ... existing fields ...
```

**Backward compat:** If `models:` absent from YAML, loader does:
```python
config.models = {"default": ModelConfig(**config.detection.__dict__)}
```

**New app.py logic:**
```python
camera_model_map: dict[str, str] = {
    cam.id: cam.model for cam in config.cameras if cam.enabled
}
detection_queues: dict[str, mp.Queue] = {}
detector_pools: list[DetectorPool] = []

for model_id in set(camera_model_map.values()):
    model_cfg = config.models[model_id]
    q = mp.Queue(maxsize=20)
    detection_queues[model_id] = q
    pool = DetectorPool(model_cfg, q, tracking_queue, stop_event)
    detector_pools.append(pool)
    pool.start()
```

**New MotionProcess routing:**
```python
model_id = self.camera_model_map[self.camera_id]
try:
    self.detection_queues[model_id].put_nowait(frame_packet)
except Full:
    logger.warning(...)
```

**Shutdown:**
```python
for pool in detector_pools: pool.stop()
for pool in detector_pools: pool.join(timeout=10)
```

### Feature 2: Zone-Based Detection Filtering

Per-camera zones in YAML. Two types: `exclude` (drop detections inside polygon) and `trigger` (drop detections outside polygon). Filtering runs in `detection_worker()` after bbox scaling.

**New dataclasses:**
```python
@dataclass
class ZonePoint:
    x: int
    y: int

@dataclass
class Zone:
    id: str
    name: str
    type: str              # "trigger" or "exclude"
    polygon: list[ZonePoint]
    active: bool = True
    classes: list[str] = field(default_factory=list)
```

**New file `src/core/zones.py`:**
```python
def point_in_polygon(px, py, polygon) -> bool:
    # ray-casting, + 1e-10 guard on division

def bbox_center(bbox) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0

def filter_detections_by_zones(detections, zones, camera_id="") -> list:
    # exclude check first, then trigger check
    # accesses det.bbox and det.label on each detection
```

**Filtering block in detection_worker (after bbox scaling):**
```python
detections = _filter_by_model_classes(detections, det_config)
# _filter_by_model_classes uses: d["class"] in model_cfg.classes

if camera_zones:
    from src.core.zones import filter_detections_by_zones
    zones_for_cam = camera_zones.get(packet.camera_id, [])
    if zones_for_cam:
        detections = filter_detections_by_zones(detections, zones_for_cam, packet.camera_id)
```

**camera_zones built in app.py:**
```python
camera_zones: dict = {
    cam.id: cam.zones
    for cam in config.enabled_cameras
    if cam.zones
}
```

**New `GET /api/models` endpoint and model info added to camera endpoints.**

---

## Review Checklist — Check Every Item

Go through each item. For each issue found: state the file, the exact line or block, what is wrong, and what the fix is.

### A. Critical Data Format Mismatch

**1. `det.label` vs `d["class"]`**

`filter_detections_by_zones` in `zones.py` accesses `det.label` and `det.bbox` (attribute access). But the real detection objects are **dicts** with key `"class"` (not `"label"`) and key `"bbox"`. Meanwhile `_filter_by_model_classes` uses `d["class"]` (dict access). This means:
- `_filter_by_model_classes` works correctly
- `filter_detections_by_zones` raises `AttributeError` on `det.label` at runtime
- Since detections are dicts: `det.bbox` also raises `AttributeError`

Confirm this mismatch exists. State the fix for both `det.label` → `det["class"]` and `det.bbox` → `det["bbox"]` in `zones.py`.

**2. `bbox_center` input format**

`bbox_center` unpacks `x1, y1, x2, y2 = bbox`. The real bbox format from the API docs is `[x1, y1, x2, y2]` — a list of 4 ints. This unpacking works on a list. Confirm it is consistent with what the worker actually passes (check whether the worker passes `det["bbox"]` directly or a tuple).

### B. `config.enabled_cameras` Attribute

**3. Does `AppConfig.enabled_cameras` exist?**

`app.py` uses `config.enabled_cameras` in two places:
```python
camera_zones = {cam.id: cam.zones for cam in config.enabled_cameras if cam.zones}
# and in the logging loop
```

The original `AppConfig` has `cameras: list[CameraConfig]` (from architecture docs). There is no documented `enabled_cameras` property. If this attribute was not added to `AppConfig`, both usages crash with `AttributeError` at startup.

Check: was `enabled_cameras` added as a property returning `[c for c in self.cameras if c.enabled]`? If not, this is a startup crash.

### C. Backward Compatibility

**4. `ModelConfig(**config.detection.__dict__)` — field name mismatch**

The backward-compat fallback does:
```python
config.models = {"default": ModelConfig(**config.detection.__dict__)}
```

`DetectionConfig` (the old dataclass) has field `model_path`. `ModelConfig` has field `path`. If `DetectionConfig.__dict__` contains `model_path` but `ModelConfig.__init__` expects `path`, this raises `TypeError: __init__() got an unexpected keyword argument 'model_path'` at startup for every old config.

Confirm this field name mismatch and state the fix.

**5. `DetectionConfig` extra fields**

`DetectionConfig` may have fields that `ModelConfig` does not have (e.g. `classes` may not have existed in the original). If so, `**config.detection.__dict__` passes unknown keyword arguments and crashes. List which fields in `DetectionConfig` are not in `ModelConfig` and confirm the fix (explicit field mapping instead of `**__dict__`).

### D. Multiprocessing Correctness

**6. `detection_queues` dict pickling into MotionProcess**

`MotionProcess.__init__` receives `detection_queues: dict[str, mp.Queue]`. In Python multiprocessing with the `spawn` start method (default on Windows and macOS), all constructor arguments are pickled before the child process starts. A `dict` of `mp.Queue` objects is picklable. However, if `MotionProcess` stores `detection_queues` as an instance attribute and then `super().__init__()` is called (wrong order), the queue handles may not be inherited correctly on some platforms.

Check: is `super().__init__(daemon=True)` called **before** or **after** storing the queue dict? The correct pattern is `super().__init__()` first, then store attributes. Confirm the order.

**7. `pool.stop()` blocking risk during shutdown**

The shutdown loop:
```python
for pool in detector_pools: pool.stop()
for pool in detector_pools: pool.join(timeout=10)
```

If `pool.stop()` sends a sentinel into the `detection_queue` (a common pattern for stopping workers) and the queue is full (maxsize=20 with backed-up frames from active cameras), `stop()` blocks indefinitely — deadlocking the shutdown. Check: does `pool.stop()` use `put()` or `put_nowait()`? If `put()`, this is a shutdown deadlock risk.

**8. `from queue import Full` import in MotionProcess**

The routing line uses:
```python
except Full:
```

`mp.Queue.put_nowait()` raises `queue.Full` (from the standard library `queue` module). If the import at the top of `motion.py` is missing `from queue import Full`, Python raises `NameError: name 'Full' is not defined` — which crashes the motion process silently (daemon processes don't propagate exceptions to main). Confirm this import exists in `motion.py`.

**9. `camera_zones` passed to workers — is it passed correctly?**

The `camera_zones` dict contains `list[Zone]` where `Zone` is a dataclass with `list[ZonePoint]`. These are plain dataclasses and are picklable. However, `camera_zones` is passed as a positional argument to `_spawn_process(...)`. Confirm that `detection_worker`'s function signature has `camera_zones` as the **last** parameter, matching the positional order in the `_spawn_process` call. A positional mismatch silently assigns `camera_zones` to the wrong parameter (e.g. `lpr_config` or `db_path`).

### E. API Correctness

**10. New fields break existing camera response shape**

The existing `GET /api/cameras` response shape (from API.md) does NOT include `model`, `model_path`, or `model_device`. The implementation adds these fields. This is additive and backward-compatible for API consumers, but check: does the implementation read `model_path` and `model_device` from `config.models[cam.model]`? If `config` is not accessible in the FastAPI route handler (it may be a module-level variable or injected differently), this raises `NameError` or `AttributeError`.

**11. `GET /api/models` — model-to-camera reverse mapping**

The `/api/models` endpoint returns:
```json
{ "fire_detection": { "cameras": ["cam_entrance"] } }
```

This requires building a reverse map from `model_id → list[camera_id]`. Check: is this reverse map built at request time (iterating `config.cameras`) or cached at startup? If built at request time, it is correct but slightly expensive. If cached at startup in a module-level dict, verify it is initialized before the first request.

**12. `GET /api/status` — `models` key added**

The spec adds a `models` summary to `/api/status`. The existing response shape (from API.md) does not include `models`. Confirm the new `models` block is added additively and does not break existing top-level keys (`status`, `uptime_seconds`, `system`, `cameras`, `detection`, `storage`). Specifically: does the implementation use response dict merging (`{**existing, "models": ...}`) or does it reconstruct the dict from scratch (risking missing existing keys)?

### F. Zone Geometry Edge Cases

**13. `point_in_polygon` — collinear polygon not validated**

`_validate_zones` only checks `len(polygon) >= 3`. A polygon with 3 collinear points (e.g. `[(0,0), (100,0), (200,0)]`) is geometrically degenerate — a line, not a polygon. `point_in_polygon` on a degenerate polygon returns unpredictable results (always False, or occasional True on exact boundary). This is a logic hazard, not a crash. Confirm the validation does not catch this and document it as a known limitation.

**14. `filter_detections_by_zones` — trigger zone logic for unmatched classes**

The spec says: if a camera has trigger zones but a detection's class is not in any trigger zone's `classes` list → the detection should be **forwarded** (no applicable trigger = unconstrained). The implementation:
```python
applicable_triggers = [z for z in trigger_zones if not z.classes or label in z.classes]
if applicable_triggers:
    inside_any = any(point_in_polygon(cx, cy, z.polygon) for z in applicable_triggers)
    if not inside_any:
        continue  # DROP
```

When `applicable_triggers` is empty (no trigger zone applies to this class), the `if applicable_triggers:` block is skipped and the detection is kept. This is **correct** per spec. Confirm it is implemented this way and not accidentally inverted.

### G. Config Validation Timing

**15. `validate_config()` called before or after model pool spawn?**

The spec says validation must run at startup and abort before any worker is spawned. Check `app.py`: is `validate_config()` called **before** the `for model_id in set(camera_model_map.values()):` loop? If called after, a missing model file causes workers to start, fail to load the model, and crash individually — harder to debug than a clean startup abort.

**16. Path validation on Windows**

`validate_config` uses `Path(model_cfg.path).exists()`. On Windows with the `spawn` context, the working directory of the main process determines relative path resolution. If `app.py` is run from a different directory than the project root, `Path("models/yolo11n.onnx").exists()` returns False even if the file exists. This is not a new bug (the original code had the same issue) but confirm the validation doesn't make it worse.

---

## Output Format

For each issue found, report exactly:

```
ISSUE #N — <severity: CRITICAL | HIGH | MEDIUM | LOW>
File: <filename>
Location: <function name or line description>
Problem: <what is wrong>
Impact: <what breaks at runtime>
Fix: <exact code change>
```

After listing all issues, provide:
1. A **summary table** of all issues by severity
2. A **verdict**: is the implementation safe to run, or does it crash on startup/first detection?

Do not suggest refactors or improvements beyond what is needed to make the implementation correct per the spec. Focus exclusively on bugs, crashes, and behavioral violations.
