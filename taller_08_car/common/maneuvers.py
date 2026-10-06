"""Maniobras del taller como comandos (v, w, t) para `car/cmd`.

Lógica pura: la usa la app Flet para calcular qué mandar.

    Línea recta de distancia D a rapidez v:   w = 0,  t = D / v
    Arco de radio R y ángulo phi a rapidez v: w = ±v / R,  t = phi / |w|
        (+ izquierda, - derecha; el arco recorrido es phi * R)
"""

import math

from common.messages import build_cmd

LEFT = "left"
RIGHT = "right"


def straight(distance_m, speed):
    if speed <= 0 or distance_m <= 0:
        raise ValueError("distancia y rapidez deben ser mayores que 0")
    return build_cmd(speed, 0.0, distance_m / speed)


def arc(radius_m, angle_rad, speed, direction):
    if speed <= 0 or radius_m <= 0 or angle_rad <= 0:
        raise ValueError("radio, ángulo y rapidez deben ser mayores que 0")
    if direction not in (LEFT, RIGHT):
        raise ValueError("direction debe ser LEFT o RIGHT")
    w = speed / radius_m
    t = angle_rad / w
    return build_cmd(speed, w if direction == LEFT else -w, t)


def quarter_circle(radius_m, speed, direction):
    return arc(radius_m, math.pi / 2, speed, direction)
