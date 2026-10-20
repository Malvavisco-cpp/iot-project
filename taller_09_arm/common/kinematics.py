"""Cinemática del robot diferencial. Lógica pura: corre en CPython y MicroPython.

    d: distancia del centro a cada rueda.

    Inversa  (v, w -> ruedas):   v_l = v - w*d        v_r = v + w*d
    Directa  (ruedas -> v, w):   v = (v_r + v_l)/2    w = (v_r - v_l)/(2d)

    w > 0 gira a la IZQUIERDA (antihorario), w < 0 a la DERECHA.
"""

import math


def inverse(v, w, d):
    """(v, w) -> (v_l, v_r)."""
    return v - w * d, v + w * d


def forward(v_l, v_r, d):
    """(v_l, v_r) -> (v, w)."""
    return (v_r + v_l) / 2, (v_r - v_l) / (2 * d)


def scale_to_limit(v_l, v_r, max_speed):
    """Si alguna rueda pide más de `max_speed`, reduce AMBAS en la misma proporción.

    Devuelve (v_l, v_r, k) con k <= 1. Escalar las dos por igual conserva el
    radio de giro (la forma de la trayectoria); quien llama compensa con el
    tiempo (t / k) para recorrer la misma distancia.
    """
    fastest = max(abs(v_l), abs(v_r))
    if fastest <= max_speed or fastest == 0:
        return v_l, v_r, 1.0
    k = max_speed / fastest
    return v_l * k, v_r * k, k


def integrate_pose(x, y, theta, v, w, t):
    """Pose tras moverse t segundos con v y w constantes (solución exacta de
    x' = v cos(theta), y' = v sin(theta), theta' = w).
    """
    if abs(w) < 1e-12:
        return x + v * t * math.cos(theta), y + v * t * math.sin(theta), theta
    theta_end = theta + w * t
    r = v / w
    return (
        x + r * (math.sin(theta_end) - math.sin(theta)),
        y - r * (math.cos(theta_end) - math.cos(theta)),
        theta_end,
    )
