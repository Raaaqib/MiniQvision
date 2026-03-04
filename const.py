"""
Raaqib NVR — Constants
"""

# ── Process Names ─────────────────────────────────────────
PROC_CAPTURE       = "capture"
PROC_MOTION        = "motion"
PROC_DETECTION     = "detection"
PROC_TRACKING      = "tracking"
PROC_RECORDING     = "recording"
PROC_EVENT         = "event"
PROC_API           = "api"
PROC_MQTT          = "mqtt"

# ── Queue Sizes ───────────────────────────────────────────
FRAME_QUEUE_SIZE        = 10
MOTION_QUEUE_SIZE       = 10
DETECTION_QUEUE_SIZE    = 20
TRACKING_QUEUE_SIZE     = 20
EVENT_QUEUE_SIZE        = 50
RECORD_QUEUE_SIZE       = 50

# ── Detection ─────────────────────────────────────────────
DEFAULT_CONFIDENCE      = 0.45
DEFAULT_IOU             = 0.45
DEFAULT_MODEL           = "yolo11n.pt"
DETECTION_POOL_SIZE     = 2         # number of detector workers

# ── Motion ────────────────────────────────────────────────
MOG2_HISTORY            = 500
MOG2_VAR_THRESHOLD      = 16
MIN_CONTOUR_AREA        = 1500
MOTION_COOLDOWN_S       = 0.2       # seconds between motion triggers (~5 FPS detect rate)

# ── Recording ─────────────────────────────────────────────
DEFAULT_PRE_CAPTURE_S   = 3
DEFAULT_POST_CAPTURE_S  = 8
DEFAULT_MAX_CLIP_S      = 60
DEFAULT_FPS             = 10
DEFAULT_CRF             = 23
DEFAULT_CODEC           = "libx264"

# ── Tracking ──────────────────────────────────────────────
TRACK_MAX_DISAPPEARED   = 5         # frames before object removed (~1s at 5 FPS)
TRACK_MAX_DISTANCE      = 80        # pixels — tighter matching avoids duplicates

# ── Retention ─────────────────────────────────────────────
DEFAULT_RETAIN_DAYS     = 7

# ── MQTT ──────────────────────────────────────────────────
MQTT_TOPIC_DETECTION    = "raaqib/{camera_id}/detection"
MQTT_TOPIC_MOTION       = "raaqib/{camera_id}/motion"
MQTT_TOPIC_RECORDING    = "raaqib/{camera_id}/recording"
MQTT_TOPIC_STATUS       = "raaqib/status"

# ── API ───────────────────────────────────────────────────
API_HOST                = "0.0.0.0"
API_PORT                = 8000

# ── Database ──────────────────────────────────────────────
DB_PATH                 = "raaqib.db"

# ── Storage dirs ──────────────────────────────────────────
DIR_RECORDINGS          = "recordings"
DIR_SNAPSHOTS           = "snapshots"
DIR_CLIPS               = "clips"

# ── Frame ─────────────────────────────────────────────────
DEFAULT_WIDTH           = 1280
DEFAULT_HEIGHT          = 720

# ── Event lifecycle ───────────────────────────────────────
EVENT_MIN_SCORE         = 0.5
EVENT_STATIONARY_S      = 10.0

# ── Object classes (COCO) ─────────────────────────────────
TRACKED_CLASSES = {
    0:  "person",
    1:  "bicycle",
    2:  "car",
    3:  "motorcycle",
    5:  "bus",
    7:  "truck",
    14: "bird",
    15: "cat",
    16: "dog",
}
