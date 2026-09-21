"""MQTTTransport: lo que garantiza que la red nunca tumba a la alarma."""

import json

import pytest

import mqtt
from common import messages

PREFIX = "UDFJC/iot_ws/robot0/"


class FakeScheduler:
    def __init__(self):
        self.tasks = []

    def add(self, task):
        self.tasks.append(task)


class FakeNode:
    def __init__(self):
        self.transports = []
        self.received = []
        self.raise_on_local_publish = False

    def add_transport(self, transport):
        self.transports.append(transport)

    def local_publish(self, topic, msg, ts=None):
        if self.raise_on_local_publish:
            raise RuntimeError("callback roto")
        self.received.append((topic, msg))


class FakeWiFi:
    def __init__(self, connected=True):
        self.connected = connected


class Setup:
    def __init__(self, wifi_up=True, **kwargs):
        self.node = FakeNode()
        self.wifi = FakeWiFi(wifi_up)
        self.transport = mqtt.MQTTTransport(
            FakeScheduler(),
            self.node,
            self.wifi,
            client_id="alarm_node_abc",
            broker="broker.test",
            prefix=PREFIX,
            retain_topics=messages.RETAINED_TOPICS,
            **kwargs,
        )

    def client(self):
        return self.transport.client


@pytest.fixture
def clients(mqtt_client_cls):
    return mqtt_client_cls.instances


def tick(clock, ms):
    clock.now += ms


# --------------------------------------------------------------------------
# Conexión
# --------------------------------------------------------------------------

def test_registers_itself_as_a_node_transport():
    s = Setup()
    assert s.node.transports == [s.transport]


def test_does_not_try_to_connect_without_wifi(clients):
    s = Setup(wifi_up=False)
    s.transport.update()

    assert clients == []
    assert not s.transport.connected


def test_connects_once_wifi_is_up(clients, clock):
    s = Setup(wifi_up=False)
    s.transport.update()
    s.wifi.connected = True
    s.transport.update()

    assert s.transport.connected
    assert len(clients) == 1
    assert clients[0].server == "broker.test"
    assert clients[0].client_id == "alarm_node_abc"
    assert clients[0].keepalive == 30
    assert clients[0].connect_timeout == 3


def test_last_will_marks_the_node_offline_and_is_retained():
    s = Setup()
    s.transport.update()

    topic, payload, retain = s.client().last_will
    assert topic == (PREFIX + "node/online").encode()
    assert json.loads(payload) == {"online": False, "node": "alarm_node_abc"}
    assert retain is True


def test_announces_online_with_retain_after_connecting():
    s = Setup()
    s.transport.update()

    topic, payload, retain = s.client().published[0]
    assert topic == (PREFIX + "node/online").encode()
    assert json.loads(payload) == {"online": True, "node": "alarm_node_abc"}
    assert retain is True


def test_on_connect_callback_is_called():
    calls = []
    s = Setup(on_connect=lambda: calls.append(1))
    s.transport.update()

    assert calls == [1]


def test_defers_connecting_while_should_defer_is_true(clients, clock):
    busy = {"value": True}
    s = Setup(should_defer=lambda: busy["value"])

    s.transport.update()
    assert clients == []

    busy["value"] = False
    s.transport.update()
    assert len(clients) == 1


# --------------------------------------------------------------------------
# Tolerancia a fallos
# --------------------------------------------------------------------------

def test_connect_failure_does_not_raise_and_closes_the_socket(clients, mqtt_client_cls):
    mqtt_client_cls.fail_connect = True
    s = Setup()

    s.transport.update()  # no debe lanzar

    assert not s.transport.connected
    assert clients[0].sock.closed  # sin fuga de sockets


def test_reconnect_backoff_grows_and_is_capped(clients, clock, mqtt_client_cls):
    mqtt_client_cls.fail_connect = True
    s = Setup(retry_min_ms=2000, retry_max_ms=8000)

    s.transport.update()
    assert len(clients) == 1

    tick(clock, 1999)
    s.transport.update()
    assert len(clients) == 1          # aún esperando los 2 s

    tick(clock, 1)
    s.transport.update()
    assert len(clients) == 2          # 2º intento

    tick(clock, 3999)
    s.transport.update()
    assert len(clients) == 2          # ahora espera 4 s
    tick(clock, 1)
    s.transport.update()
    assert len(clients) == 3

    tick(clock, 7999)
    s.transport.update()
    assert len(clients) == 3          # tope: 8 s
    tick(clock, 1)
    s.transport.update()
    assert len(clients) == 4

    tick(clock, 8000)                 # y se queda en el tope
    s.transport.update()
    assert len(clients) == 5


def test_backoff_resets_after_a_successful_connection(clients, clock, mqtt_client_cls):
    mqtt_client_cls.fail_connect = True
    s = Setup(retry_min_ms=2000)
    s.transport.update()
    tick(clock, 2000)
    s.transport.update()

    mqtt_client_cls.fail_connect = False
    tick(clock, 4000)
    s.transport.update()
    assert s.transport.connected

    mqtt_client_cls.fail_io = True
    s.transport.publish("alarm/state", {"x": 1})  # cae la conexión
    assert not s.transport.connected

    mqtt_client_cls.fail_io = False
    tick(clock, 2000)                 # 2 s, no 8 s: el backoff volvió a empezar
    s.transport.update()
    assert s.transport.connected


def test_publish_failure_drops_the_connection_without_raising(clients, mqtt_client_cls):
    s = Setup()
    s.transport.update()
    mqtt_client_cls.fail_io = True

    s.transport.publish("alarm/state", {"state": "armed"})  # no debe lanzar

    assert not s.transport.connected
    assert clients[0].sock.closed


def test_update_failure_drops_the_connection_without_raising(mqtt_client_cls):
    s = Setup()
    s.transport.update()
    mqtt_client_cls.fail_io = True

    s.transport.update()

    assert not s.transport.connected


def test_resubscribes_to_every_topic_after_reconnecting(clients, clock, mqtt_client_cls):
    s = Setup()
    s.transport.subscribe("a/one")
    s.transport.subscribe("b/two")
    s.transport.update()
    assert sorted(clients[0].subscribed) == [(PREFIX + "a/one").encode(), (PREFIX + "b/two").encode()]

    mqtt_client_cls.fail_io = True
    s.transport.update()  # se cae
    mqtt_client_cls.fail_io = False
    tick(clock, 2000)
    s.transport.update()

    assert sorted(clients[1].subscribed) == [(PREFIX + "a/one").encode(), (PREFIX + "b/two").encode()]


def test_subscribing_before_connecting_is_remembered_not_sent(clients):
    s = Setup(wifi_up=False)
    s.transport.subscribe("a/one")

    assert clients == []
    assert "a/one" in s.transport._topics


# --------------------------------------------------------------------------
# Publicación
# --------------------------------------------------------------------------

def test_publishing_while_disconnected_is_silently_dropped(clients):
    s = Setup(wifi_up=False)
    s.transport.publish("alarm/state", {"state": "armed"})  # no debe lanzar
    assert clients == []


def test_state_topic_is_retained_and_events_are_not():
    s = Setup()
    s.transport.update()
    s.transport.publish(messages.TOPIC_STATE, {"state": "armed"})
    s.transport.publish(messages.TOPIC_EVENT, {"event": "armed"})

    published = {t: (m, r) for t, m, r in s.client().published}
    assert published[(PREFIX + "alarm/state").encode()][1] is True
    assert published[(PREFIX + "alarm/event").encode()][1] is False


def test_dicts_are_sent_as_json_and_prefix_is_added():
    s = Setup()
    s.transport.update()
    s.transport.publish("alarm/event", {"seq": 1, "event": "armed"})

    topic, payload, _ = s.client().published[-1]
    assert topic == (PREFIX + "alarm/event").encode()
    assert json.loads(payload) == {"seq": 1, "event": "armed"}


def test_non_dict_non_string_data_is_json_encoded_instead_of_crashing():
    # PubSubMQTT le pasaba el int crudo a umqtt (len(int) -> TypeError).
    s = Setup()
    s.transport.update()
    s.transport.publish("ir/value", 42)

    assert s.client().published[-1][1] == "42"


# --------------------------------------------------------------------------
# Recepción y mantenimiento de la conexión
# --------------------------------------------------------------------------

def test_incoming_message_is_routed_without_prefix_and_parsed():
    s = Setup()
    s.transport.update()
    s.client().inbox.append(((PREFIX + "led/GP0").encode(), b'{"value": 1}'))

    s.transport.update()

    assert s.node.received == [("led/GP0", {"value": 1})]


def test_incoming_non_json_is_delivered_as_raw_bytes():
    s = Setup()
    s.transport.update()
    s.client().inbox.append(((PREFIX + "x").encode(), b"not json"))

    s.transport.update()

    assert s.node.received == [("x", b"not json")]


def test_messages_from_another_prefix_are_ignored():
    s = Setup()
    s.transport.update()
    s.client().inbox.append((b"otro/grupo/x", b"{}"))

    s.transport.update()

    assert s.node.received == []


def test_a_failing_subscriber_does_not_drop_the_connection():
    s = Setup()
    s.transport.update()
    s.node.raise_on_local_publish = True
    s.client().inbox.append(((PREFIX + "x").encode(), b"{}"))

    s.transport.update()

    assert s.transport.connected


def test_message_burst_is_bounded_per_cycle():
    s = Setup(max_msgs_per_cycle=3)
    s.transport.update()
    for i in range(10):
        s.client().inbox.append(((PREFIX + "x").encode(), b"{}"))

    s.transport.update()

    assert len(s.node.received) == 3  # el resto espera al siguiente ciclo


def test_pings_the_broker_to_keep_the_connection_alive(clock):
    s = Setup(keepalive_s=30)
    s.transport.update()

    tick(clock, 9000)
    s.transport.update()
    assert s.client().pings == 0

    tick(clock, 1500)                 # > keepalive/3 = 10 s
    s.transport.update()
    assert s.client().pings == 1
