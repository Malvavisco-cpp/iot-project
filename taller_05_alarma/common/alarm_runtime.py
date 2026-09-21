"""Une AlarmController con el mundo físico: puerta, LED, sirena y publicación.

No importa `machine` ni `time`: los pines, el reloj y `publish` se inyectan.
Así el mismo código corre en el Pico (pines reales), en el simulador y en los
tests (pines falsos). Es la parte que permite que la alarma funcione SIN el PC:
todas las decisiones y salidas ocurren aquí, en el Pico. La red solo informa.

Uso desde el Pico:  AlarmTask llama a poll() cada ~20 ms y KeypadIR llama a
on_ir_code() por cada tecla recibida.
"""

from common import messages
from common.alarm import STATE_ARMED, STATE_TRIGGERED, ticks_diff


class AlarmRuntime:

    def __init__(
        self,
        controller,
        door_pin,
        led_pin,
        siren_pin,
        publish,
        clock,
        door_open_level: int = 1,
        debounce_ms: int = 50,
        state_period_ms: int = 5000,
        blink_ms: int = 250,
    ):
        """
        door_pin / led_pin / siren_pin: objetos con .value() / .value(x).
                                        siren_pin puede ser None (el LED parpadea).
        publish(topic, dict):           p. ej. node.publish. Si falla no afecta a la alarma.
        clock():                        milisegundos (time.ticks_ms en el Pico).
        door_open_level:                nivel del pin cuando la puerta está abierta.
        """
        self.controller = controller
        self.door_pin = door_pin
        self.led_pin = led_pin
        self.siren_pin = siren_pin
        self.publish = publish
        self.clock = clock
        self.door_open_level = door_open_level
        self.debounce_ms = debounce_ms
        self.state_period_ms = state_period_ms
        self.blink_ms = blink_ms

        self._seq = 0
        self._dirty = True
        self._uptime_ms = 0

        now = clock()
        self._last_poll = now
        self._last_state_ms = now

        # Lectura inicial: la puerta se toma tal como está, sin esperar el debounce.
        raw = door_pin.value()
        self._door_stable = raw
        self._door_candidate = raw
        self._door_since = now
        controller.on_event = self._on_event
        controller.handle_door(raw == door_open_level, now)
        self._apply_outputs(now)

    # --------------------------------------------------------------- entradas

    def on_ir_code(self, code: int) -> None:
        """Una tecla llegó del receptor IR."""
        now = self.clock()
        self.controller.handle_ir_code(code, now)
        # La sirena no espera al siguiente poll().
        self._apply_outputs(now)

    def poll(self) -> None:
        """Llamar periódicamente (~20 ms): puerta, vencimiento de teclas, salidas, estado."""
        now = self.clock()
        self._uptime_ms += ticks_diff(now, self._last_poll)
        self._last_poll = now

        self._read_door(now)
        self.controller.tick(now)
        self._apply_outputs(now)

        if self._dirty or ticks_diff(now, self._last_state_ms) >= self.state_period_ms:
            self._publish_state(now)

    def mark_dirty(self) -> None:
        """Pide republicar el estado en el próximo poll() (p. ej. al reconectar MQTT)."""
        self._dirty = True

    # ---------------------------------------------------------------- internos

    def _read_door(self, now: int) -> None:
        raw = self.door_pin.value()
        if raw != self._door_candidate:
            self._door_candidate = raw
            self._door_since = now
        elif raw != self._door_stable and ticks_diff(now, self._door_since) >= self.debounce_ms:
            self._door_stable = raw
            self.controller.handle_door(raw == self.door_open_level, now)

    def _apply_outputs(self, now: int) -> None:
        state = self.controller.state
        siren_on = state == STATE_TRIGGERED

        if self.siren_pin is not None:
            self.siren_pin.value(1 if siren_on else 0)

        if state == STATE_ARMED:
            led = 1
        elif siren_on:
            led = 1 if (now // self.blink_ms) % 2 == 0 else 0
        else:
            led = 0
        self.led_pin.value(led)

    def _on_event(self, name: str, detail: dict) -> None:
        self._seq += 1
        self._publish(
            messages.TOPIC_EVENT,
            messages.build_event(self._seq, name, detail, self._uptime_ms // 1000),
        )
        self._dirty = True

    def _publish_state(self, now: int) -> None:
        snap = self.controller.snapshot()
        self._publish(
            messages.TOPIC_STATE,
            messages.build_state(
                snap["state"],
                snap["door_open"],
                snap["keys_entered"],
                snap["wrong_attempts"],
                snap["reason"],
                self._uptime_ms // 1000,
            ),
        )
        self._dirty = False
        self._last_state_ms = now

    def _publish(self, topic: str, msg: dict) -> None:
        # Un fallo de red jamás debe impedir que la alarma decida o suene.
        try:
            self.publish(topic, msg)
        except Exception as e:
            print("AlarmRuntime: no se pudo publicar", topic, e)
