"""
Raaqib NVR — Object Tracking Process
Assigns persistent track IDs to detected objects across frames.
Uses centroid-based tracking (fast, no deep learning needed).
"""

from __future__ import annotations
import time
import logging
import multiprocessing as mp
import numpy as np
from collections import OrderedDict
from scipy.spatial import distance as dist

from camera.camera import FramePacket, TrackedObject, DetectionResult
from const import TRACK_MAX_DISAPPEARED, TRACK_MAX_DISTANCE

logger = logging.getLogger(__name__)


class CentroidTracker:
    """
    Simple centroid-based multi-object tracker.
    Assigns persistent IDs to objects across frames using nearest centroid matching.
    """

    def __init__(self, max_disappeared: int = TRACK_MAX_DISAPPEARED,
                 max_distance: float = TRACK_MAX_DISTANCE):
        self.next_id = 0
        self.objects: OrderedDict[int, TrackedObject] = OrderedDict()
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance

    def _centroid(self, bbox: tuple) -> tuple:
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    def update(self, detections: list[DetectionResult]) -> list[TrackedObject]:
        """Update tracker with new detections. Returns current tracked objects."""

        # Mark all as disappeared
        for obj in self.objects.values():
            obj.disappeared += 1

        if not detections:
            # Remove objects gone too long
            to_delete = [oid for oid, obj in self.objects.items()
                         if obj.disappeared > self.max_disappeared]
            for oid in to_delete:
                del self.objects[oid]
            return list(self.objects.values())

        new_centroids = np.array([self._centroid(d.bbox) for d in detections])

        if not self.objects:
            # Register all new detections
            for det in detections:
                self._register(det)
        else:
            obj_ids = list(self.objects.keys())
            obj_centroids = np.array([obj.centroid for obj in self.objects.values()])

            # Compute distance matrix
            D = dist.cdist(obj_centroids, new_centroids)

            # Match: sort rows by min distance
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            used_rows, used_cols = set(), set()

            for row, col in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue
                if D[row, col] > self.max_distance:
                    continue

                obj_id = obj_ids[row]
                det = detections[col]
                self.objects[obj_id].update(det.bbox, det.confidence)
                used_rows.add(row)
                used_cols.add(col)

            # Unmatched existing objects — already incremented disappeared above
            for row in set(range(D.shape[0])) - used_rows:
                obj_id = obj_ids[row]
                if self.objects[obj_id].disappeared > self.max_disappeared:
                    del self.objects[obj_id]

            # Unmatched new detections — register
            for col in set(range(len(detections))) - used_cols:
                self._register(detections[col])

        return list(self.objects.values())

    def _register(self, det: DetectionResult):
        obj = TrackedObject(
            track_id=self.next_id,
            label=det.label,
            confidence=det.confidence,
            bbox=det.bbox,
            camera_id=det.camera_id,
        )
        cx = (det.bbox[0] + det.bbox[2]) // 2
        cy = (det.bbox[1] + det.bbox[3]) // 2
        obj.centroid = (cx, cy)
        self.objects[self.next_id] = obj
        self.next_id += 1


def tracking_process(
    in_queue: mp.Queue,          # receives FramePackets from detector
    event_queue: mp.Queue,       # sends track events to event processor
    record_queue: mp.Queue,      # sends packets to recorder
    state_dict: dict,
    stop_event: mp.Event,
):
    """Tracking process entry point — one tracker per camera, shared process."""
    logging.basicConfig(level=logging.INFO,
                        format="[Tracker] %(levelname)s %(message)s")

    # Per-camera trackers
    trackers: dict[str, CentroidTracker] = {}

    logger.info("Tracking process started")

    while not stop_event.is_set():
        try:
            packet: FramePacket = in_queue.get(timeout=1.0)
        except Exception:
            continue

        cam_id = packet.camera_id

        if cam_id not in trackers:
            trackers[cam_id] = CentroidTracker()

        tracker = trackers[cam_id]
        tracked = tracker.update(packet.detections)
        packet.tracked_objects = tracked

        # Update camera state with active track count
        try:
            cam_state = state_dict.get(cam_id, {})
            cam_state["active_tracks"] = len(tracked)
            cam_state["detection_count"] = cam_state.get("detection_count", 0) + len(packet.detections)
            state_dict[cam_id] = cam_state
        except Exception:
            pass

        # Push to event processor if there are tracked objects
        if tracked:
            try:
                event_queue.put_nowait({
                    "type": "tracks",
                    "camera_id": cam_id,
                    "timestamp": packet.timestamp,
                    "objects": [o.to_dict() for o in tracked],
                })
            except Exception:
                pass

        # Forward to recorder
        try:
            record_queue.put_nowait(packet)
        except Exception:
            pass

    logger.info("Tracking process stopped")
