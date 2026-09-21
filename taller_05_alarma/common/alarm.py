"""Máquina de estados de la alarma. Lógica pura: sin hardware, red ni reloj.

Reglas (pizarra del taller):

  1. La clave de 4 dígitos, ingresada por el IR, activa y desactiva la alarma.
  2. Clave equivocada  -> se dispara la sirena.
  3. Alarma activa   + puerta abierta -> se dispara la sirena.
  4. Alarma inactiva + puerta abierta -> NO se dispara.

Estados:

    DISARMED --clave OK--> ARMED --clave OK--> DISARMED
        |                    |
        | clave mala         | clave mala / puerta abierta
        v                    v
                 TRIGGERED  --clave OK--> DISARMED   (la clave silencia la sirena)

Decisiones que el enunciado no fija:
  * La condición de intrusión es por NIVEL (taller §22): si se activa con la
    puerta ya abierta, la sirena suena de inmediato.
  * Estando disparada, una clave mala solo suma intentos; la sirena sigue.
  * Una clave a medias se descarta sola tras `key_timeout_ms` sin teclas, para
    que una pulsación suelta no envenene el siguiente intento.
  * Un código IR que no está en el keymap (ruido, trama de repetición del
    control) se ignora: nunca cuenta como clave equivocada.

Corre en CPython y en MicroPython: no usa dataclass, typing, enum ni time.
El reloj lo pone quien llama (`now_ms`, p. ej. `time.ticks_ms()`).
"""

STATE_DISARMED = "disarmed"
STATE_ARMED = "armed"
STATE_TRIGGERED = "triggered"

REASON_DOOR_OPEN = "door_open"
REASON_WRONG_PASSWORD = "wrong_password"

EVENT_KEY = "key"
EVENT_KEYS_CLEARED = "keys_cleared"
EVENT_DOOR = "door"
EVENT_WRONG_PASSWORD = "wrong_password"
EVENT_ARMED = "armed"
EVENT_DISARMED = "disarmed"
EVENT_TRIGGERED = "triggered"

KEY_CLEAR = "C"

# time.ticks_ms() de MicroPython da la vuelta cada 2**30 ms (~12 días).
_TICKS_PERIOD = 1 << 30
_TICKS_HALF = _TICKS_PERIOD >> 1


def ticks_diff(new: int, old: int) -> int:
    """Diferencia new - old tolerante a la vuelta del contador (como time.ticks_diff)."""
    diff = (new - old) & (_TICKS_PERIOD - 1)
    if diff >= _TICKS_HALF:
        diff -= _TICKS_PERIOD
    return diff


class AlarmController:
    """Decide el estado de la alarma a partir de teclas IR y del sensor de puerta.

    on_event(name, detail) se llama en cada cambio relevante. Las teclas
    digitadas NUNCA salen en un evento: solo su cantidad.
    """

    def __init__(
        self,
        password: str,
        keymap: dict,
        password_length: int = 4,
        key_timeout_ms: int = 5000,
        on_event=None,
    ):
        if len(password) != password_length or not password.isdigit():
            raise ValueError("la clave debe tener exactamente %d dígitos" % password_length)
        self.password = password
        self.password_length = password_length
        self.keymap = keymap
        self.key_timeout_ms = key_timeout_ms
        self.on_event = on_event

        self.state = STATE_DISARMED
        self.door_open = False
        self.reason = None
        self.wrong_attempts = 0

        self._entered = ""
        self._last_key_ms = 0

    # ------------------------------------------------------------------ estado

    @property
    def siren(self) -> bool:
        return self.state == STATE_TRIGGERED

    @property
    def keys_entered(self) -> int:
        return len(self._entered)

    def snapshot(self) -> dict:
        return {
            "state": self.state,
            "door_open": self.door_open,
            "keys_entered": len(self._entered),
            "wrong_attempts": self.wrong_attempts,
            "reason": self.reason,
        }

    # ---------------------------------------------------------------- entradas

    def handle_ir_code(self, code: int, now_ms: int) -> None:
        key = self.keymap.get(code)
        if key is None:
            return

        self._expire_keys(now_ms)
        self._last_key_ms = now_ms

        if key == KEY_CLEAR:
            self._clear_keys("clear_key")
            return

        self._entered += key
        self._emit(EVENT_KEY, {"count": len(self._entered)})

        if len(self._entered) == self.password_length:
            entered = self._entered
            self._entered = ""
            self._check_password(entered)

    def handle_door(self, is_open: bool, now_ms: int) -> None:
        if is_open == self.door_open:
            return
        self.door_open = is_open
        self._emit(EVENT_DOOR, {"open": is_open})
        if is_open and self.state == STATE_ARMED:
            self._trigger(REASON_DOOR_OPEN)

    def tick(self, now_ms: int) -> None:
        """Llamar periódicamente: vence la clave a medias."""
        self._expire_keys(now_ms)

    # ------------------------------------------------------------- transiciones

    def _check_password(self, entered: str) -> None:
        if entered == self.password:
            self.wrong_attempts = 0
            if self.state == STATE_DISARMED:
                self._arm()
            else:
                self._disarm()
            return

        self.wrong_attempts += 1
        self._emit(EVENT_WRONG_PASSWORD, {"attempts": self.wrong_attempts})
        if self.state != STATE_TRIGGERED:
            self._trigger(REASON_WRONG_PASSWORD)

    def _arm(self) -> None:
        self.state = STATE_ARMED
        self.reason = None
        self._emit(EVENT_ARMED, {})
        if self.door_open:
            self._trigger(REASON_DOOR_OPEN)

    def _disarm(self) -> None:
        silenced = self.state == STATE_TRIGGERED
        self.state = STATE_DISARMED
        self.reason = None
        self._emit(EVENT_DISARMED, {"silenced": silenced})

    def _trigger(self, reason: str) -> None:
        self.state = STATE_TRIGGERED
        self.reason = reason
        self._emit(EVENT_TRIGGERED, {"reason": reason})

    # ------------------------------------------------------------------ helpers

    def _expire_keys(self, now_ms: int) -> None:
        if self._entered and ticks_diff(now_ms, self._last_key_ms) >= self.key_timeout_ms:
            self._clear_keys("timeout")

    def _clear_keys(self, why: str) -> None:
        if self._entered:
            self._entered = ""
            self._emit(EVENT_KEYS_CLEARED, {"reason": why})

    def _emit(self, name: str, detail: dict) -> None:
        if self.on_event is not None:
            self.on_event(name, detail)
