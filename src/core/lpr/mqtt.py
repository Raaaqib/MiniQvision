"""
LPR MQTT Publisher — publishes LPR results to the existing Raaqib MQTT broker.

Topics
------
raaqib/lpr/<camera_id>/plate        — every recognised plate
raaqib/lpr/<camera_id>/alert        — unknown plate alerts only
raaqib/lpr/<camera_id>/zone/<zone>  — per-zone events

Payload (JSON)
--------------
{
  "camera_id":   "cam1",
  "zone_id":     "lpr_zone_1",
  "plate":       "ABC123",
  "confidence":  0.92,
  "known":       false,
  "alert":       true,
  "snapshot":    "snapshots/lpr/cam1_ABC123_20240101_120000.jpg",
  "timestamp":   "2024-01-01T12:00:00+00:00"
}
"""

from __future__ import annotations
import json
import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .pipeline import LPRResult

logger = logging.getLogger(__name__)

BASE_TOPIC = "raaqib/lpr"


class LPRMQTTPublisher:
    """
    Wraps Raaqib's existing MQTT client to publish LPR events.

    Parameters
    ----------
    mqtt_client : any
        The existing Raaqib MQTT client instance (must have a .publish(topic, payload) method).
        Pass None to disable publishing.
    qos : int
        MQTT QoS level (default 1 — at least once).
    retain : bool
        Whether to retain the last plate message per camera.
    """

    def __init__(self, mqtt_client=None, qos: int = 1, retain: bool = False):
        self._client = mqtt_client
        self.qos = qos
        self.retain = retain

        if mqtt_client is None:
            logger.info("[LPR] MQTT publisher disabled (no client provided)")
        else:
            logger.info("[LPR] MQTT publisher ready")

    # ------------------------------------------------------------------
    def publish(self, result: "LPRResult"):
        if self._client is None:
            return

        payload = json.dumps(result.to_dict(), default=str)

        # Always publish to the general plate topic
        self._send(f"{BASE_TOPIC}/{result.camera_id}/plate", payload)

        # Also publish to zone-specific topic
        self._send(f"{BASE_TOPIC}/{result.camera_id}/zone/{result.zone_id}", payload)

        # Publish to alert topic only for unknown plates
        if result.alert:
            self._send(f"{BASE_TOPIC}/{result.camera_id}/alert", payload)
            logger.warning(
                f"[LPR] ALERT — unknown plate '{result.plate}' "
                f"on {result.camera_id}/{result.zone_id}"
            )

    # ------------------------------------------------------------------
    def _send(self, topic: str, payload: str):
        try:
            self._client.publish(topic, payload, qos=self.qos, retain=self.retain)
            logger.debug(f"[LPR] MQTT → {topic}")
        except Exception as e:
            logger.warning(f"[LPR] MQTT publish failed ({topic}): {e}")
