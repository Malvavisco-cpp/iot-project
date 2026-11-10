"""Servo de hobby (SG90 / MG90S): ángulo -> ciclo de trabajo. Lógica pura.

Recibe el PWM ya creado (cualquier objeto con `.duty_u16(int)`, como
`machine.PWM`), así se prueba con dobles en el PC (como en el taller 07).

    -90° -> min_pulse_ms     0° -> centro     +90° -> max_pulse_ms
"""


class Servo:

    def __init__(self, pwm, min_pulse_ms=0.5, max_pulse_ms=2.5, freq_hz=50,
                 limit_deg=90.0, offset_deg=0.0, inverted=False):
        self.pwm = pwm
        self.min_pulse_ms = min_pulse_ms
        self.max_pulse_ms = max_pulse_ms
        self.freq_hz = freq_hz
        self.limit_deg = limit_deg
        self.offset_deg = offset_deg
        self.inverted = inverted
        self.angle = None

    def angle_to_duty_u16(self, angle):
        a = (-angle if self.inverted else angle) + self.offset_deg
        a = max(-self.limit_deg, min(self.limit_deg, a))
        fraction = (a + 90.0) / 180.0
        pulse_ms = self.min_pulse_ms + fraction * (self.max_pulse_ms - self.min_pulse_ms)
        return int(pulse_ms * self.freq_hz / 1000.0 * 65535 + 0.5)

    def set_angle(self, angle):
        self.pwm.duty_u16(self.angle_to_duty_u16(angle))
        self.angle = angle
