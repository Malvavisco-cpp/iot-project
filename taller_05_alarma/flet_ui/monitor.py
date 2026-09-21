"""Modelo de la interfaz: recibe mensajes MQTT y mantiene el estado que se muestra.

No importa Flet ni paho: así se prueba sin abrir ventanas ni conectarse a un broker
(taller 02, §1.6: separar la UI de la lógica).
"""

import json
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable

from common import messages
from common.alarm import (
    REASON_DOOR_OPEN,
    REASON_WRONG_PASSWORD,
    STATE_ARMED,
    STATE_DISARMED,
    STATE_TRIGGERED,
)

STATE_UNKNOWN = "unknown"

# Estado del enlace con el Pico
LINK_WAITING = "waiting"   # todavía no llega nada
LINK_ONLINE = "online"
LINK_OFFLINE = "offline"   # el broker publicó el Last Will: el Pico se cayó
LINK_SILENT = "silent"     # conectado, pero hace rato que no reporta

# Severidad de una línea de la bitácora (la vista la traduce a color)
LEVEL_INFO = "info"
LEVEL_SUCCESS = "success"
LEVEL_WARNING = "warning"
LEVEL_DANGER = "danger"

HEADLINES = {
    STATE_UNKNOWN: "SIN DATOS",
    STATE_DISARMED: "ALARMA DESACTIVADA",
    STATE_ARMED: "ALARMA ACTIVADA",
    STATE_TRIGGERED: "¡ALARMA DISPARADA!",
}

REASON_TEXT = {
    REASON_DOOR_OPEN: "Intrusión: la puerta se abrió con la alarma activa",
    REASON_WRONG_PASSWORD: "Se digitó una clave incorrecta",
}


@dataclass
class AlarmStatus:
    state: str = STATE_UNKNOWN
    door_open: bool = False
    siren: bool = False
    keys_entered: int = 0
    wrong_attempts: int = 0
    reason: str | None = None
    uptime_s: int = 0


@dataclass
class SystemInfo:
    """Telemetría del WatchdogTask de PicoROS."""
    mem_free_bytes: int | None = None
    rssi: int | None = None
    temperature_c: float | None = None


@dataclass
class LogEntry:
    seq: int
    name: str
    text: str
    level: str
    received_at: float


def headline_for(status: AlarmStatus) -> str:
    return HEADLINES.get(status.state, HEADLINES[STATE_UNKNOWN])


def detail_for(status: AlarmStatus) -> str:
    """Segunda línea de la tarjeta principal."""
    if status.state == STATE_TRIGGERED:
        return REASON_TEXT.get(status.reason, "Alarma disparada")
    if status.state == STATE_ARMED:
        return "Vigilando la puerta"
    if status.state == STATE_DISARMED:
        return "La puerta puede abrirse sin disparar la alarma"
    return "Esperando datos del Pico..."


def describe_event(name: str, detail: dict) -> tuple[str, str] | None:
    """(texto, nivel) para la bitácora; None si el evento no se muestra."""
    if name == "key":
        return None  # el avance de la clave se ve en los puntos de la tarjeta principal
    if name == "keys_cleared":
        why = "tiempo agotado" if detail.get("reason") == "timeout" else "tecla borrar"
        return f"Clave a medias descartada ({why})", LEVEL_INFO
    if name == "door":
        return ("Puerta 1 ABIERTA" if detail.get("open") else "Puerta 1 CERRADA"), LEVEL_INFO
    if name == "wrong_password":
        return f"Clave incorrecta (intento {detail.get('attempts', '?')})", LEVEL_WARNING
    if name == "armed":
        return "Alarma ACTIVADA", LEVEL_SUCCESS
    if name == "disarmed":
        if detail.get("silenced"):
            return "Alarma DESACTIVADA y sirena silenciada", LEVEL_SUCCESS
        return "Alarma DESACTIVADA", LEVEL_SUCCESS
    if name == "triggered":
        return "¡SIRENA! " + REASON_TEXT.get(detail.get("reason"), "Alarma disparada"), LEVEL_DANGER
    return f"Evento: {name}", LEVEL_INFO


class AlarmMonitor:

    def __init__(
        self,
        prefix: str,
        clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], float] = time.time,
        offline_after_s: float = 15.0,
        max_log: int = 100,
    ):
        self.prefix = prefix
        self._clock = clock
        self._wall_clock = wall_clock
        self.offline_after_s = offline_after_s

        self.status = AlarmStatus()
        self.system = SystemInfo()
        self.log: deque[LogEntry] = deque(maxlen=max_log)
        self.log_version = 0
        self.rejected = 0

        self._node_online: bool | None = None
        self._last_state_at: float | None = None

    @property
    def topics(self) -> list[str]:
        """Tópicos completos a los que debe suscribirse el cliente MQTT."""
        return [
            self.prefix + topic
            for topic in (
                messages.TOPIC_STATE,
                messages.TOPIC_EVENT,
                messages.TOPIC_ONLINE,
                messages.TOPIC_WATCHDOG,
            )
        ]

    def link(self) -> str:
        if self._node_online is False:
            return LINK_OFFLINE
        if self._last_state_at is None:
            return LINK_ONLINE if self._node_online else LINK_WAITING
        if self._clock() - self._last_state_at > self.offline_after_s:
            return LINK_SILENT
        return LINK_ONLINE

    def handle_message(self, topic: str, payload: bytes) -> bool:
        """Procesa un mensaje. Devuelve True si algo visible cambió.

        El broker es público: cualquier payload puede llegar, así que lo malformado
        se descarta (y se cuenta en `rejected`) en lugar de romper la interfaz.
        """
        if not topic.startswith(self.prefix):
            return False
        local_topic = topic[len(self.prefix):]

        try:
            data = json.loads(payload.decode("utf-8"))
            if local_topic == messages.TOPIC_STATE:
                return self._on_state(data)
            if local_topic == messages.TOPIC_EVENT:
                return self._on_event(data)
            if local_topic == messages.TOPIC_ONLINE:
                return self._on_online(data)
            if local_topic == messages.TOPIC_WATCHDOG:
                return self._on_watchdog(data)
        except (ValueError, TypeError, UnicodeDecodeError):
            self.rejected += 1
        return False

    # ---------------------------------------------------------------- tópicos

    def _on_state(self, data: dict) -> bool:
        messages.validate_state(data)
        self.status = AlarmStatus(
            state=data["state"],
            door_open=data["door_open"],
            siren=data["siren"],
            keys_entered=data["keys_entered"],
            wrong_attempts=data["wrong_attempts"],
            reason=data["reason"],
            uptime_s=data["uptime_s"],
        )
        self._last_state_at = self._clock()
        return True

    def _on_event(self, data: dict) -> bool:
        messages.validate_event(data)
        described = describe_event(data["event"], data["detail"])
        if described is None:
            return False
        text, level = described
        self.log.appendleft(LogEntry(data["seq"], data["event"], text, level, self._wall_clock()))
        self.log_version += 1
        return True

    def _on_online(self, data: dict) -> bool:
        if not isinstance(data, dict) or not isinstance(data.get("online"), bool):
            raise ValueError("node/online inválido")
        self._node_online = data["online"]
        return True

    def _on_watchdog(self, data: dict) -> bool:
        if not isinstance(data, dict):
            raise ValueError("watchdog/stats inválido")
        self.system = SystemInfo(
            mem_free_bytes=_as_int(data.get("mem_free_bytes")),
            rssi=_as_int(data.get("rssi")),
            temperature_c=_as_float(data.get("temperature_c")),
        )
        return True


def _as_int(value) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _as_float(value) -> float | None:
    # WatchdogTask manda la temperatura como texto ("24.31").
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
