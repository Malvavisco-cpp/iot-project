"""Car: robot diferencial que avanza con rapidez v y velocidad angular w
durante un tiempo t, según lo que llegue por MQTT.

    car/cmd  {"v", "w", "t"} -> cinemática inversa -> v_l, v_r -> motores
    car/stop {}              -> frena ya
    (al cumplirse t frena solo, y publica car/state al arrancar y al frenar)

No importa `machine` ni `time`: recibe el `node` de PicoROS (solo usa
`subscribe` y `publish`), los dos `Motor` y un reloj en ms. Así corre igual
en el Pico, en el simulador del PC y en los tests.

Alguien debe llamar a `tick()` seguido (cada ~20 ms): en el Pico lo hace
`CarTask`; es lo que detiene el carro al cumplirse t sin bloquear nada.
"""

from common import messages
from common.kinematics import inverse, scale_to_limit

# time.ticks_ms() de MicroPython da la vuelta cada 2**30 ms (~12 días).
_TICKS_PERIOD = 1 << 30
_TICKS_HALF = _TICKS_PERIOD >> 1


def ticks_diff(new, old):
    """new - old tolerante a la vuelta del contador (como time.ticks_diff)."""
    diff = (new - old) & (_TICKS_PERIOD - 1)
    if diff >= _TICKS_HALF:
        diff -= _TICKS_PERIOD
    return diff


class Car:

    def __init__(self, node, left, right, half_track_m, max_wheel_speed, clock, max_duration_s=30.0):
        self.node = node
        self.left = left
        self.right = right
        self.half_track_m = half_track_m
        self.max_wheel_speed = max_wheel_speed
        self.clock = clock
        self.max_duration_s = max_duration_s

        self._end_ms = None
        self._last = messages.build_state(False, 0.0, 0.0, 0.0, 0.0, 0.0)

        node.subscribe(messages.TOPIC_CMD, self._on_cmd)
        node.subscribe(messages.TOPIC_STOP, self._on_stop)

    @property
    def moving(self):
        return self._end_ms is not None

    # --------------------------------------------------------------- acciones

    def drive(self, v, w, t):
        """Avanza con v (m/s) y w (rad/s) durante t (s). Reemplaza el comando anterior."""
        v_l, v_r = inverse(v, w, self.half_track_m)
        # Si una rueda no da para tanto, se bajan las dos en la misma proporción
        # (mismo radio de giro) y se alarga el tiempo: misma trayectoria, más lenta.
        v_l, v_r, k = scale_to_limit(v_l, v_r, self.max_wheel_speed)
        if k < 1.0:
            print("Car: rueda saturada, rapidez x%.2f y tiempo x%.2f" % (k, 1 / k))
            t = t / k
        t = min(t, self.max_duration_s)

        self.left.set_speed(v_l)
        self.right.set_speed(v_r)
        self._end_ms = self.clock() + int(t * 1000)
        self._last = messages.build_state(True, v * k, w * k, t, v_l, v_r)
        print("Car: v=%.3f w=%.3f t=%.2f -> v_l=%.3f v_r=%.3f" % (v * k, w * k, t, v_l, v_r))
        self.publish_state()

    def stop(self):
        self.left.stop()
        self.right.stop()
        was_moving = self.moving
        self._end_ms = None
        self._last = messages.build_state(False, 0.0, 0.0, 0.0, 0.0, 0.0)
        if was_moving:
            print("Car: detenido")
        self.publish_state()

    def tick(self):
        if self._end_ms is not None and ticks_diff(self.clock(), self._end_ms) >= 0:
            self.stop()

    def publish_state(self):
        try:
            self.node.publish(messages.TOPIC_STATE, self._last)
        except Exception as e:
            # Un fallo de red jamás debe impedir que el carro frene.
            print("Car: no se pudo publicar el estado", e)

    # ---------------------------------------------------------------- MQTT

    # Node de PicoROS quita para siempre un callback que lance una excepción,
    # por eso estos dos nunca la dejan salir.

    def _on_cmd(self, topic, msg):
        try:
            messages.validate_cmd(msg)
            self.drive(msg["v"], msg["w"], msg["t"])
        except Exception as e:
            print("Car: car/cmd ignorado:", e)

    def _on_stop(self, topic, msg):
        try:
            self.stop()
        except Exception as e:
            print("Car: error al frenar:", e)
