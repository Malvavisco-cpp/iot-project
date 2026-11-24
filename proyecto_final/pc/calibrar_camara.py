"""Tarea 0a: ¿a qué ritmo llegan las imágenes y qué tan parejo es?

    python calibrar_camara.py            # escucha 30 s
    python calibrar_camara.py 60 --png   # 60 s y guarda la última imagen en ultima.png

Mide lo que llega al PC (WiFi + broker incluidos), que es lo que le importa a la visión.
"""

import re
import statistics
import sys
import time

import paho.mqtt.client as mqtt

import ajustes
import vision


def analizar(tiempos, tamanos_ok, tamanos_mal):
    """tiempos: instantes (s) de llegada de cada imagen. -> dict con el resumen."""
    n = len(tiempos)
    r = {"imagenes": n, "corruptas": tamanos_mal, "ok": tamanos_ok}
    if n < 2:
        return r
    dt = [b - a for a, b in zip(tiempos, tiempos[1:])]
    med = statistics.median(dt)
    r.update({
        "fps": (n - 1) / (tiempos[-1] - tiempos[0]),
        "intervalo_medio_s": statistics.mean(dt),
        "intervalo_mediana_s": med,
        "jitter_s": statistics.pstdev(dt),
        "intervalo_max_s": max(dt),
        "huecos": sum(1 for d in dt if d > 1.5 * med),   # imágenes que faltan o llegaron tarde
    })
    return r


def main():
    segundos = float(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else 30.0
    guardar = "--png" in sys.argv
    tiempos, ok, mal, ultima = [], 0, 0, {}

    def on_message(_c, _u, msg):
        nonlocal ok, mal
        m = re.search(r"rgb565_(\d+)x(\d+)$", msg.topic)
        if not m:
            return
        ancho, alto = int(m.group(1)), int(m.group(2))
        tiempos.append(time.monotonic())
        if len(msg.payload) == ancho * alto * 2:
            ok += 1
            ultima["img"] = vision.rgb565_a_bgr(msg.payload, ancho, alto)
            ultima["tam"] = (ancho, alto)
        else:
            mal += 1

    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2) if hasattr(mqtt, "CallbackAPIVersion") else mqtt.Client()
    c.on_message = on_message
    c.connect(ajustes.BROKER, ajustes.PORT)
    c.subscribe(ajustes.TOPIC_FRAME)
    print("Escuchando %s en %s durante %.0f s..." % (ajustes.TOPIC_FRAME, ajustes.BROKER, segundos))
    c.loop_start()
    time.sleep(segundos)
    c.loop_stop()

    r = analizar(tiempos, ok, mal)
    for k, v in r.items():
        print("%-22s %s" % (k, ("%.3f" % v) if isinstance(v, float) else v))
    if r["imagenes"] < 2:
        print("-> No llegaron imágenes: revise PREFIX, que el Pico esté publicando y camara_test.py.")
    elif r.get("huecos", 0):
        print("-> Hay huecos: suba CAMERA_PERIOD_MS o baje la resolución (CAMERA_SIZE_DIV).")
    if guardar and "img" in ultima:
        import cv2
        cv2.imwrite("ultima.png", ultima["img"])
        print("guardada ultima.png (%dx%d)" % ultima["tam"])


if __name__ == "__main__":
    main()
