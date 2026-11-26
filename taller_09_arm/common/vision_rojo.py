"""Detección del punto rojo en una imagen RGB565. Lógica pura, sin OpenCV ni numpy:
corre en el Pico (MicroPython) y en el PC (pruebas).

La imagen es la de la cámara: 2 bytes por píxel, byte alto primero (RGB565).
"""


def detectar_rojo(buf, ancho, alto, r_min=110, dif_min=60, area_min=2, radio=12, paso=1):
    """Busca el grupo de píxeles rojos más denso.

    Es rojo el píxel con R >= r_min, R - max(G, B) >= dif_min y G y B a lo sumo la mitad de R
    (escala 0-255; así el naranja y el rosa no cuentan).
    Con uno o dos píxeles sueltos de ruido, el centro se corre; por eso se calcula el centro
    de todos los rojos y se repite solo con los que están a `radio` píxeles de él.

    Devuelve {"cx", "cy", "area", "err_x", "err_y"} o None si no hay al menos `area_min`
    píxeles. err_x en [-1, 1]: negativo = a la izquierda del centro de la imagen.
    `paso` = 2 revisa un píxel de cada dos en cada eje (4 veces más rápido, menos fino).
    """
    rojos = []
    for y in range(0, alto, paso):
        base = y * ancho * 2
        for x in range(0, ancho, paso):
            i = base + x * 2
            hi = buf[i]
            lo = buf[i + 1]
            r = (hi >> 3) << 3
            if r < r_min:
                continue
            g = (((hi & 7) << 3) | (lo >> 5)) << 2
            b = (lo & 31) << 3
            m = g if g > b else b
            if r - m >= dif_min and m * 2 <= r:     # naranja y rosa tienen G o B altos: no son rojo
                rojos.append((x, y))
                if len(rojos) >= 3000:
                    break
        if len(rojos) >= 3000:
            break
    if len(rojos) * paso * paso < area_min:
        return None

    cx = sum(p[0] for p in rojos) / len(rojos)
    cy = sum(p[1] for p in rojos) / len(rojos)
    r2 = radio * radio
    cerca = [p for p in rojos if (p[0] - cx) ** 2 + (p[1] - cy) ** 2 <= r2]
    if len(cerca) * paso * paso < area_min:
        return None
    cx = sum(p[0] for p in cerca) / len(cerca)
    cy = sum(p[1] for p in cerca) / len(cerca)
    return {
        "cx": cx,
        "cy": cy,
        "area": len(cerca) * paso * paso,
        "err_x": (cx - ancho / 2) / (ancho / 2),
        "err_y": (cy - alto / 2) / (alto / 2),
    }
