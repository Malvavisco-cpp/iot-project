"""MotionPlayer: ejecuta una lista de estados igual que el gemelo (RoDifArm.update).

Por cada estado:
  * v y w se aplican al inicio y se mantienen durante duration_s,
  * el brazo va de los ángulos que tenía al empezar el estado a los del
    estado, en línea recta durante duration_s (interpolación lineal),
  * al acabar el último estado, el carro frena y el brazo queda quieto.

Los estados se leen (parse_state) justo al empezar cada uno, como el gemelo:
así un ángulo que falta significa "quedarse donde quedó el estado anterior".

Sin retraso acumulado: cada estado empieza exactamente cuando debía terminar
el anterior (inicio + duración), aunque tick() llegue tarde. Si el Pico se
traba un momento, se pone al día en vez de quedar desfasado del gemelo.

No importa `machine` ni `time`: recibe `drive` (DiffDrive), `arm` (Arm) y un
reloj en ms (time.ticks_ms en el Pico). Alguien debe llamar tick() cada ~20 ms.
"""

from common.motion import parse_state
from common.ticks import ticks_add, ticks_diff

IDLE = "idle"
STATE = "state"
SEQUENCE = "sequence"


class MotionPlayer:

    def __init__(self, drive, arm, clock, on_change=None):
        self.drive = drive
        self.arm = arm
        self.clock = clock
        self.on_change = on_change

        self.mode = IDLE
        self.name = None
        self.index = 0
        self.count = 0
        self._queue = []
        self._step = None
        self._start_ms = 0
        self._start_angles = (0.0, 0.0, 0.0)

    @property
    def active(self):
        return self._step is not None

    def status(self):
        return {"mode": self.mode, "name": self.name, "step": self.index, "steps": self.count}

    # --------------------------------------------------------------- acciones

    def play(self, raw_states, name=None):
        """Reemplaza lo que se esté ejecutando (como el gemelo)."""
        self._queue = list(raw_states)
        self.mode = SEQUENCE if name is not None else STATE
        self.name = name
        self.index = 0
        self.count = len(self._queue)
        self._begin_next(self.clock())

    def stop(self):
        self._queue = []
        self._finish()

    def tick(self):
        guard = 0
        while self._step is not None and guard < 100:
            guard += 1
            elapsed = ticks_diff(self.clock(), self._start_ms)
            duration = self._step["duration_ms"]
            if elapsed < duration:
                self._move_arm(elapsed / duration)
                return
            self._move_arm(1.0)
            self._begin_next(ticks_add(self._start_ms, duration))

    # --------------------------------------------------------------- internos

    def _begin_next(self, start_ms):
        if not self._queue:
            self._finish()
            return
        raw = self._queue.pop(0)
        self.index += 1
        try:
            step = parse_state(raw, self.arm.angles)
        except ValueError as e:
            print("Player: estado %d ignorado: %s" % (self.index, e))
            self._begin_next(start_ms)
            return
        self._step = step
        self._start_ms = start_ms
        self._start_angles = self.arm.angles
        self.drive.drive(step["v"], step["w"])
        self._notify()

    def _move_arm(self, t):
        start = self._start_angles
        end = self._step["angles"]
        if start == end:
            return
        self.arm.set(
            start[0] + (end[0] - start[0]) * t,
            start[1] + (end[1] - start[1]) * t,
            start[2] + (end[2] - start[2]) * t,
        )

    def _finish(self):
        was_active = self._step is not None or self.mode != IDLE
        self.drive.stop()
        self._step = None
        self.mode = IDLE
        self.name = None
        self.index = 0
        self.count = 0
        if was_active:
            self._notify()

    def _notify(self):
        if self.on_change is not None:
            self.on_change()
