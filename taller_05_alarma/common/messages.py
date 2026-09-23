"""Contrato de mensajes entre el Pico y la interfaz Flet.

Los tópicos van SIN prefijo; el transporte MQTT antepone `config.PREFIX`.

    Pico -> Flet
      alarm/state     (retenido)  estado completo; se republica cada ~5 s
      alarm/event                 bitácora: qué pasó y cuándo
      node/online     (retenido)  {"online": bool}; el broker publica false si el Pico cae
      watchdog/stats              telemetría de PicoROS (memoria, RSSI, tiempos)

    Flet -> Pico (real o virtual)
      sim/door_set                {"door_open": bool}; botón "simular puerta" de la UI.
                                   Lo escuchan tanto tools/pico_simulator.py como
                                   micropython/main.py. Si el grupo sí tiene un sensor
                                   de puerta físico cableado, ese sensor manda igual;
                                   este comando solo importa para los grupos que no
                                   tienen sensor físico (solo el receptor IR).

Fuera de ese comando de simulación, Flet no envía nada: la clave solo se digita
en el control IR, así que la interfaz no puede armar ni desarmar la alarma.
"""

from common.alarm import STATE_ARMED, STATE_DISARMED, STATE_TRIGGERED

TOPIC_STATE = "alarm/state"
TOPIC_EVENT = "alarm/event"
TOPIC_ONLINE = "node/online"
TOPIC_WATCHDOG = "watchdog/stats"
TOPIC_DOOR_SIM = "sim/door_set"

# Estos se retienen en el broker: quien se conecte tarde recibe el último valor.
RETAINED_TOPICS = (TOPIC_STATE, TOPIC_ONLINE)

VALID_STATES = (STATE_DISARMED, STATE_ARMED, STATE_TRIGGERED)


def build_state(
    state: str,
    door_open: bool,
    keys_entered: int,
    wrong_attempts: int,
    reason,
    uptime_s: int,
) -> dict:
    return {
        "state": state,
        "door_open": door_open,
        "siren": state == STATE_TRIGGERED,
        "keys_entered": keys_entered,
        "wrong_attempts": wrong_attempts,
        "reason": reason,
        "uptime_s": uptime_s,
    }


def build_event(seq: int, name: str, detail: dict, uptime_s: int) -> dict:
    return {
        "seq": seq,
        "event": name,
        "detail": detail,
        "uptime_s": uptime_s,
    }


def build_online(online: bool, node: str) -> dict:
    return {"online": online, "node": node}


def build_door_set(door_open: bool) -> dict:
    return {"door_open": door_open}


def _is_int(value) -> bool:
    # bool es subclase de int en Python; aquí no cuenta como número.
    return isinstance(value, int) and not isinstance(value, bool)


def validate_state(msg) -> None:
    """Lanza ValueError si `msg` no es un alarm/state válido (el broker es público)."""
    if not isinstance(msg, dict):
        raise ValueError("alarm/state debe ser un objeto JSON")
    if msg.get("state") not in VALID_STATES:
        raise ValueError("state inválido: %r" % (msg.get("state"),))
    for key in ("door_open", "siren"):
        if not isinstance(msg.get(key), bool):
            raise ValueError("%s debe ser booleano" % key)
    for key in ("keys_entered", "wrong_attempts", "uptime_s"):
        if not _is_int(msg.get(key)) or msg[key] < 0:
            raise ValueError("%s debe ser un entero >= 0" % key)
    if msg.get("reason") is not None and not isinstance(msg["reason"], str):
        raise ValueError("reason debe ser texto o null")


def validate_door_set(msg) -> None:
    """Lanza ValueError si `msg` no es un sim/door_set válido."""
    if not isinstance(msg, dict):
        raise ValueError("sim/door_set debe ser un objeto JSON")
    if not isinstance(msg.get("door_open"), bool):
        raise ValueError("door_open debe ser booleano")


def validate_event(msg) -> None:
    """Lanza ValueError si `msg` no es un alarm/event válido."""
    if not isinstance(msg, dict):
        raise ValueError("alarm/event debe ser un objeto JSON")
    if not _is_int(msg.get("seq")):
        raise ValueError("seq debe ser un entero")
    if not isinstance(msg.get("event"), str) or not msg["event"]:
        raise ValueError("event debe ser texto")
    if not isinstance(msg.get("detail"), dict):
        raise ValueError("detail debe ser un objeto")
    if not _is_int(msg.get("uptime_s")):
        raise ValueError("uptime_s debe ser un entero")
