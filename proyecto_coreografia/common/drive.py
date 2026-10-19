"""Tracción diferencial: (v, w) -> velocidad de cada rueda (cinemática inversa)."""

from common.kinematics import inverse, scale_to_limit


class DiffDrive:

    def __init__(self, left, right, half_track_m, max_wheel_speed):
        self.left = left
        self.right = right
        self.half_track_m = half_track_m
        self.max_wheel_speed = max_wheel_speed
        self.v = 0.0
        self.w = 0.0

    def drive(self, v, w):
        """v en m/s, w en rad/s (w > 0 gira a la izquierda, como el gemelo)."""
        v_l, v_r = inverse(v, w, self.half_track_m)
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
