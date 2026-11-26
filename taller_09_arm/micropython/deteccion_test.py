"""Prueba de la detección del punto rojo EN EL PICO, sin WiFi, sin motores. Suba a la raíz:
deteccion_test.py, camara_test.py, config.py, drivers/ y common/ (con config.py, vision_rojo.py).

F5 y luego en la Shell:
    ver()        captura una imagen y dice dónde ve el rojo y cuánto tardó la detección
    repetir(10)  lo repite 10 veces (mueva el punto rojo frente a la cámara: cx y cy cambian)

Pegue un punto rojo de 1 cm frente a la cámara a 10 cm. Debe salir "VISTO" con area >= 2.
Si sale "no veo rojo" con el punto delante: la cámara tiñe los colores. Mire los valores de R, G, B
que imprime y ajuste rojo_r_min / rojo_dif_min en MISION (common/config.py).
"""

import time

import camara_test
from common.config import MISION
from common.vision_rojo import detectar_rojo


def ver():
    s = camara_test.iniciar()
    w, h = camara_test._size
    buf = bytearray(w * h * 2)
    if not s.capture(buf):
        print("NO llegó imagen (revise PCLK/HREF/VSYNC): corra camara_test.capturar()")
        return None
    t0 = time.ticks_ms()
    det = detectar_rojo(buf, w, h, MISION["rojo_r_min"], MISION["rojo_dif_min"], MISION["area_min"])
    ms = time.ticks_diff(time.ticks_ms(), t0)
    if det is None:
        # el píxel más rojo de la imagen, para saber qué colores está viendo la cámara
        mejor, mi = -1, 0
        for i in range(0, len(buf), 2):
            r = (buf[i] >> 3) << 3
            if r > mejor:
                mejor, mi = r, i
        hi, lo = buf[mi], buf[mi + 1]
        print("no veo rojo (%d ms). El píxel más rojo: R=%d G=%d B=%d" % (
            ms, (hi >> 3) << 3, (((hi & 7) << 3) | (lo >> 5)) << 2, (lo & 31) << 3))
    else:
        print("VISTO (%d ms): cx=%.1f cy=%.1f area=%d err_x=%.2f  [imagen %dx%d]" % (
            ms, det["cx"], det["cy"], det["area"], det["err_x"], w, h))
    return det


def repetir(n=10):
    for _ in range(n):
        ver()
        time.sleep_ms(300)
