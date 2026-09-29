"""Servo: traduce un ángulo a ciclo de trabajo. Lógica pura, sin hardware ni red.

No conoce MQTT ni pines: recibe un `pwm_out` (cualquier objeto con
`set_duty_u16(int)`, como `micropython.pwm_out.PWMOut` o un doble de prueba) y
un ángulo, y calcula el ancho de pulso que le corresponde según la hoja de
datos del servo (rango de ángulo, ancho de pulso mínimo/máximo, frecuencia).

Corre igual en CPython (tests, simulador) y en MicroPython (el Pico real).
"""


class Servo:

    def __init__(
        self,
        pwm_out,
        min_angle: float,
        max_angle: float,
        min_pulse_ms: float,
        max_pulse_ms: float,
        freq_hz: float,
    ):
        if min_angle >= max_angle:
            raise ValueError("min_angle debe ser menor que max_angle")
        self.pwm_out = pwm_out
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.min_pulse_ms = min_pulse_ms
        self.max_pulse_ms = max_pulse_ms
        self.freq_hz = freq_hz
        self.angle = None  # último ángulo aplicado (después de recortar al rango)

    def clamp(self, angle: float) -> float:
        return max(self.min_angle, min(self.max_angle, angle))

    def angle_to_duty_u16(self, angle: float) -> int:
        """Ángulo (recortado al rango configurado) -> ciclo de trabajo de 16 bits."""
        angle = self.clamp(angle)
        span = self.max_angle - self.min_angle
        fraction = (angle - self.min_angle) / span
        pulse_ms = self.min_pulse_ms + fraction * (self.max_pulse_ms - self.min_pulse_ms)
        period_ms = 1000.0 / self.freq_hz
        return round((pulse_ms / period_ms) * 65535)

    def set_angle(self, angle: float) -> None:
        """Mueve el servo al ángulo dado (recortado si se pasa del rango configurado)."""
        self.angle = self.clamp(angle)
        self.pwm_out.set_duty_u16(self.angle_to_duty_u16(angle))
