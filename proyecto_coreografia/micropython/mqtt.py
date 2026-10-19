import json
import sys
import time

from umqtt.simple import MQTTClient

from task import Task


class MQTTTransport(Task):
    """Transporte MQTT para Node (reemplaza a PubSubMQTT en este taller).

    Diferencias con PubSubMQTT, pensadas para que la alarma funcione sola:
      * Nunca lanza excepciones al Scheduler: ante cualquier fallo cierra el socket
        y reintenta con espera creciente (2 s, 4 s ... 30 s).
      * Sin conexión, publish() descarta el mensaje en silencio. La alarma sigue
        decidiendo en el Pico; el estado se republica al reconectar.
      * Solo intenta conectar si hay WiFi y `should_defer()` es falso (p. ej. mientras
        alguien digita la clave), porque connect() puede bloquear hasta `connect_timeout_s`.
      * keepalive + ping para que el broker detecte la caída y publique el Last Will
        (`online: false`, retenido) que Flet usa para mostrar "Pico sin señal".
      * Acota los mensajes atendidos por vuelta (no monopoliza el Scheduler).
      * Publica con retain los tópicos de `retain_topics`.
      * Serializa a JSON cualquier dato que no sea str/bytes (PubSubMQTT fallaba con int).
    """

    def __init__(
        self,
        scheduler,
        node,
        wifi,
        client_id,
        broker,
        prefix,
        port=1883,
        period_ms=100,
        keepalive_s=30,
        connect_timeout_s=3,
        retry_min_ms=2000,
        retry_max_ms=30000,
        max_msgs_per_cycle=5,
        retain_topics=(),
        online_topic="node/online",
        should_defer=None,
        on_connect=None,
    ):
        super().__init__(scheduler, period_ms, name="MQTTTransport")
        self.node = node
        self.wifi = wifi
        self.client_id = client_id
        self.broker = broker
        self.port = port
        self.prefix = prefix
        self.keepalive_s = keepalive_s
        self.connect_timeout_s = connect_timeout_s
        self.retry_min_ms = retry_min_ms
        self.retry_max_ms = retry_max_ms
        self.max_msgs_per_cycle = max_msgs_per_cycle
        self.retain_topics = retain_topics
        self.online_topic = online_topic
        self.should_defer = should_defer
        self.on_connect = on_connect

        self.client = None
        self.connected = False
        self._topics = set()
        self._retry_ms = retry_min_ms
        self._next_try = time.ticks_ms()
        self._last_ping = time.ticks_ms()
        self._ping_ms = keepalive_s * 1000 // 3

        node.add_transport(self)

    # ------------------------------------------------- interfaz que espera Node

    def publish(self, topic, data):
        if not self.connected:
            return
        if not isinstance(data, (str, bytes)):
            data = json.dumps(data)
        try:
            self.client.publish(
                (self.prefix + topic).encode(),
                data,
                retain=topic in self.retain_topics,
            )
        except Exception as e:
            self._drop("publish", e)

    def subscribe(self, topic):
        self._topics.add(topic)
        if not self.connected:
            return  # se suscribe al (re)conectar
        try:
            self.client.subscribe((self.prefix + topic).encode())
        except Exception as e:
            self._drop("subscribe", e)

    # ------------------------------------------------------------ ciclo de vida

    def update(self):
        now = time.ticks_ms()

        if not self.connected:
            if not self.wifi.connected:
                return
            if time.ticks_diff(now, self._next_try) < 0:
                return
            if self.should_defer is not None and self.should_defer():
                return
            self._connect(now)
            return

        try:
            for _ in range(self.max_msgs_per_cycle):
                if self.client.check_msg() is None:
                    break
            if time.ticks_diff(now, self._last_ping) >= self._ping_ms:
                self.client.ping()
                self._last_ping = now
        except Exception as e:
            self._drop("update", e)

    def _connect(self, now):
        try:
            client = MQTTClient(
                self.client_id,
                self.broker,
                port=self.port,
                keepalive=self.keepalive_s,
            )
            # Se guarda ANTES de conectar: si connect() falla a medias, _drop() debe
            # poder cerrar el socket (en lwIP hay pocos y cada reintento agotaría el cupo).
            self.client = client
            client.set_callback(self._on_message)
            client.set_last_will(
                (self.prefix + self.online_topic).encode(),
                json.dumps({"online": False, "node": self.client_id}),
                retain=True,
            )
            client.connect(timeout=self.connect_timeout_s)

            for topic in self._topics:
                client.subscribe((self.prefix + topic).encode())

            self.connected = True
            self._retry_ms = self.retry_min_ms
            self._last_ping = time.ticks_ms()
            print("MQTT conectado a", self.broker)

            self.publish(self.online_topic, {"online": True, "node": self.client_id})
            if self.on_connect is not None:
                self.on_connect()
        except Exception as e:
            self._drop("connect", e)

    def _drop(self, where, error):
        """Cierra la conexión y programa el reintento. Nunca propaga la excepción."""
        print("MQTT: fallo en", where, "-", error, "- reintento en", self._retry_ms, "ms")
        try:
            if self.client is not None and self.client.sock is not None:
                self.client.sock.close()
        except Exception:
            pass
        self.client = None
        self.connected = False
        self._next_try = time.ticks_add(time.ticks_ms(), self._retry_ms)
        self._retry_ms = min(self._retry_ms * 2, self.retry_max_ms)

    def _on_message(self, topic, payload):
        try:
            topic = topic.decode()
            if not topic.startswith(self.prefix):
                return
            local_topic = topic[len(self.prefix):]
            try:
                data = json.loads(payload.decode("utf-8"))
            except Exception:
                data = payload
            self.node.local_publish(local_topic, data)
        except Exception as e:
            # Un mensaje malo no debe tumbar la conexión.
            sys.print_exception(e)
