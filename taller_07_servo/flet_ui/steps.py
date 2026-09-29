"""Modelo de la secuencia de pasos: sin Flet, así se prueba sin abrir ventanas
(igual que `flet_ui.monitor` en el taller 05).

Un paso es "mover el servo a X grados" o "esperar N segundos". La próxima
clase se estandariza el formato; por ahora es lo mínimo para encadenar
movimientos, p. ej.: Paso 1: poner el servo a 20°, Paso 2: esperar, Paso 3:
bajar a -45°.
"""

from dataclasses import dataclass
from typing import Callable

STEP_ANGLE = "angle"
STEP_WAIT = "wait"


@dataclass
class Step:
    kind: str      # STEP_ANGLE o STEP_WAIT
    value: float   # grados si kind == STEP_ANGLE, segundos si kind == STEP_WAIT

    def describe(self) -> str:
        if self.kind == STEP_ANGLE:
            return f"Poner el servo a {self.value:g}°"
        return f"Esperar {self.value:g} s"


class StepSequence:

    def __init__(self):
        self.steps: list[Step] = []

    def add_angle(self, angle: float) -> None:
        self.steps.append(Step(STEP_ANGLE, angle))

    def add_wait(self, seconds: float) -> None:
        self.steps.append(Step(STEP_WAIT, seconds))

    def remove(self, index: int) -> None:
        del self.steps[index]

    def clear(self) -> None:
        self.steps.clear()

    def run(
        self,
        set_angle: Callable[[float], None],
        wait: Callable[[float], None],
        on_step: Callable[[int, Step], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> None:
        """Ejecuta los pasos en orden.

        on_step(index, step) se llama justo antes de ejecutar cada paso (para
        que la UI resalte cuál está corriendo). Si is_cancelled() empieza a
        devolver True, se detiene antes del siguiente paso.
        """
        for index, step in enumerate(self.steps):
            if is_cancelled is not None and is_cancelled():
                return
            if on_step is not None:
                on_step(index, step)
            if step.kind == STEP_ANGLE:
                set_angle(step.value)
            else:
                wait(step.value)
