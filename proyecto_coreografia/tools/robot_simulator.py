"""Robot virtual: corre en el PC las MISMAS clases del Pico (MotionPlayer,
Choreographer, RobotNode, Arm, DiffDrive) con motores y servos falsos.

Sirve para probar la app Flet y el gemelo sin el robot. Usa la hora del PC
como "NTP", así que arranca las coreografías a la vez que el gemelo.

    python -m tools.robot_simulator
"""

import argparse
import json
import math
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from common import config, motion
from common.arm import Arm
from common.choreographer import Choreographer
from common.drive import DiffDrive
from common.kinematics import forward, integrate_pose
from common.player import MotionPlayer
from common.robot import RobotNode
from common.ticks import TICKS_PERIOD

TICK_S = 0.02


def ticks_ms():
    return int(time.monotonic() * 1000) & (TICKS_PERIOD - 1)


def wall_now():
    return int(datetime.now(timezone.utc).timestamp() * 1000)


class FakeMotor:
    def __init__(self):
        self.speed = 0.0

    def set_speed(self, speed):
        self.speed = speed

    def stop(self):
        self.speed = 0.0


class FakeServo:
    def __init__(self):
        self.angle = 0.0

    def set_angle(self, angle):
        self.angle = angle


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
        retain = topic in (motion.TOPIC_STATUS, motion.TOPIC_ONLINE)
        self.client.publish(self.prefix + topic, json.dumps(msg), retain=retain)

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


class SimulatedRobot:

    def __init__(self, broker, port, prefix):
        self.lock = threading.RLock()
        self.pose = (0.0, 0.0, 0.0)
        self.left, self.right = FakeMotor(), FakeMotor()
        self.drive = DiffDrive(self.left, self.right, config.WHEEL_HALF_TRACK_M, config.MAX_WHEEL_SPEED_M_S)
        self.arm = Arm(FakeServo(), FakeServo(), FakeServo())

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="coreo_sim_%d" % int(time.time()))
        self.client.will_set(prefix + motion.TOPIC_ONLINE, json.dumps({"online": False}), retain=True)
        self.node = PahoNode(self.client, prefix, self.lock)
        self.player = MotionPlayer(self.drive, self.arm, ticks_ms)
        self.choreographer = Choreographer(self.player, wall_now)
        self.robot = RobotNode(self.node, self.player, self.choreographer, clock_synced=lambda: True)

        self.client.on_connect = self._on_connect
        self.client.reconnect_delay_set(1, 30)
        self.client.connect_async(broker, port, keepalive=30)

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print("MQTT: no se pudo conectar:", reason_code)
            return
        print("MQTT conectado.")
        self.node.resubscribe()
        self.node.publish(motion.TOPIC_ONLINE, {"online": True})
        with self.lock:
            self.robot.publish_status()

    def start(self):
        self.client.loop_start()
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def _loop(self):
        last = time.monotonic()
        last_step = None
        while True:
            now = time.monotonic()
            dt, last = now - last, now
            with self.lock:
                v, w = forward(self.left.speed, self.right.speed, config.WHEEL_HALF_TRACK_M)
                self.pose = integrate_pose(*self.pose, v, w, dt)
                self.choreographer.tick()
                self.player.tick()
                step = (self.player.mode, self.player.name, self.player.index)
                if step != last_step:
                    x, y, th = self.pose
                    a = self.arm.angles
                    print("  %-8s %-8s paso %-2d | pose x=%.2f m y=%.2f m θ=%.0f° | brazo (%.0f, %.0f, %.0f)°"
                          % (step[0], step[1] or "-", step[2], x, y, math.degrees(th), a[0], a[1], a[2]))
                    last_step = step
            time.sleep(TICK_S)


def main():
    parser = argparse.ArgumentParser(description="Robot virtual para probar la app y el gemelo")
    parser.add_argument("--broker", default=config.BROKER)
    parser.add_argument("--port", type=int, default=config.PORT)
    parser.add_argument("--prefix", default=config.PREFIX)
    args = parser.parse_args()

    sim = SimulatedRobot(args.broker, args.port, args.prefix)
    sim.start()
    print("Robot virtual en %s:%d, prefijo %s. Ctrl+C para salir." % (args.broker, args.port, args.prefix))
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        sim.stop()


if __name__ == "__main__":
    main()
