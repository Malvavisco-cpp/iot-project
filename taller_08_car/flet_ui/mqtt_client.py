"""Cliente MQTT de la interfaz (paho-mqtt 2.x): publica car/cmd y car/stop,
y escucha car/state para mostrar si el carro se está moviendo.

Los callbacks llegan desde el hilo propio de paho, no desde el de Flet: quien
los recibe debe actualizar la UI con page.run_thread() (ver flet_ui/main.py).
"""

import json
import uuid

import paho.mqtt.client as mqtt


class MqttClient:

    def __init__(self, broker, port, topics, on_message, on_link):
        """
        topics:                       tópicos COMPLETOS (con prefijo) a escuchar.
        on_message(topic, payload):   llega un mensaje.
        on_link(connected, detail):   cambió la conexión con el broker.
        """
        self.broker = broker
        self.port = port
        self.topics = topics
        self._on_message_cb = on_message
        self._on_link_cb = on_link

        # id único: en un broker público, dos clientes con el mismo id se expulsan entre sí
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"car_ui_{uuid.uuid4().hex[:10]}",
        )
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def start(self):
        self._client.connect_async(self.broker, self.port, keepalive=30)
        self._client.loop_start()

    def stop(self):
        self._client.loop_stop()
        self._client.disconnect()

    def publish(self, topic, payload):
        self._client.publish(topic, json.dumps(payload))

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            self._on_link_cb(False, str(reason_code))
            return
        # Aquí (no en start) para que también se suscriba tras cada reconexión.
        for topic in self.topics:
            client.subscribe(topic)
        self._on_link_cb(True, self.broker)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        self._on_link_cb(False, str(reason_code))

    def _on_message(self, client, userdata, message):
        self._on_message_cb(message.topic, message.payload)
