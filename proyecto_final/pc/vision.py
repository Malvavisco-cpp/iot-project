"""Visión del proyecto final: imagen RGB565 del Pico -> dónde está el punto de color.

Todo son funciones puras (sin MQTT) para probarlas con imágenes sintéticas.
"""

import math

import cv2
import numpy as np


def rgb565_a_bgr(datos, ancho, alto):
    """Bytes RGB565 (byte alto primero, como los manda el Pico) -> imagen BGR de OpenCV."""
    if len(datos) != ancho * alto * 2:
        raise ValueError("tamaño %d, esperado %d" % (len(datos), ancho * alto * 2))
    b = np.frombuffer(datos, dtype=np.uint8).astype(np.uint16)
    v = (b[0::2] << 8) | b[1::2]
    r = ((v >> 11) & 0x1F) * 255 // 31
    g = ((v >> 5) & 0x3F) * 255 // 63
    bl = (v & 0x1F) * 255 // 31
    return np.dstack([bl, g, r]).astype(np.uint8).reshape(alto, ancho, 3)


def mascara_color(bgr, rangos):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask = np.zeros(bgr.shape[:2], dtype=np.uint8)
    for lo, hi in rangos:
        mask |= cv2.inRange(hsv, np.array(lo, dtype=np.uint8), np.array(hi, dtype=np.uint8))
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))


def buscar_punto(bgr, rangos, area_min=12):
    """Blob más grande del color. -> dict(cx, cy, area, error_x, error_y) o None.

    error_x en [-1, 1]: negativo = el punto está a la izquierda del centro de la imagen
    (el carro debe girar a la izquierda), positivo = a la derecha.
    """
    mask = mascara_color(bgr, rangos)
    n, _etiq, stats, cent = cv2.connectedComponentsWithStats(mask)
    if n <= 1:
        return None
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    area = int(stats[i, cv2.CC_STAT_AREA])
    if area < area_min:
        return None
    alto, ancho = bgr.shape[:2]
    cx, cy = float(cent[i][0]), float(cent[i][1])
    return {"cx": cx, "cy": cy, "area": area,
            "error_x": (cx - ancho / 2) / (ancho / 2), "error_y": (cy - alto / 2) / (alto / 2)}


def distancia_al_piso(cy, alto, altura_m, inclinacion_deg, fov_vert_deg):
    """Distancia horizontal (m) hasta un punto del piso visto en la fila `cy`.

    Modelo: cámara a `altura_m` mirando `inclinacion_deg` hacia abajo; el rayo del píxel
    baja inclinacion + atan((cy - alto/2) / f). None si el rayo no toca el piso.
    """
    f = (alto / 2) / math.tan(math.radians(fov_vert_deg) / 2)
    bajada = math.radians(inclinacion_deg) + math.atan((cy - alto / 2) / f)
    if bajada <= 0:
        return None
    return altura_m / math.tan(bajada)


def marcar(bgr, punto):
    """Copia de la imagen con una cruz sobre el punto (para depurar)."""
    out = bgr.copy()
    if punto:
        cv2.drawMarker(out, (int(punto["cx"]), int(punto["cy"])), (0, 255, 0), cv2.MARKER_CROSS, 8, 1)
    return out
