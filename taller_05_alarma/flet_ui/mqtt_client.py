"""Cliente MQTT de la interfaz (paho-mqtt 2.x). Solo escucha: Flet no publica nada."""

import uuid
from typing import Callable

import paho.mqtt.client as mqtt


class MqttClient:

    def __init__(
        self,
        broker: str,
        port: int,
        topics: list[str],
        on_message: Callable[[str, bytes], None],
        on_link: Callable[[bool, str], None],
    ):
        """
        on_message(topic, payload): llega un mensaje.
        on_link(connected, detail): cambió la conexión con el broker.
        """
        self.broker = broker
        self.port = port
        self.topics = topics
        self._on_message_cb = on_message
        self._on_link_cb = on_link

        # id único: en un broker público, dos clientes con el mismo id se expulsan entre sí
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"alarm_ui_{uuid.uuid4().hex[:10]}",
        )
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def start(self) -> None:
        # connect_async + loop_start: no bloquea la ventana y reconecta solo.
        self._client.connect_async(self.broker, self.port, keepalive=30)
        self._client.loop_start()

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code.is_failure:
            self._on_link_cb(False, str(reason_code))
            return
        # Se suscribe aquí (no en start) para que también ocurra tras cada reconexión.
        for topic in self.topics:
            client.subscribe(topic)
        self._on_link_cb(True, self.broker)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties) -> None:
        self._on_link_cb(False, str(reason_code))

    def _on_message(self, client, userdata, message) -> None:
        self._on_message_cb(message.topic, message.payload)
