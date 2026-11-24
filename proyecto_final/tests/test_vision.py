import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc"))

import ajustes  # noqa: E402
import calibrar_camara  # noqa: E402
import vision  # noqa: E402

ROJO = ajustes.COLORES["rojo"]


def _rgb565(r, g, b):
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


def _imagen(ancho, alto, x, y, color=(255, 0, 0), lado=4):
    px = np.full((alto, ancho), _rgb565(200, 200, 200), dtype=np.uint16)
    px[y:y + lado, x:x + lado] = _rgb565(*color)
    datos = bytearray()
    for v in px.flatten():
        datos += bytes([int(v) >> 8, int(v) & 0xFF])
    return bytes(datos)


def test_rgb565_a_bgr_tamano_malo():
    try:
        vision.rgb565_a_bgr(b"\x00" * 10, 160, 120)
    except ValueError:
        return
    raise AssertionError("debía fallar")


def test_encuentra_punto_rojo_y_error():
    bgr = vision.rgb565_a_bgr(_imagen(160, 120, 120, 50), 160, 120)
    p = vision.buscar_punto(bgr, ROJO)
    assert p is not None
    assert abs(p["cx"] - 121.5) < 1.5 and abs(p["cy"] - 51.5) < 1.5
    assert p["error_x"] > 0.4          # a la derecha del centro


def test_punto_a_la_izquierda_error_negativo():
    bgr = vision.rgb565_a_bgr(_imagen(160, 120, 10, 60), 160, 120)
    assert vision.buscar_punto(bgr, ROJO)["error_x"] < -0.7


def test_sin_punto():
    bgr = vision.rgb565_a_bgr(_imagen(160, 120, 20, 20, color=(0, 0, 255)), 160, 120)
    assert vision.buscar_punto(bgr, ROJO) is None


def test_distancia_al_piso():
    # Cámara a 0,2 m mirando 45 grados hacia abajo, centro de la imagen: tan(45)=1 -> 0,2 m.
    d = vision.distancia_al_piso(60, 120, 0.2, 45.0, 40.0)
    assert abs(d - 0.2) < 1e-6
    assert vision.distancia_al_piso(0, 120, 0.2, 0.0, 40.0) is None   # mira por encima del piso


def test_analizar_ritmo_y_huecos():
    t = [0.0, 1.0, 2.0, 3.0, 6.0, 7.0]        # falta una imagen entre 3 y 6
    r = calibrar_camara.analizar(t, 6, 0)
    assert abs(r["fps"] - 5 / 7.0) < 1e-9
    assert r["huecos"] == 1
    assert calibrar_camara.analizar([0.0], 1, 0)["imagenes"] == 1
