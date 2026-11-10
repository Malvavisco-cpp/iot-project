"""Tracción diferencial: (v, w) -> velocidad de cada rueda (cinemática inversa)."""

from common.kinematics import inverse, scale_to_limit


class DiffDrive:

    def __init__(self, left, right, half_track_m, max_wheel_speed,
                 straight_w_trim=0.0, arc_w_gain_left=1.0, arc_w_gain_right=1.0):
        """
        straight_w_trim:  rad/s que se suma a w cuando el robot avanza recto (w = 0, v != 0).
        arc_w_gain_left / right: factor con el que se multiplica w en un arco (v != 0, w != 0)
                          a la izquierda (w > 0) o a la derecha (w < 0).

        Es una corrección del carro REAL (motores que no responden lineal al PWM):
        se aplica aquí, en el Pico, para que el gemelo siga recibiendo los (v, w)
        teóricos. Los giros en el sitio (v = 0) no se corrigen. Con los valores por
        defecto (0, 1, 1) no cambia nada.
        """
        self.left = left
        self.right = right
        self.half_track_m = half_track_m
        self.max_wheel_speed = max_wheel_speed
        self.straight_w_trim = straight_w_trim
        self.arc_w_gain_left = arc_w_gain_left
        self.arc_w_gain_right = arc_w_gain_right
        self.v = 0.0
        self.w = 0.0

    def _corrected_w(self, v, w):
        if v == 0:
            return w
        if w == 0:
            return self.straight_w_trim
        return w * (self.arc_w_gain_left if w > 0 else self.arc_w_gain_right)

    def drive(self, v, w):
        """v en m/s, w en rad/s (w > 0 gira a la izquierda, como el gemelo)."""
        v_l, v_r = inverse(v, self._corrected_w(v, w), self.half_track_m)
        # Si una rueda no da, se bajan las dos en la misma proporción: mismo radio
        # de giro. A diferencia del taller 08, NO se alarga el tiempo: en una
        # coreografía lo que manda es ir sincronizado con el gemelo.
        v_l, v_r, k = scale_to_limit(v_l, v_r, self.max_wheel_speed)
        if k < 1.0:
            print("Drive: rueda saturada, rapidez x%.2f (mismo radio, misma duración)" % k)
        self.left.set_speed(v_l)
        self.right.set_speed(v_r)
        self.v = v * k
        self.w = w * k

    def stop(self):
        self.left.stop()
        self.right.stop()
        self.v = 0.0
        self.w = 0.0
