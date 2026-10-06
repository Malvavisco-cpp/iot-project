"""Contrato de mensajes entre la app Flet y el carro (Pico).

Los tópicos van SIN prefijo; el transporte MQTT antepone `config.PREFIX`.

    Flet -> Pico
      car/cmd     {"v": m/s, "w": rad/s, "t": s}   avanza con v y w durante t
      car/stop    {}                                frena ya

    Pico -> Flet
      car/state   (retenido) {"moving", "v", "w", "t", "v_l", "v_r"}
"""

import math

TOPIC_CMD = "car/cmd"
TOPIC_STOP = "car/stop"
TOPIC_STATE = "car/state"


def _is_number(value):
    # bool es subclase de int en Python; aquí no cuenta como número.
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def build_cmd(v, w, t):
    return {"v": v, "w": w, "t": t}


def validate_cmd(msg):
    """Lanza ValueError si `msg` no es un car/cmd válido (el broker es público)."""
    if not isinstance(msg, dict):
        raise ValueError("car/cmd debe ser un objeto JSON")
    for key in ("v", "w", "t"):
        if not _is_number(msg.get(key)):
            raise ValueError("%s debe ser numérico" % key)
    if msg["t"] <= 0:
        raise ValueError("t debe ser mayor que 0")


def build_state(moving, v, w, t, v_l, v_r):
    return {"moving": moving, "v": v, "w": w, "t": t, "v_l": v_l, "v_r": v_r}


def validate_state(msg):
    if not isinstance(msg, dict) or not isinstance(msg.get("moving"), bool):
        raise ValueError("car/state inválido")
    for key in ("v", "w", "t", "v_l", "v_r"):
        if not _is_number(msg.get(key)):
            raise ValueError("%s debe ser numérico" % key)
