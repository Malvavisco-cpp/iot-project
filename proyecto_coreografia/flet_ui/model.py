"""Modelo de la app: la coreografía que se está armando y cálculo de horas.

Sin Flet ni MQTT, así se prueba sin abrir ventanas.
"""

import math
from datetime import datetime, timezone

from common import config, motion
from common.kinematics import integrate_pose
from common.timeutil import iso_to_unix_ms, unix_ms_to_iso

# El ejemplo de motionTopics.md.
EXAMPLE_NAME = "hello"
EXAMPLE_STATES = [
    motion.build_state(2, 0, 0, 0, 0, 5.0),
    motion.build_state(5.2, 30, 0, 0, 0, 3.0),
    motion.build_state(0, 0, -90, 0, 0, 1.0),
    motion.build_state(0, 0, 90, 0, 0, 2.0),
    motion.build_state(0, 0, 0, 90, 0, 1.0),
    motion.build_state(0, 0, 0, 0, 90, 1.0),
]


def describe_state(s):
    return "v=%g dm/s  w=%g°/s  brazo(%g, %g, %g)°  %g s" % (
        s["v_dm/s"], s["w_deg/s"], s["alpha0_deg"], s["alpha1_deg"], s["alpha2_deg"], s["duration_s"],
    )


class Choreography:

    def __init__(self, name=EXAMPLE_NAME):
        self.name = name
        self.states = []

    def add(self, state):
        self.states.append(dict(state))

    def remove(self, index):
        del self.states[index]

    def clear(self):
        self.states = []

    def load_example(self):
        self.name = EXAMPLE_NAME
        self.states = [dict(s) for s in EXAMPLE_STATES]

    def total_s(self):
        return sum(s["duration_s"] for s in self.states)

    def end_pose(self):
        """(x dm, y dm, theta °) donde termina, saliendo de (0, 0) mirando a +x."""
        x = y = theta = 0.0
        for s in self.states:
            x, y, theta = integrate_pose(
                x, y, theta, s["v_dm/s"], math.radians(s["w_deg/s"]), s["duration_s"]
            )
        return x, y, math.degrees(theta)

    def create_payload(self):
        if not self.name:
            raise ValueError("ponga un nombre a la coreografía")
        if not self.states:
            raise ValueError("la coreografía no tiene pasos")
        return motion.build_create(self.name, self.states)


def utc_now_ms():
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def run_at_in(seconds, now_ms):
    """Fecha ISO UTC de dentro de `seconds` segundos."""
    if seconds < 0:
        raise ValueError("los segundos no pueden ser negativos")
    return unix_ms_to_iso(now_ms + int(seconds * 1000))


def run_at_local_time(text, now_local):
    """'20:30' o '20:30:15' (hora del PC, hoy) -> fecha ISO UTC.

    now_local: datetime "aware" con la zona del PC (datetime.now().astimezone()).
    """
    parts = text.strip().split(":")
    if len(parts) not in (2, 3) or not all(p.isdigit() for p in parts):
        raise ValueError("use HH:MM o HH:MM:SS")
    h, m = int(parts[0]), int(parts[1])
    s = int(parts[2]) if len(parts) == 3 else 0
    if h > 23 or m > 59 or s > 59:
        raise ValueError("hora fuera de rango")
    target = now_local.replace(hour=h, minute=m, second=s, microsecond=0)
    if target <= now_local:
        raise ValueError("esa hora ya pasó")
    return unix_ms_to_iso(int(target.astimezone(timezone.utc).timestamp() * 1000))


def local_time_text(iso):
    """ISO UTC -> 'HH:MM:SS' en la hora del PC."""
    ms = iso_to_unix_ms(iso)
    return datetime.fromtimestamp(ms / 1000).strftime("%H:%M:%S")


def twin_instructions():
    base = config.PREFIX.rstrip("/")
    robot = base.rsplit("/", 1)[-1]
    return (
        "Gemelo oficial (PubSub_client_web.html): prefix %s, Robot ID %s\n"
        "Gemelo alterno (robot_coreografia_mqtt.html): Topic base %s/motion"
        % (base.rsplit("/", 1)[0], robot.replace("robot", ""), base)
    )


def parse_float(text, what):
    try:
        return float(str(text).replace(",", "."))
    except ValueError:
        raise ValueError("'%s' debe ser un número" % what)
