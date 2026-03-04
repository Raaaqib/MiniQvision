"""
Raaqib NVR — MQTT Publisher Process
Publishes detection events, motion alerts, and system status to MQTT broker.
"""

from __future__ import annotations
import json
import time
import logging
import multiprocessing as mp

from config import MQTTConfig
from const import (
    MQTT_TOPIC_DETECTION, MQTT_TOPIC_MOTION,
    MQTT_TOPIC_RECORDING, MQTT_TOPIC_STATUS
)

logger = logging.getLogger(__name__)


def mqtt_process(
    config: MQTTConfig,
    mqtt_queue: mp.Queue,
    stop_event: mp.Event,
):
    """MQTT publisher process entry point."""
    from log_utils import configure_logging
    configure_logging("mqtt")

    if not config.enabled:
        logger.info("MQTT disabled in config — process idle")
        while not stop_event.is_set():
            try:
                mqtt_queue.get(timeout=1.0)
            except Exception:
                pass
        return

    client = _connect(config)
    if client is None:
        logger.error("MQTT connection failed — publisher exiting")
        return

    logger.info(f"MQTT connected to {config.host}:{config.port}")

    while not stop_event.is_set():
        try:
            msg = mqtt_queue.get(timeout=1.0)
        except Exception:
            continue

        try:
            _publish(client, config, msg)
        except Exception as e:
            logger.warning(f"MQTT publish error: {e}")
            client = _reconnect(client, config)

    client.disconnect()
    logger.info("MQTT process stopped")


def _connect(config: MQTTConfig):
    try:
        import paho.mqtt.client as mqtt

        client = mqtt.Client(client_id=config.client_id)

        if config.username:
            client.username_pw_set(config.username, config.password)
        if config.tls:
            client.tls_set()

        client.connect(config.host, config.port, keepalive=60)
        client.loop_start()
        return client
    except ImportError:
        logger.error("paho-mqtt not installed. Run: pip install paho-mqtt")
        return None
    except Exception as e:
        logger.error(f"MQTT connect error: {e}")
        return None


def _reconnect(client, config: MQTTConfig, retries: int = 5):
    for i in range(retries):
        try:
            client.reconnect()
            logger.info("MQTT reconnected")
            return client
        except Exception as e:
            logger.warning(f"Reconnect attempt {i+1} failed: {e}")
            time.sleep(2 ** i)
    logger.error("MQTT reconnect failed — giving up")
    return client


def _publish(client, config: MQTTConfig, msg: dict):
    event_type = msg.get("event_type", "unknown")
    data = msg.get("data", {})
    camera_id = data.get("camera_id", "unknown")

    topic_map = {
        "event_start":  MQTT_TOPIC_DETECTION.format(camera_id=camera_id),
        "event_update": MQTT_TOPIC_DETECTION.format(camera_id=camera_id),
        "event_end":    MQTT_TOPIC_DETECTION.format(camera_id=camera_id),
        "motion":       MQTT_TOPIC_MOTION.format(camera_id=camera_id),
        "recording":    MQTT_TOPIC_RECORDING.format(camera_id=camera_id),
        "status":       MQTT_TOPIC_STATUS,
    }

    topic = topic_map.get(event_type, f"raaqib/events/{event_type}")
    payload = json.dumps({
        "event": event_type,
        "timestamp": time.time(),
        **data
    })

    client.publish(topic, payload, qos=1, retain=False)
    logger.debug(f"Published → {topic}: {event_type}")
