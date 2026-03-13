# RAAQIB NVR — REST API Documentation

Complete reference for Raaqib's REST API endpoints and integrations.

## Quick Reference

**Base URL**: `http://localhost:8000`

**Interactive Docs**: `http://localhost:8000/docs`

**OpenAPI Schema**: `http://localhost:8000/openapi.json`

## Table of Contents

- [Status Endpoints](#status-endpoints)
- [Camera Endpoints](#camera-endpoints)
- [Event Endpoints](#event-endpoints)
- [Recording Endpoints](#recording-endpoints)
- [Snapshot Endpoints](#snapshot-endpoints)
- [Authentication](#authentication)
- [MQTT Integration](#mqtt-integration)
- [Error Handling](#error-handling)
- [Rate Limits](#rate-limits)
- [Examples](#examples)

---

## Status Endpoints

### GET /api/status

**System Health & Statistics**

Returns overall system health, resource usage, and summary statistics.

**Request**:
```bash
curl http://localhost:8000/api/status
```

**Response** (200 OK):
```json
{
  "status": "running",
  "uptime_seconds": 3600,
  "timestamp": "2024-03-04T10:30:45.123Z",
  "system": {
    "cpu_percent": 15.2,
    "memory_percent": 28.5,
    "memory_mb": 450,
    "disk_free_gb": 250.3
  },
  "cameras": {
    "camera1": {
      "status": "connected",
      "fps": 10.0,
      "frames_captured": 36000,
      "frames_dropped": 5,
      "uptime_seconds": 3600
    },
    "camera2": {
      "status": "disconnected",
      "error": "Connection timeout"
    }
  },
  "detection": {
    "total_detections": 127,
    "detections_last_hour": 15,
    "active_events": 2
  },
  "storage": {
    "recordings_count": 42,
    "snapshots_count": 158,
    "total_size_mb": 2340.5
  }
}
```

**Fields**:
- `status`: `"running"`, `"starting"`, `"stopping"`, `"error"`
- `uptime_seconds`: System uptime since startup
- `system.cpu_percent`: CPU utilization (0-100)
- `system.memory_percent`: RAM utilization
- `cameras[id].status`: `"connected"`, `"disconnected"`, `"error"`
- `detection.active_events`: Currently active detection events

---

## Camera Endpoints

### GET /api/cameras

**List All Cameras**

Returns status of all configured cameras.

**Request**:
```bash
curl http://localhost:8000/api/cameras
```

**Response** (200 OK):
```json
{
  "cameras": [
    {
      "id": "camera1",
      "name": "Front Door",
      "source": "rtsp://192.168.1.100:554/stream1",
      "enabled": true,
      "status": "connected",
      "fps": 10.0,
      "resolution": "1280x720",
      "frames_captured": 36000,
      "frames_dropped": 5,
      "last_frame_time": "2024-03-04T10:30:45.123Z",
      "detections_count": 42,
      "last_detection": "2024-03-04T10:25:30.456Z"
    },
    {
      "id": "camera2",
      "name": "Back Porch",
      "source": 0,
      "enabled": false,
      "status": "disconnected",
      "error": "Camera not found or disconnected"
    }
  ]
}
```

---

### GET /api/cameras/{camera_id}

**Get Single Camera Status**

Get detailed status of a specific camera.

**Request**:
```bash
curl http://localhost:8000/api/cameras/camera1
```

**Response** (200 OK):
```json
{
  "id": "camera1",
  "name": "Front Door",
  "source": "rtsp://192.168.1.100:554/stream1",
  "enabled": true,
  "status": "connected",
  "fps": 10.0,
  "resolution": "1280x720",
  "frames_captured": 36000,
  "frames_dropped": 5,
  "dropped_percent": 0.014,
  "uptime_seconds": 3600,
  "last_frame_time": "2024-03-04T10:30:45.123Z",
  "last_frame_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
  "detections": {
    "count_total": 42,
    "count_today": 3,
    "count_this_hour": 0,
    "last_detection": {
      "time": "2024-03-04T10:25:30.456Z",
      "class": "person",
      "confidence": 0.89,
      "bbox": [100, 200, 150, 320]
    }
  },
  "statistics": {
    "average_fps": 9.8,
    "min_fps": 7.2,
    "max_fps": 10.1
  }
}
```

---

### GET /api/cameras/{camera_id}/frame

**Get Latest Frame as JPEG**

Returns the most recent frame from a camera as JPEG image (useful for dashboards).

**Request**:
```bash
curl http://localhost:8000/api/cameras/camera1/frame -o latest_frame.jpg
```

**Response** (200 OK):
```
[JPEG binary data]
```

**Query Parameters**:
- `width` (int, optional): Resize to width (maintains aspect ratio)
- `quality` (int, optional): JPEG quality 1-100 (default: 85)

**Example with parameters**:
```bash
curl "http://localhost:8000/api/cameras/camera1/frame?width=320&quality=75" -o thumb.jpg
```

---

## Event Endpoints

### GET /api/events

**Event History**

Get historical detection events with optional filtering.

**Request**:
```bash
curl "http://localhost:8000/api/events?limit=50&offset=0"
```

**Response** (200 OK):
```json
{
  "total": 127,
  "limit": 50,
  "offset": 0,
  "events": [
    {
      "id": "evt_20240304_103045_001",
      "camera_id": "camera1",
      "start_time": "2024-03-04T10:30:45.123Z",
      "end_time": "2024-03-04T10:30:52.456Z",
      "duration_seconds": 7.333,
      "objects": [
        {
          "id": 5,
          "class": "person",
          "confidence": 0.89,
          "first_seen": "2024-03-04T10:30:45.123Z",
          "last_seen": "2024-03-04T10:30:52.456Z",
          "bbox_first": [100, 200, 150, 320],
          "bbox_last": [120, 210, 170, 330],
          "frames_seen": 42
        }
      ],
      "snapshot_file": "camera1/2024-03-04/10-30-45_person.jpg",
      "clip_file": "camera1/2024-03-04/10-30-45.mp4"
    }
  ]
}
```

**Query Parameters**:
- `limit` (int, optional): Max events to return (default: 50, max: 1000)
- `offset` (int, optional): Pagination offset (default: 0)
- `camera_id` (str, optional): Filter by camera
- `start_time` (ISO 8601, optional): Filter events after this time
- `end_time` (ISO 8601, optional): Filter events before this time
- `class_filter` (str, optional): Filter by object class (e.g., "person", "car")

**Examples**:
```bash
# Last 100 events
curl "http://localhost:8000/api/events?limit=100"

# Events from today
curl "http://localhost:8000/api/events?start_time=2024-03-04T00:00:00Z&end_time=2024-03-04T23:59:59Z"

# Person detections from a specific camera
curl "http://localhost:8000/api/events?camera_id=camera1&class_filter=person"
```

---

### GET /api/events/active

**Active Events**

Get currently active (ongoing) detection events.

**Request**:
```bash
curl http://localhost:8000/api/events/active
```

**Response** (200 OK):
```json
{
  "active_events": [
    {
      "id": "evt_20240304_103045_002",
      "camera_id": "camera1",
      "start_time": "2024-03-04T10:30:45.123Z",
      "duration_seconds": 45.678,
      "objects": [
        {
          "id": 3,
          "class": "person",
          "confidence": 0.92,
          "first_seen": "2024-03-04T10:30:45.123Z",
          "current_bbox": [150, 250, 200, 400]
        }
      ]
    }
  ]
}
```

---

### GET /api/events/{event_id}

**Get Specific Event Details**

Get complete details of a single event.

**Request**:
```bash
curl http://localhost:8000/api/events/evt_20240304_103045_001
```

**Response** (200 OK):
```json
{
  "id": "evt_20240304_103045_001",
  "camera_id": "camera1",
  "start_time": "2024-03-04T10:30:45.123Z",
  "end_time": "2024-03-04T10:30:52.456Z",
  "duration_seconds": 7.333,
  "objects": [
    {
      "id": 5,
      "class": "person",
      "confidence": 0.89,
      "first_seen": "2024-03-04T10:30:45.123Z",
      "last_seen": "2024-03-04T10:30:52.456Z",
      "movement": {
        "start_bbox": [100, 200, 150, 320],
        "end_bbox": [120, 210, 170, 330],
        "distance_pixels": 45.2,
        "direction": "right_down"
      },
      "frames_seen": 42
    }
  ],
  "motion_summary": {
    "motion_duration": 7.3,
    "max_motion_score": 0.35,
    "motion_frames": 42
  },
  "snapshot_file": "camera1/2024-03-04/10-30-45_person.jpg",
  "clip_file": "camera1/2024-03-04/10-30-45.mp4"
}
```

---

## Recording Endpoints

### GET /api/recordings

**List Video Clips**

List all recorded video clips.

**Request**:
```bash
curl "http://localhost:8000/api/recordings?limit=20"
```

**Response** (200 OK):
```json
{
  "total": 42,
  "recordings": [
    {
      "file": "camera1/2024-03-04/10-30-45.mp4",
      "camera_id": "camera1",
      "start_time": "2024-03-04T10:30:45.123Z",
      "end_time": "2024-03-04T10:30:52.456Z",
      "duration_seconds": 7.333,
      "size_mb": 3.4,
      "fps": 10.0,
      "resolution": "1280x720",
      "event_id": "evt_20240304_103045_001"
    }
  ]
}
```

**Query Parameters**:
- `limit` (int, optional): Max clips to return (default: 50)
- `offset` (int, optional): Pagination offset
- `camera_id` (str, optional): Filter by camera
- `start_time` (ISO 8601, optional): Clips after this time
- `end_time` (ISO 8601, optional): Clips before this time

---

### GET /api/recordings/{file_path}

**Download Video Clip**

Download a specific video clip file.

**Request**:
```bash
curl http://localhost:8000/api/recordings/camera1/2024-03-04/10-30-45.mp4 \
  -o recording.mp4
```

**Response** (200 OK):
```
[MP4 binary data]
```

**Headers**:
- `Content-Type`: `video/mp4`
- `Content-Length`: File size in bytes
- `Content-Disposition`: Attachment with filename

---

### DELETE /api/recordings/{file_path}

**Delete Video Clip**

Delete a specific recorded clip.

**Request**:
```bash
curl -X DELETE http://localhost:8000/api/recordings/camera1/2024-03-04/10-30-45.mp4
```

**Response** (204 No Content):
```
(empty)
```

---

## Snapshot Endpoints

### GET /api/snapshots

**List Detection Snapshots**

List all saved detection snapshots.

**Request**:
```bash
curl "http://localhost:8000/api/snapshots?limit=50"
```

**Response** (200 OK):
```json
{
  "total": 158,
  "snapshots": [
    {
      "file": "camera1/2024-03-04/10-30-45_person.jpg",
      "camera_id": "camera1",
      "timestamp": "2024-03-04T10:30:45.123Z",
      "class": "person",
      "confidence": 0.89,
      "size_kb": 85,
      "event_id": "evt_20240304_103045_001"
    }
  ]
}
```

---

### GET /api/snapshots/{file_path}

**Download Snapshot Image**

Get a specific detection snapshot.

**Request**:
```bash
curl http://localhost:8000/api/snapshots/camera1/2024-03-04/10-30-45_person.jpg \
  -o snapshot.jpg
```

**Response** (200 OK):
```
[JPEG binary data]
```

---

### DELETE /api/snapshots/{file_path}

**Delete Snapshot**

Delete a specific snapshot.

**Request**:
```bash
curl -X DELETE http://localhost:8000/api/snapshots/camera1/2024-03-04/10-30-45_person.jpg
```

**Response** (204 No Content):

---

## Authentication

**Current Version**: No authentication (local network only)

For production deployments, add authentication via:

1. **Reverse Proxy** (nginx with basic auth):
   ```nginx
   location /api {
     auth_basic "Raaqib API";
     auth_basic_user_file /etc/nginx/raaqib.htpasswd;
     proxy_pass http://localhost:8000;
   }
   ```

2. **API Key Header**:
   ```bash
   curl -H "X-API-Key: your-secret-key" http://localhost:8000/api/status
   ```

3. **JWT Bearer Token**:
   ```bash
   curl -H "Authorization: Bearer <token>" http://localhost:8000/api/status
   ```

---

## MQTT Integration

### Publishing to MQTT

Raaqib publishes events to MQTT broker automatically. Configure in `config.yaml`:

```yaml
mqtt:
  enabled: true
  broker: "192.168.1.50"
  port: 1883
  username: "raaqib"
  password: "secure_pass"
  retain: true
```

### MQTT Topics

| Topic | Payload | Trigger |
|-------|---------|---------|
| `raaqib/{camera_id}/detection` | JSON event | Object detected |
| `raaqib/{camera_id}/motion` | JSON detection | Motion detected |
| `raaqib/{camera_id}/recording` | `{"status": "started\|stopped"}` | Recording lifecycle |
| `raaqib/status` | JSON system status | Every 60 seconds |

### Example Payloads

**Detection Event**:
```json
{
  "camera_id": "camera1",
  "timestamp": "2024-03-04T10:30:45.123Z",
  "event_id": "evt_20240304_103045_001",
  "objects": [
    {
      "id": 5,
      "class": "person",
      "confidence": 0.89,
      "bbox": [100, 200, 150, 320]
    }
  ]
}
```

**Home Assistant Integration**:
```yaml
automation:
  - alias: "Front door person detected"
    trigger:
      platform: mqtt
      topic: "raaqib/camera1/detection"
    condition:
      template: "{{ trigger.payload_json.objects | selectattr('class', 'equalto', 'person') | list | length > 0 }}"
    action:
      - service: notify.mobile_app_phone
        data:
          message: "Person detected at front door!"
```

---

## Error Handling

### Error Response Format

```json
{
  "detail": "Camera not found",
  "error_code": "CAMERA_NOT_FOUND",
  "status_code": 404,
  "timestamp": "2024-03-04T10:30:45.123Z"
}
```

### Common Error Codes

| Status | Code | Meaning |
|--------|------|---------|
| 400 | `INVALID_REQUEST` | Malformed request parameters |
| 404 | `NOT_FOUND` | Resource doesn't exist |
| 409 | `CONFLICT` | Operation conflicts (e.g., camera already enabled) |
| 500 | `INTERNAL_ERROR` | Server error, check logs |
| 503 | `SERVICE_UNAVAILABLE` | System starting up or shutting down |

---

## Rate Limits

**No hard limits** (designed for local network)

**Recommendations**:
- Max 100 requests/second per client IP
- Implement exponential backoff for retries
- Cache camera status (refresh every 5-10 seconds)
- Don't poll event list faster than 1 second

---

## Examples

### Python Client Example

```python
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

class RaaqibClient:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
    
    def get_status(self):
        """Get system status"""
        resp = requests.get(f"{self.base_url}/api/status")
        resp.raise_for_status()
        return resp.json()
    
    def get_cameras(self):
        """Get all cameras"""
        resp = requests.get(f"{self.base_url}/api/cameras")
        resp.raise_for_status()
        return resp.json()
    
    def get_active_events(self):
        """Get currently active detections"""
        resp = requests.get(f"{self.base_url}/api/events/active")
        resp.raise_for_status()
        return resp.json()
    
    def get_events_today(self, camera_id=None):
        """Get today's events"""
        now = datetime.now()
        start_time = now.replace(hour=0, minute=0, second=0).isoformat() + "Z"
        end_time = now.isoformat() + "Z"
        
        params = {
            "start_time": start_time,
            "end_time": end_time,
            "limit": 100
        }
        if camera_id:
            params["camera_id"] = camera_id
        
        resp = requests.get(f"{self.base_url}/api/events", params=params)
        resp.raise_for_status()
        return resp.json()
    
    def download_clip(self, file_path, output_path):
        """Download a video clip"""
        url = f"{self.base_url}/api/recordings/{file_path}"
        resp = requests.get(url, stream=True)
        resp.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

# Usage
client = RaaqibClient()

# Check system status
status = client.get_status()
print(f"System uptime: {status['uptime_seconds']}s")
print(f"CPU: {status['system']['cpu_percent']}%")

# Get today's detections
events = client.get_events_today(camera_id="camera1")
print(f"Detections today: {len(events['events'])}")

# Download latest clip
if events['events']:
    latest = events['events'][0]
    if latest.get('clip_file'):
        client.download_clip(latest['clip_file'], "latest_detection.mp4")
```

### cURL Examples

```bash
# Check system health
curl http://localhost:8000/api/status | jq .

# Get all cameras
curl http://localhost:8000/api/cameras | jq .

# Get active events
curl http://localhost:8000/api/events/active | jq .

# Filter person detections from last hour
curl "http://localhost:8000/api/events?class_filter=person&limit=100" | jq .

# Download latest snapshot
curl http://localhost:8000/api/snapshots \
  | jq -r '.snapshots[0].file' \
  | xargs -I {} curl -o snapshot.jpg "http://localhost:8000/api/snapshots/{}"

# Monitor system in real-time
watch -n 1 'curl -s http://localhost:8000/api/status | jq -r "\(.system.cpu_percent)% CPU, \(.system.memory_percent)% RAM"'
```

---

## Next Steps

- [Running the System](RUNNING.md)
- [Configuration Reference](CONFIGURATION.md)
- [MQTT Integration](README.md#mqtt-integration)
