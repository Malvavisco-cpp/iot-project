"""Dobles de MicroPython/PicoROS para probar en el PC el código de micropython/.

Solo se reemplaza lo que no existe fuera del Pico (umqtt, rp2, machine, network, time.ticks_*)
y una réplica mínima de task.py / scheduler.py de PicoROS (esos archivos no están en el
repo: vienen en minimum_PicoROS.zip). El código bajo prueba es el real.
"""

import sys
import time
import traceback
import types
from pathlib import Path

import pytest

from common.alarm import ticks_diff as _ticks_diff

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "micropython"))

_PERIOD = 1 << 30


class FakeTime:
    """Reloj controlado por los tests."""
    now = 0


# --- time.ticks_* de MicroPython --------------------------------------------
time.ticks_ms = lambda: FakeTime.now
time.ticks_diff = _ticks_diff
time.ticks_add = lambda a, b: (a + b) & (_PERIOD - 1)


def _sleep_ms(ms):
    FakeTime.now += ms


time.sleep_ms = _sleep_ms

# --- sys.print_exception es exclusivo de MicroPython -------------------------
sys.print_exception = lambda exc, *args, **kwargs: traceback.print_exception(exc)


# --- PicoROS: réplica mínima de task.py y scheduler.py ------------------------
task_mod = types.ModuleType("task")


class Task:
    def __init__(self, scheduler, period_ms, priority=1, name=None):
        self.period = period_ms
        self.priority = priority
        self.name = name or self.__class__.__name__
        self.next_run = time.ticks_ms()
        self.scheduler = scheduler
        scheduler.add(self)

    def update(self):
        pass

    def update_measured(self):
        self.update()


task_mod.Task = Task
sys.modules["task"] = task_mod

scheduler_mod = types.ModuleType("scheduler")


class Scheduler:
    def __init__(self):
        self.tasks = []

    def add(self, task):
        self.tasks.append(task)
        self.tasks.sort(key=lambda t: t.priority)


scheduler_mod.Scheduler = Scheduler
sys.modules["scheduler"] = scheduler_mod


# --- umqtt.simple -----------------------------------------------------------
class FakeSocket:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeMQTTClient:
    instances = []
    fail_connect = False   # connect() lanza OSError
    fail_io = False        # publish/subscribe/check_msg/ping lanzan OSError

    def __init__(self, client_id, server, port=0, user=None, password=None, keepalive=0, **kw):
        self.client_id = client_id
        self.server = server
        self.port = port
        self.keepalive = keepalive
        self.cb = None
        self.sock = FakeSocket()
        self.last_will = None
        self.connect_timeout = None
        self.published = []   # (topic, msg, retain)
        self.subscribed = []
        self.pings = 0
        self.check_calls = 0
        self.inbox = []       # (topic, payload) por entregar en check_msg()
        FakeMQTTClient.instances.append(self)

    def set_callback(self, f):
        self.cb = f

    def set_last_will(self, topic, msg, retain=False, qos=0):
        self.last_will = (topic, msg, retain)

    def connect(self, clean_session=True, timeout=None):
        self.connect_timeout = timeout
        if FakeMQTTClient.fail_connect:
            raise OSError("broker inalcanzable")

    def _maybe_fail(self):
        if FakeMQTTClient.fail_io:
            raise OSError("socket roto")

    def publish(self, topic, msg, retain=False, qos=0):
        self._maybe_fail()
        self.published.append((topic, msg, retain))

    def subscribe(self, topic, qos=0):
        self._maybe_fail()
        self.subscribed.append(topic)

    def ping(self):
        self._maybe_fail()
        self.pings += 1

    def check_msg(self):
        self._maybe_fail()
        self.check_calls += 1
        if not self.inbox:
            return None
        topic, payload = self.inbox.pop(0)
        self.cb(topic, payload)
        return 0x30


umqtt_pkg = types.ModuleType("umqtt")
umqtt_simple = types.ModuleType("umqtt.simple")
umqtt_simple.MQTTClient = FakeMQTTClient
umqtt_pkg.simple = umqtt_simple
sys.modules["umqtt"] = umqtt_pkg
sys.modules["umqtt.simple"] = umqtt_simple


# --- rp2 / machine (solo lo que toca ir_in.py) -----------------------------
class FakeStateMachine:
    def __init__(self, sm_id, program, freq=None, jmp_pin=None):
        self.fifo = []
        self.handler = None
        self.active_flag = 0
        self.put_values = []

    def irq(self, handler=None):
        self.handler = handler

    def active(self, flag):
        self.active_flag = flag

    def put(self, value):
        self.put_values.append(value)

    def rx_fifo(self):
        return len(self.fifo)

    def get(self):
        return self.fifo.pop(0)


rp2_mod = types.ModuleType("rp2")
rp2_mod.asm_pio = lambda **kwargs: (lambda fn: fn)
rp2_mod.PIO = types.SimpleNamespace(OUT_LOW=0)
rp2_mod.StateMachine = FakeStateMachine
sys.modules["rp2"] = rp2_mod

machine_mod = types.ModuleType("machine")


class FakePin:
    IN = 0
    OUT = 1
    PULL_UP = 2
    PULL_DOWN = 3

    def __init__(self, pin_id, mode=None, pull=None):
        self.pin_id = pin_id


machine_mod.Pin = FakePin
sys.modules["machine"] = machine_mod


# --- fixtures ---------------------------------------------------------------
@pytest.fixture(autouse=True)
def fresh_world():
    """Cada test arranca con reloj en 0 y sin clientes MQTT previos."""
    FakeTime.now = 0
    FakeMQTTClient.instances = []
    FakeMQTTClient.fail_connect = False
    FakeMQTTClient.fail_io = False
    yield


@pytest.fixture
def clock():
    return FakeTime


@pytest.fixture
def mqtt_client_cls():
    return FakeMQTTClient
