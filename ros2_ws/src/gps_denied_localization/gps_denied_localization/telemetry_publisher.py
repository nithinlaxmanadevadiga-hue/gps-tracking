"""
Ground-Station Telemetry Service.

Transmits structured JSON telemetry from the onboard localization computer
to the ground station over secure WebSocket or MQTT.
Supports TLS-ready communication and Bearer token authentication.
"""

import json
import time
import asyncio
import threading
from typing import Dict, Any, Optional
import urllib.request
import urllib.error


class TelemetryPublisher:
    def __init__(
        self,
        device_id: str,
        auth_token: str,
        server_url: str = "http://localhost:8000/api/telemetry",
        ws_url: Optional[str] = "ws://localhost:8000/ws/telemetry/ingest",
        mqtt_broker: Optional[str] = "localhost",
        mqtt_port: int = 1883,
        mqtt_topic: Optional[str] = None
    ):
        self.device_id = device_id
        self.auth_token = auth_token
        self.server_url = server_url
        self.ws_url = ws_url
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_topic = mqtt_topic or f"telemetry/{device_id}"

        self.last_sent_payload: Optional[Dict[str, Any]] = None
        self._mqtt_client = None
        self._init_mqtt()

    def _init_mqtt(self) -> None:

        try:
            import paho.mqtt.client as mqtt

            if hasattr(mqtt, "CallbackAPIVersion"):
                self._mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"agent_{self.device_id}")
            else:
                self._mqtt_client = mqtt.Client(client_id=f"agent_{self.device_id}")
            if self.auth_token:

                self._mqtt_client.username_pw_set(self.device_id, self.auth_token)
            # Non-blocking connection attempt
            def connect_worker():
                try:
                    self._mqtt_client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)
                    self._mqtt_client.loop_start()
                except Exception:
                    pass
            t = threading.Thread(target=connect_worker, daemon=True)
            t.start()
        except ImportError:
            pass

    @staticmethod
    def build_telemetry_message(
        device_id: str,
        timestamp: float,
        ref_lat: float,
        ref_lon: float,
        ref_alt: float,
        east: float,
        north: float,
        up: float,
        cur_lat: float,
        cur_lon: float,
        cur_alt: float,
        vel_e: float,
        vel_n: float,
        vel_u: float,
        roll: float,
        pitch: float,
        yaw: float,
        speed: float,
        heading: float,
        horiz_dist: float,
        dist_3d: float,
        accuracy: float,
        quality: str,
        reason: str,
        health_info: Optional[Dict[str, Any]] = None,
        is_simulation: bool = False
    ) -> Dict[str, Any]:
        """
        Creates telemetry structure conforming strictly to Section 8 of the specification.
        """
        msg = {
            "device_id": device_id,
            "timestamp": timestamp,
            "reference": {
                "latitude": round(ref_lat, 8),
                "longitude": round(ref_lon, 8),
                "altitude": round(ref_alt, 3)
            },
            "position": {
                "east": round(east, 3),
                "north": round(north, 3),
                "up": round(up, 3),
                "latitude": round(cur_lat, 8),
                "longitude": round(cur_lon, 8),
                "altitude": round(cur_alt, 3)
            },
            "velocity": {
                "east": round(vel_e, 3),
                "north": round(vel_n, 3),
                "up": round(vel_u, 3)
            },
            "orientation": {
                "roll": round(roll, 4),
                "pitch": round(pitch, 4),
                "yaw": round(yaw, 4)
            },
            "localization": {
                "source": "lidar_imu_ekf",
                "gps_available": False,
                "position_accuracy": round(accuracy, 3),
                "status": quality,
                "status_reason": reason,
                "heading_deg": round(heading, 1),
                "speed_mps": round(speed, 2),
                "horizontal_distance_m": round(horiz_dist, 2),
                "distance_3d_m": round(dist_3d, 2),
                "is_simulation": is_simulation
            }
        }
        if health_info:
            msg["health"] = health_info
        return msg

    def publish_http(self, payload: Dict[str, Any]) -> bool:
        """Synchronous HTTP POST fallback to Ground Station REST ingestion."""
        self.last_sent_payload = payload
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.server_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.auth_token}",
                "X-Device-ID": self.device_id
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                return resp.status in (200, 201)
        except Exception:
            return False

    def publish_mqtt(self, payload: Dict[str, Any]) -> bool:
        if self._mqtt_client and self._mqtt_client.is_connected():
            try:
                self._mqtt_client.publish(self.mqtt_topic, json.dumps(payload), qos=0)
                return True
            except Exception:
                return False
        return False
