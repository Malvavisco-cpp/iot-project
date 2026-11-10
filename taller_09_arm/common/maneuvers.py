"""Maniobras de la evaluación 3, en las unidades de motionTopics.md (dm, °).

    Línea recta de distancia D a rapidez v:      w = 0,             t = D / v
    Arco de radio R y ángulo phi a rapidez v:   w = ±deg(v / R),   t = phi / (v / R)
        (+ izquierda, - derecha, igual que el gemelo)
"""

import math

LEFT = "left"
RIGHT = "right"


def straight(distance_dm, speed_dm_s):
    """-> (v_dm/s, w_deg/s, duration_s)."""
    if distance_dm <= 0 or speed_dm_s <= 0:
        raise ValueError("distancia y rapidez deben ser mayores que 0")
    return speed_dm_s, 0.0, distance_dm / speed_dm_s


def arc(radius_dm, angle_deg, speed_dm_s, direction):
    """-> (v_dm/s, w_deg/s, duration_s)."""
    if radius_dm <= 0 or angle_deg <= 0 or speed_dm_s <= 0:
        raise ValueError("radio, ángulo y rapidez deben ser mayores que 0")
    if direction not in (LEFT, RIGHT):
        raise ValueError("direction debe ser LEFT o RIGHT")
    w_rad = speed_dm_s / radius_dm
    duration = math.radians(angle_deg) / w_rad
    w_deg = math.degrees(w_rad)
    return speed_dm_s, (w_deg if direction == LEFT else -w_deg), duration


def quarter_circle(radius_dm, speed_dm_s, direction):
    return arc(radius_dm, 90.0, speed_dm_s, direction)
