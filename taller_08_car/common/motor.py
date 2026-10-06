"""Un motor DC detrás de un puente H tipo L298N / TB6612 (pines EN/PWM + IN1 + IN2).

No importa `machine`: recibe los pines ya creados (cualquier objeto con
`.duty_u16(int)` para el PWM y `.value(int)` para IN1/IN2), así se prueba con
dobles en el PC, igual que PWMOut en el taller 07.

    IN1=1, IN2=0 -> adelante     IN1=0, IN2=1 -> atrás     IN1=IN2=0 -> libre
"""


class Motor:

    def __init__(self, pwm, in1, in2, max_speed, inverted=False):
        """
        max_speed: rapidez lineal de la rueda (m/s) con el PWM al 100 %.
        inverted:  True si al mandar "adelante" la rueda gira hacia atrás (los
                   dos motores de un diferencial suelen ir montados en espejo).
        """
        self.pwm = pwm
        self.in1 = in1
        self.in2 = in2
        self.max_speed = max_speed
        self.inverted = inverted
        self.speed = 0.0
        self.stop()

    def set_speed(self, speed):
        """Rapidez lineal de la rueda en m/s; el signo es el sentido."""
        if speed == 0:
            self.stop()
            return
        fraction = min(abs(speed) / self.max_speed, 1.0)
        forward = (speed > 0) != self.inverted
        self.in1.value(1 if forward else 0)
        self.in2.value(0 if forward else 1)
        self.pwm.duty_u16(int(fraction * 65535 + 0.5))
        self.speed = speed

    def stop(self):
        self.pwm.duty_u16(0)
        self.in1.value(0)
        self.in2.value(0)
        self.speed = 0.0
