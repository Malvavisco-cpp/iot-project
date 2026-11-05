"""Un motor DC detrás de un puente H tipo L298N / TB6612 (pines EN/PWM + IN1 + IN2).

No importa `machine`: recibe los pines ya creados (cualquier objeto con
`.duty_u16(int)` para el PWM y `.value(int)` para IN1/IN2), así se prueba con
dobles en el PC, igual que PWMOut en el taller 07.

    IN1=1, IN2=0 -> adelante     IN1=0, IN2=1 -> atrás     IN1=IN2=0 -> libre
"""


def duty_for(speed, max_speed, min_duty=0.0):
    """Duty u16 para una rapidez distinta de 0.

    Un motor DC con carga no arranca con un PWM bajo (zona muerta): por eso el
    rango (0, max_speed] se mapea a [min_duty, 1] en vez de a [0, 1].
    """
    fraction = min(abs(speed) / max_speed, 1.0)
    return int((min_duty + (1.0 - min_duty) * fraction) * 65535 + 0.5)


class Motor:

    def __init__(self, pwm, in1, in2, max_speed, inverted=False, min_duty=0.0, gain=1.0):
        """
        max_speed: rapidez lineal de la rueda (m/s) con el PWM al 100 %.
        inverted:  True si al mandar "adelante" la rueda gira hacia atrás (los
                   dos motores de un diferencial suelen ir montados en espejo).
        min_duty:  fracción (0-1) del PWM con la que el motor apenas arranca; toda
                   rapidez distinta de 0 usa al menos este duty.
        gain:      factor de calibración de esta rueda (0.97 = 3 % más lenta).
                   Se baja en la rueda que resulte más rápida para ir recto.
        """
        self.pwm = pwm
        self.in1 = in1
        self.in2 = in2
        self.max_speed = max_speed
        self.inverted = inverted
        self.min_duty = min_duty
        self.gain = gain
        self.speed = 0.0
        self.stop()

    def set_speed(self, speed):
        """Rapidez lineal de la rueda en m/s; el signo es el sentido."""
        if speed == 0:
            self.stop()
            return
        forward = (speed > 0) != self.inverted
        self.in1.value(1 if forward else 0)
        self.in2.value(0 if forward else 1)
        self.pwm.duty_u16(duty_for(speed * self.gain, self.max_speed, self.min_duty))
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

    def __init__(self, in1, in2, max_speed, inverted=False, min_duty=0.0, gain=1.0):
        self.in1 = in1
        self.in2 = in2
        self.max_speed = max_speed
        self.inverted = inverted
        self.min_duty = min_duty
        self.gain = gain
        self.speed = 0.0
        self.stop()

    def set_speed(self, speed):
        """Rapidez lineal de la rueda en m/s; el signo es el sentido."""
        if speed == 0:
            self.stop()
            return
        duty = duty_for(speed * self.gain, self.max_speed, self.min_duty)
        forward = (speed > 0) != self.inverted
        self.in1.duty_u16(duty if forward else 0)
        self.in2.duty_u16(0 if forward else duty)
        self.speed = speed

    def stop(self):
        self.in1.duty_u16(0)
        self.in2.duty_u16(0)
        self.speed = 0.0
