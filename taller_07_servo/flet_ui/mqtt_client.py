"""Cliente MQTT de la interfaz (paho-mqtt 2.x): solo publica comandos de servo
y avisa si está conectado al broker. No necesita suscribirse a nada porque
este taller no tiene telemetría de vuelta (a diferencia del taller 05).
"""

import json
import uuid
from typing import Callable

import paho.mqtt.client as mqtt


class MqttClient:

    def __init__(
        self,
        broker: str,
        port: int,
        on_link: Callable[[bool, str], None],
    ):
        self.broker = broker
        self.port = port
        self._on_link_cb = on_link

        # id único: en un broker público, dos clientes con el mismo id se expulsan entre sí
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"servo_ui_{uuid.uuid4().hex[:10]}",
        )
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

    def start(self) -> None:
        self._client.connect_async(self.broker, self.port, keepalive=30)
        self._client.loop_start()

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    def publish(self, topic: str, payload: dict, retain: bool = False) -> None:
        self._client.publish(topic, json.dumps(payload), retain=retain)

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code.is_failure:
            self._on_link_cb(False, str(reason_code))
            return
        self._on_link_cb(True, self.broker)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties) -> None:
        self._on_link_cb(False, str(reason_code))
