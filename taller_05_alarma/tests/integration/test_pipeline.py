"""Integración: Pico (lógica + runtime) -> tópicos MQTT -> monitor de Flet, con un bus en memoria.

Ejercita las dos mitades a través del contrato real (los mismos tópicos, JSON y prefijo),
sin depender de un broker. Al final hay una prueba contra un broker real, opcional.
"""

import json
import os
import threading
import time
import uuid

import pytest

from common import config, messages
from common.alarm import AlarmController
from common.alarm_runtime import AlarmRuntime
from flet_ui import monitor as mon
from flet_ui.monitor import AlarmMonitor

PREFIX = "UDFJC/iot_ws/robot9/"
PASSWORD = "1234"
CODE_OF = {key: code for code, key in config.DEFAULT_IR_KEYMAP.items()}


class FakePin:
    def __init__(self, level=0):
        self.level = level

    def value(self, new=None):
        if new is None:
            return self.level
        self.level = new


class Bus:
    """Hace de broker: lo que el Pico publica llega serializado a Flet, como por MQTT."""

    def __init__(self):
        self.wire = []
        self.retained = {}

    def publish(self, topic: str, msg: dict, monitor: AlarmMonitor):
        payload = json.dumps(msg).encode()
        self.wire.append((PREFIX + topic, payload))
        if topic in messages.RETAINED_TOPICS:
            self.retained[topic] = payload
        monitor.handle_message(PREFIX + topic, payload)


class System:
    """Un Pico completo y una interfaz conectados por el bus."""

    def __init__(self):
        self.now = 50_000
        self.bus = Bus()
        self.monitor = AlarmMonitor(PREFIX)
        self.door = FakePin()
        self.led = FakePin()
        self.siren = FakePin()
        self.controller = AlarmController(PASSWORD, config.DEFAULT_IR_KEYMAP)
        self.runtime = AlarmRuntime(
            self.controller,
            self.door,
            self.led,
            self.siren,
            publish=lambda topic, msg: self.bus.publish(topic, msg, self.monitor),
            clock=lambda: self.now,
        )
        self.advance(40)

    def advance(self, ms: int) -> None:
        end = self.now + ms
        while self.now < end:
            self.now += 20
            self.runtime.poll()

    def press(self, digits: str) -> None:
        for digit in digits:
            self.now += 200
            self.runtime.on_ir_code(CODE_OF[digit])
        self.advance(40)

    def open_door(self) -> None:
        self.door.level = 1
        self.advance(100)

    def close_door(self) -> None:
        self.door.level = 0
        self.advance(100)

    def ui_headline(self) -> str:
        return mon.headline_for(self.monitor.status)


@pytest.fixture
def system() -> System:
    return System()


def test_ui_learns_the_initial_state(system):
    assert system.monitor.status.state == "disarmed"
    assert system.monitor.link() == mon.LINK_ONLINE


def test_scenario_arm_intrusion_silence(system):
    system.press(PASSWORD)
    assert system.ui_headline() == "ALARMA ACTIVADA"
    assert system.led.level == 1 and system.siren.level == 0

    system.open_door()
    assert system.ui_headline() == "¡ALARMA DISPARADA!"
    assert system.monitor.status.reason == "door_open"
    assert system.siren.level == 1

    system.press(PASSWORD)
    assert system.ui_headline() == "ALARMA DESACTIVADA"
    assert system.siren.level == 0


def test_scenario_wrong_password_fires_the_siren(system):
    system.press("9999")

    assert system.ui_headline() == "¡ALARMA DISPARADA!"
    assert system.monitor.status.reason == "wrong_password"
    assert system.monitor.status.wrong_attempts == 1
    assert system.siren.level == 1


def test_scenario_door_while_disarmed_is_silent(system):
    system.open_door()
    system.close_door()

    assert system.ui_headline() == "ALARMA DESACTIVADA"
    assert system.siren.level == 0
    texts = [e.text for e in system.monitor.log]
    assert any("ABIERTA" in t for t in texts)
    assert not any("SIRENA" in t for t in texts)


def test_the_log_tells_the_story_in_order(system):
    system.press(PASSWORD)
    system.open_door()
    system.press(PASSWORD)

    names = [e.name for e in reversed(system.monitor.log)]
    assert names == ["armed", "door", "triggered", "disarmed"]


def test_the_password_never_travels_over_the_wire(system):
    system.press(PASSWORD)
    system.press("9999")

    everything = b" ".join(payload for _, payload in system.bus.wire).decode()
    assert "1234" not in everything and "9999" not in everything
    for code in CODE_OF.values():
        assert str(code) not in everything


def test_every_message_on_the_wire_is_valid_json_with_the_agreed_topics(system):
    system.press(PASSWORD)
    system.open_door()

    allowed = {PREFIX + t for t in (messages.TOPIC_STATE, messages.TOPIC_EVENT)}
    for topic, payload in system.bus.wire:
        assert topic in allowed
        json.loads(payload)
    assert system.monitor.rejected == 0


def test_late_joining_ui_gets_the_last_state_from_the_retained_message(system):
    system.press(PASSWORD)
    system.open_door()

    late = AlarmMonitor(PREFIX)  # abre Flet después de que ocurrió todo
    late.handle_message(PREFIX + messages.TOPIC_STATE, system.bus.retained[messages.TOPIC_STATE])

    assert late.status.state == "triggered"
    assert late.status.door_open is True


def test_ui_flags_the_pico_as_silent_if_reports_stop(system):
    t = {"now": 0.0}
    monitor = AlarmMonitor(PREFIX, clock=lambda: t["now"], offline_after_s=15)
    monitor.handle_message(PREFIX + messages.TOPIC_STATE, system.bus.retained[messages.TOPIC_STATE])
    assert monitor.link() == mon.LINK_ONLINE

    t["now"] = 30.0
    assert monitor.link() == mon.LINK_SILENT


def test_alarm_keeps_deciding_when_the_ui_and_network_are_gone():
    """El requisito de la pizarra: funcionar desconectado del PC."""
    now = {"t": 50_000}
    door, led, siren = FakePin(), FakePin(), FakePin()

    def dead_network(topic, msg):
        raise OSError("sin red")

    controller = AlarmController(PASSWORD, config.DEFAULT_IR_KEYMAP)
    runtime = AlarmRuntime(controller, door, led, siren, publish=dead_network, clock=lambda: now["t"])

    for digit in PASSWORD:
        now["t"] += 200
        runtime.on_ir_code(CODE_OF[digit])
    door.level = 1
    for _ in range(10):
        now["t"] += 20
        runtime.poll()

    assert controller.state == "triggered"
    assert siren.level == 1


# --------------------------------------------------------------------------
# Broker real (opcional: RUN_MQTT_TESTS=1 pytest -m network)
# --------------------------------------------------------------------------

@pytest.mark.network
@pytest.mark.skipif(os.environ.get("RUN_MQTT_TESTS") != "1", reason="define RUN_MQTT_TESTS=1 para usar el broker real")
def test_real_broker_round_trip():
    import paho.mqtt.client as mqtt

    prefix = f"UDFJC/iot_ws/test_{uuid.uuid4().hex[:8]}/"
    received = threading.Event()
    monitor = AlarmMonitor(prefix)

    sub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"test_sub_{uuid.uuid4().hex[:8]}")
    sub.on_connect = lambda c, u, f, rc, p: [c.subscribe(t) for t in monitor.topics]

    def on_message(client, userdata, message):
        monitor.handle_message(message.topic, message.payload)
        received.set()

    sub.on_message = on_message
    sub.connect(config.BROKER, config.PORT, 30)
    sub.loop_start()

    pub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"test_pub_{uuid.uuid4().hex[:8]}")
    pub.connect(config.BROKER, config.PORT, 30)
    pub.loop_start()
    try:
        time.sleep(1.5)  # deja que la suscripción se asiente
        msg = messages.build_state("triggered", True, 0, 1, "door_open", 7)
        pub.publish(prefix + messages.TOPIC_STATE, json.dumps(msg)).wait_for_publish(5)

        assert received.wait(10), "el broker no entregó el mensaje"
        assert monitor.status.state == "triggered"
        assert monitor.status.reason == "door_open"
    finally:
        pub.loop_stop()
        sub.loop_stop()
        pub.disconnect()
        sub.disconnect()
