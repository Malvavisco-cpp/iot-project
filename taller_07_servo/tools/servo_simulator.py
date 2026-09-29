"""Servo virtual: corre en el PC la MISMA clase Servo y escucha por MQTT.

Sirve para probar la app Flet sin la placa. Usa `common.servo.Servo` tal cual
la usa `micropython/main.py`, con un "pin" falso que solo imprime.

    python -m tools.servo_simulator                 # broker y prefijo de common/config.py
"""

import argparse
import json
import threading

import paho.mqtt.client as mqtt

from common import config, messages
from common.servo import Servo


class ConsolePWM:
    """PWM falso: imprime el ciclo de trabajo en vez de mover un pin real."""

    def __init__(self):
        self.duty = 0

    def duty_u16(self, value: int) -> None:
        self.duty = value
        percent = value / 65535 * 100
        print(f"   [PWM] duty_u16={value} ({percent:.1f}%)")


class SimulatedServo:

    def __init__(self, broker: str, port: int, prefix: str):
        self.prefix = prefix
        self.pwm = ConsolePWM()
        self.servo = Servo(
            self.pwm,
            min_angle=config.SERVO_MIN_ANGLE,
            max_angle=config.SERVO_MAX_ANGLE,
            min_pulse_ms=config.SERVO_MIN_PULSE_MS,
            max_pulse_ms=config.SERVO_MAX_PULSE_MS,
            freq_hz=config.SERVO_FREQ_HZ,
        )

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="servo_sim_pico")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.reconnect_delay_set(1, 30)
        self.client.connect_async(broker, port, keepalive=30)

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code.is_failure:
            print("MQTT: no se pudo conectar:", reason_code)
            return
        print("MQTT conectado.")
        client.subscribe(self.prefix + messages.TOPIC_SERVO_ANGLE)
        client.subscribe(self.prefix + messages.TOPIC_PWM_DUTY)

    def _on_message(self, client, userdata, message) -> None:
        try:
            data = json.loads(message.payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return

        local_topic = message.topic[len(self.prefix):]
        if local_topic == messages.TOPIC_SERVO_ANGLE:
            try:
                messages.validate_angle(data)
            except ValueError as e:
                print("   payload inválido en servo/angle:", e)
                return
            self.servo.set_angle(data["angle"])
            print(f"   ángulo -> {self.servo.angle:g}°")
        elif local_topic == messages.TOPIC_PWM_DUTY:
            try:
                messages.validate_duty(data)
            except ValueError as e:
                print("   payload inválido en pwm/duty:", e)
                return
            self.pwm.duty_u16(data["duty_u16"])

    def start(self) -> None:
        self.client.loop_start()

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description="Servo virtual para probar la interfaz Flet")
    parser.add_argument("--broker", default=config.BROKER)
    parser.add_argument("--port", type=int, default=config.PORT)
    parser.add_argument("--prefix", default=config.PREFIX)
    args = parser.parse_args()

    sim = SimulatedServo(args.broker, args.port, args.prefix)
    sim.start()
    print(f"Servo virtual en {args.broker}:{args.port}, prefijo {args.prefix}")
    print("Mueve el servo desde la app Flet (python -m flet_ui.main). Ctrl+C para salir.")

    stop_event = threading.Event()
    try:
        stop_event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        sim.stop()


if __name__ == "__main__":
    main()
