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


class MiniMotor:
    """Un motor DC en un L298N mini (placa roja pequeña, chip MX1508): no tiene
    ENA/ENB, solo IN1/IN2 por motor, y la velocidad se da con PWM en esos
    mismos pines.

        IN1=PWM, IN2=0 -> adelante     IN1=0, IN2=PWM -> atrás     IN1=IN2=0 -> libre

    in1 / in2: objetos con `.duty_u16(int)` (p. ej. `machine.PWM`).
    """

    def __init__(self, in1, in2, max_speed, inverted=False):
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
        duty = int(min(abs(speed) / self.max_speed, 1.0) * 65535 + 0.5)
        forward = (speed > 0) != self.inverted
        self.in1.duty_u16(duty if forward else 0)
        self.in2.duty_u16(0 if forward else duty)
        self.speed = speed

    def stop(self):
        self.in1.duty_u16(0)
        self.in2.duty_u16(0)
        self.speed = 0.0
