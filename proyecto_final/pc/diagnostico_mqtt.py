"""Diagnóstico de la comunicación robot <-> PC (lo que usa Flet). Escucha el robot y dice qué llega.

    python diagnostico_mqtt.py                 # escucha 15 s
    python diagnostico_mqtt.py 30 --start      # arranca la misión y mira cómo responde
    python diagnostico_mqtt.py 10 --stop       # detiene la misión

Copie todo lo que imprime y pásemelo.
"""

import json
import re
import sys
import time

import paho.mqtt.client as mqtt

import ajustes

SEGUNDOS = float(next((a for a in sys.argv[1:] if not a.startswith("--")), 15))
cuentas, ultimos, frames = {}, {}, []
estados = []


def on_message(_c, _u, msg):
    local = msg.topic[len(ajustes.PREFIX):] if msg.topic.startswith(ajustes.PREFIX) else msg.topic
    clave = "camera/frame" if local.startswith("camera/frame/") else local
    cuentas[clave] = cuentas.get(clave, 0) + 1
    if clave == "camera/frame":
        m = re.search(r"rgb565_(\d+)x(\d+)$", local)
        esperado = int(m.group(1)) * int(m.group(2)) * 2 if m else None
        frames.append((local, len(msg.payload), esperado))
        return
    try:
        dato = json.loads(msg.payload.decode("utf-8"))
    except Exception:
        dato = msg.payload[:80]
    ultimos[local] = dato
    if local == "mission/status":
        estados.append(dato)
        print("  [%6.1f s] mission/status: %s" % (time.monotonic() - t0, dato))


def main():
    global t0
    print("Broker: %s:%s   PREFIX: %s" % (ajustes.BROKER, ajustes.PORT, ajustes.PREFIX))
    if not ajustes.PREFIX.rstrip("/").split("robot")[-1].isdigit() or len(ajustes.PREFIX.rstrip("/").split("robot")[-1]) != 2:
        print("AVISO: el PREFIX no tiene un número de robot de 2 dígitos")
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2) if hasattr(mqtt, "CallbackAPIVersion") else mqtt.Client()
    c.on_message = on_message
    try:
        c.connect(ajustes.BROKER, ajustes.PORT)
    except Exception as e:
        print("FALLA: no conecta al broker (%s). Revise internet/broker." % e)
        return
    c.subscribe(ajustes.PREFIX + "#")
    c.loop_start()
    t0 = time.monotonic()
    time.sleep(1.5)
    if "--start" in sys.argv:
        print("-> publicando mission/cmd start")
        c.publish(ajustes.PREFIX + "mission/cmd", json.dumps({"action": "start"}))
    if "--stop" in sys.argv:
        print("-> publicando mission/cmd stop")
        c.publish(ajustes.PREFIX + "mission/cmd", json.dumps({"action": "stop"}))
    time.sleep(SEGUNDOS)
    c.loop_stop()

    print("\n== Resumen (%.0f s) ==" % SEGUNDOS)
    for k in sorted(cuentas):
        print("  %-22s %d mensajes" % (k, cuentas[k]))
    if not cuentas:
        print("  NO llegó nada con este PREFIX: el robot está apagado, sin WiFi, en otro broker o con otro PREFIX.")
        return
    print()
    online = ultimos.get("node/online")
    print("Robot en línea:", online if online is not None else "sin dato (no llegó node/online)")
    if "watchdog/stats" in cuentas:
        print("  OK   el robot manda watchdog/stats")
    n = cuentas.get("camera/frame", 0)
    if n:
        malos = [f for f in frames if f[1] != f[2]]
        print("  OK   llegan imágenes (%d); tamaños incorrectos: %d" % (n, len(malos)))
    else:
        print("  FALLA no llegan imágenes de la cámara (camera/frame): ¿CAMERA_ENABLED, cámara conectada, robot sin moverse?")
    if "mission/status" in cuentas:
        print("  OK   el robot publica mission/status; último:", ultimos["mission/status"])
    elif "--start" in sys.argv:
        print("  FALLA el robot NO respondió al start: el Pico no tiene mision_task.py/common nuevos, "
              "o no está suscrito (reinícielo y mire su Shell).")
    else:
        print("  (mission/status solo aparece después de un start: corra con --start)")
    if "motion/status" in ultimos:
        print("motion/status:", ultimos["motion/status"])


if __name__ == "__main__":
    main()
