"""Carro virtual: corre en el PC la MISMA clase Car y escucha por MQTT.

Sirve para probar la app Flet sin el carro. Usa `common.car.Car` tal cual la
usa `micropython/main.py`, con motores falsos, e integra la pose (x, y, theta)
con la cinemática directa para mostrar dónde termina cada maniobra.

    python -m tools.car_simulator              # broker y prefijo de common/config.py
"""

import argparse
import json
import math
import threading
import time

import paho.mqtt.client as mqtt

from common import config
from common.car import Car
from common.kinematics import forward, integrate_pose

TICK_S = 0.02
TICKS_MASK = (1 << 30) - 1  # como time.ticks_ms() de MicroPython


def ticks_ms():
    return int(time.monotonic() * 1000) & TICKS_MASK


class FakeMotor:
    """Motor falso: solo recuerda la rapidez que le pidieron."""

    def __init__(self):
        self.speed = 0.0

    def set_speed(self, speed):
        self.speed = speed

    def stop(self):
        self.speed = 0.0


class PahoNode:
    """Lo mínimo del Node de PicoROS (subscribe/publish) encima de paho-mqtt."""

    def __init__(self, client, prefix, lock):
        self.client = client
        self.prefix = prefix
        self.lock = lock
        self.subscriptions = {}
        client.on_message = self._on_message

    def subscribe(self, topic, callback):
        self.subscriptions[topic] = callback
        if self.client.is_connected():
            self.client.subscribe(self.prefix + topic)

    def resubscribe(self):
        for topic in self.subscriptions:
            self.client.subscribe(self.prefix + topic)

    def publish(self, topic, msg):
        self.client.publish(self.prefix + topic, json.dumps(msg), retain=topic == "car/state")

    def _on_message(self, client, userdata, message):
        topic = message.topic[len(self.prefix):]
        callback = self.subscriptions.get(topic)
        if callback is None:
            return
        try:
            msg = json.loads(message.payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return
        with self.lock:
            callback(topic=topic, msg=msg)


class SimulatedCar:

    def __init__(self, broker, port, prefix):
        self.lock = threading.RLock()
        self.pose = (0.0, 0.0, 0.0)
        self.left = FakeMotor()
        self.right = FakeMotor()

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="car_sim_pico")
        self.node = PahoNode(self.client, prefix, self.lock)
        self.car = Car(
            self.node,
            self.left,
            self.right,
            half_track_m=config.WHEEL_HALF_TRACK_M,
            max_wheel_speed=config.MAX_WHEEL_SPEED_M_S,
            clock=ticks_ms,
            max_duration_s=config.MAX_COMMAND_S,
        )
        self.client.on_connect = self._on_connect
        self.client.reconnect_delay_set(1, 30)
        self.client.connect_async(broker, port, keepalive=30)

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print("MQTT: no se pudo conectar:", reason_code)
            return
        print("MQTT conectado.")
        self.node.resubscribe()
        self.car.publish_state()

    def start(self):
        self.client.loop_start()
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def _loop(self):
        last = time.monotonic()
        while True:
            now = time.monotonic()
            dt, last = now - last, now
            with self.lock:
                was_moving = self.car.moving
                if was_moving:
                    v, w = forward(self.left.speed, self.right.speed, config.WHEEL_HALF_TRACK_M)
                    self.pose = integrate_pose(*self.pose, v, w, dt)
                self.car.tick()
                if was_moving and not self.car.moving:
                    x, y, theta = self.pose
                    print(f"   pose final: x={x:.2f} m  y={y:.2f} m  theta={math.degrees(theta):.1f}°")
            time.sleep(TICK_S)


def main():
    parser = argparse.ArgumentParser(description="Carro virtual para probar la interfaz Flet")
    parser.add_argument("--broker", default=config.BROKER)
    parser.add_argument("--port", type=int, default=config.PORT)
    parser.add_argument("--prefix", default=config.PREFIX)
    args = parser.parse_args()

    sim = SimulatedCar(args.broker, args.port, args.prefix)
    sim.start()
    print(f"Carro virtual en {args.broker}:{args.port}, prefijo {args.prefix}")
    print("Empieza en (0, 0) mirando hacia +x. Mándele maniobras desde la app Flet. Ctrl+C para salir.")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        sim.stop()


if __name__ == "__main__":
    main()
