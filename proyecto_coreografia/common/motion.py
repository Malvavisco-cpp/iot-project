"""Contrato de tópicos de motionTopics.md, interpretado igual que el gemelo
virtual (IoT_ws/coreografia/3D/RoDifArm.js) para que robot y gemelo hagan lo mismo.

Tópicos (sin prefijo; el transporte antepone config.PREFIX):

    PC -> robot y gemelo
      motion/state      {"v_dm/s", "w_deg/s", "alpha0_deg", "alpha1_deg", "alpha2_deg", "duration_s"}
      motion/sequence   {"action": "create" | "delete" | "schedule" | "execute_now", "name", ...}

    robot -> PC
      motion/status     (retenido) modo, paso, secuencias cargadas y programadas
      watchdog/stats    telemetría del WatchdogTask de PicoROS
      node/online       (retenido) {"online": bool}; Last Will si el robot se cae

Reglas del gemelo que se copian:
  * v en dm/s, w y ángulos en grados.
  * Falta v o w -> 0. Falta duration_s -> 1 s (mínimo 0.001 s).
  * Falta un ángulo -> el brazo se queda donde está (el gemelo hace eso; el
    .md dice "cero", pero lo que importa para la coreografía es ir igual al gemelo).
  * Se aceptan "alpha0_deg" (motionTopics.md, RoDifArm.js) y "alfa0_deg"
    (robot_coreografia_mqtt.html): la app manda las dos.
"""

import math

TOPIC_STATE = "motion/state"
TOPIC_SEQUENCE = "motion/sequence"
TOPIC_STATUS = "motion/status"
TOPIC_WATCHDOG = "watchdog/stats"
TOPIC_ONLINE = "node/online"

ANGLE_KEYS = (
    ("alpha0_deg", "alfa0_deg"),
    ("alpha1_deg", "alfa1_deg"),
    ("alpha2_deg", "alfa2_deg"),
)
DEFAULT_DURATION_S = 1.0
MIN_DURATION_S = 0.001


def _number(value, fallback):
    """Como Number() del gemelo: número finito, o `fallback`."""
    if value is None or isinstance(value, bool):
        return fallback
    try:
        n = float(value)
    except (TypeError, ValueError):
        return fallback
    return n if math.isfinite(n) else fallback


def parse_state(payload, current_angles):
    """Estado del tópico -> {"v": m/s, "w": rad/s, "angles": (a0, a1, a2) en °, "duration_ms"}."""
    if not isinstance(payload, dict):
        raise ValueError("el estado debe ser un objeto JSON")
    v_dm = _number(payload.get("v_dm/s"), 0.0)
    w_deg = _number(payload.get("w_deg/s"), 0.0)

    angles = []
    for i, keys in enumerate(ANGLE_KEYS):
        value = current_angles[i]
        for key in keys:
            if key in payload:
                value = _number(payload[key], 0.0)
                break
        angles.append(value)

    duration_s = max(MIN_DURATION_S, _number(payload.get("duration_s"), DEFAULT_DURATION_S))
    return {
        "v": v_dm / 10.0,
        "w": math.radians(w_deg),
        "angles": (angles[0], angles[1], angles[2]),
        "duration_ms": max(1, int(duration_s * 1000 + 0.5)),
    }


def _r(x):
    return round(float(x), 4)


def build_state(v_dm_s=0.0, w_deg_s=0.0, alpha0=0.0, alpha1=0.0, alpha2=0.0, duration_s=1.0):
    """Estado completo, con las dos grafías de los ángulos (sirve para los dos gemelos)."""
    return {
        "v_dm/s": _r(v_dm_s),
        "w_deg/s": _r(w_deg_s),
        "alpha0_deg": _r(alpha0),
        "alpha1_deg": _r(alpha1),
        "alpha2_deg": _r(alpha2),
        "alfa0_deg": _r(alpha0),
        "alfa1_deg": _r(alpha1),
        "alfa2_deg": _r(alpha2),
        "duration_s": _r(duration_s),
    }


def build_create(name, states):
    return {"action": "create", "name": name, "states": [dict(s) for s in states]}


def build_delete(name):
    return {"action": "delete", "name": name}


def build_schedule(name, run_at="now"):
    return {"action": "schedule", "name": name, "run_at": run_at}


def build_execute_now(name):
    return {"action": "execute_now", "name": name}
