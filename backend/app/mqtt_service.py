import json
import logging
import asyncio
from typing import Optional
from .config import settings
from .telemetry_hub import hub

logger = logging.getLogger("mqtt_service")


class MqttService:
    def __init__(self):
        self.client = None
        self.loop = None

    def start(self, loop: asyncio.AbstractEventLoop):
        if not settings.MQTT_ENABLE:
            return

        try:
            import paho.mqtt.client as mqtt

            self.loop = loop
            if hasattr(mqtt, "CallbackAPIVersion"):
                self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="gps_denied_ground_station")
            else:
                self.client = mqtt.Client(client_id="gps_denied_ground_station")


            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    logger.info("Connected to MQTT Broker")
                    client.subscribe(settings.MQTT_TOPIC)
                else:
                    logger.warning(f"MQTT connect failed with rc={rc}")

            def on_message(client, userdata, msg):
                try:
                    payload = json.loads(msg.payload.decode("utf-8"))
                    asyncio.run_coroutine_threadsafe(
                        hub.broadcast_telemetry(payload),
                        self.loop
                    )
                except Exception as e:
                    logger.error(f"Failed to process MQTT payload: {e}")

            self.client.on_connect = on_connect
            self.client.on_message = on_message

            self.client.connect_async(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
            self.client.loop_start()
        except ImportError:
            logger.info("paho-mqtt not available, MQTT service disabled")
        except Exception as e:
            logger.warning(f"MQTT initialization exception: {e}")

    def stop(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()


mqtt_service = MqttService()
