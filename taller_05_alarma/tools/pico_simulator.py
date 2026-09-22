"""Pico virtual: corre en el PC la MISMA lógica de la alarma y publica por MQTT.

Sirve para probar la interfaz Flet sin la placa (quien tiene el hardware es otro
compañero). Usa AlarmController y AlarmRuntime tal cual los usa main.py del Pico,
con pines falsos; los comandos del teclado reemplazan al control IR.

La puerta ya no se simula por consola: se abre/cierra con el botón "Simular
puerta" de la interfaz Flet, que publica en `common.messages.TOPIC_DOOR_SIM` (lo
único que este Pico virtual escucha por MQTT; la Pico real no escucha nada, ahí
la puerta es siempre el sensor físico).

    python -m tools.pico_simulator                  # broker y prefijo de common/config.py
    python -m tools.pico_simulator --password 4321

Comandos (escriba y Enter):
    1234     digita esas teclas, como si las presionara en el control IR
    c        tecla "borrar"
    s        muestra el estado
    q        salir
"""

import argparse
import json
import threading
import time

import paho.mqtt.client as mqtt

from common import config, messages
from common.alarm import KEY_CLEAR, AlarmController
from common.alarm_runtime import AlarmRuntime

POLL_S = 0.02
WATCHDOG_PERIOD_S = 10
TICKS_MASK = (1 << 30) - 1  # time.ticks_ms() de MicroPython da la vuelta a los 2**30 ms

HELP = __doc__.split("Comandos", 1)[1]


def ticks_ms() -> int:
    return int(time.monotonic() * 1000) & TICKS_MASK


class ConsolePin:
    """Pin falso: guarda el nivel y avisa por consola cuando cambia."""

    def __init__(self, label: str | None = None, level: int = 0):
        self.label = label
        self.level = level

    def value(self, new: int | None = None) -> int | None:
        if new is None:
            return self.level
        if new != self.level and self.label:
            print(f"   [{self.label}] {'ENCENDIDO' if new else 'apagado'}")
        self.level = new
        return None


class SimulatedPico:

    def __init__(self, broker: str, port: int, prefix: str, password: str):
        self.prefix = prefix
        self.lock = threading.Lock()
        self.door = ConsolePin()
        self.controller = AlarmController(password, config.DEFAULT_IR_KEYMAP, password_length=config.PASSWORD_LENGTH)
        self.code_of = {key: code for code, key in config.DEFAULT_IR_KEYMAP.items()}

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="alarm_sim_pico")
        self.client.will_set(
            prefix + messages.TOPIC_ONLINE,
            json.dumps(messages.build_online(False, "simulator")),
            retain=True,
        )
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_command
        self.client.reconnect_delay_set(1, 30)
        self.client.connect_async(broker, port, keepalive=30)

        self.runtime = AlarmRuntime(
            self.controller,
            door_pin=self.door,
            led_pin=ConsolePin("LED"),
            siren_pin=ConsolePin("SIRENA"),
            publish=self.publish,
            clock=ticks_ms,
        )

    def publish(self, topic: str, msg: dict) -> None:
        self.client.publish(self.prefix + topic, json.dumps(msg), retain=topic in messages.RETAINED_TOPICS)

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code.is_failure:
            print("MQTT: no se pudo conectar:", reason_code)
            return
        print("MQTT conectado.")
        client.subscribe(self.prefix + messages.TOPIC_DOOR_SIM)
        self.publish(messages.TOPIC_ONLINE, messages.build_online(True, "simulator"))
        with self.lock:
            self.runtime.mark_dirty()  # el estado retenido puede ser viejo

    def _on_command(self, client, userdata, message) -> None:
        if message.topic != self.prefix + messages.TOPIC_DOOR_SIM:
            return
        try:
            data = json.loads(message.payload.decode("utf-8"))
            messages.validate_door_set(data)
        except (ValueError, TypeError, UnicodeDecodeError):
            return
        self.set_door(data["door_open"])

    def start(self) -> None:
        self.client.loop_start()
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self) -> None:
        offline = json.dumps(messages.build_online(False, "simulator"))
        try:
            self.client.publish(self.prefix + messages.TOPIC_ONLINE, offline, retain=True).wait_for_publish(2)
        except (RuntimeError, ValueError):
            pass  # nunca llegó a conectar: no hay a quién avisar
        self.client.loop_stop()
        self.client.disconnect()

    def _loop(self) -> None:
        last_watchdog = 0.0
        while True:
            with self.lock:
                self.runtime.poll()
            if time.monotonic() - last_watchdog >= WATCHDOG_PERIOD_S:
                last_watchdog = time.monotonic()
                self.publish(
                    messages.TOPIC_WATCHDOG,
                    {"mem_free_bytes": 180000, "mem_used_bytes": 84000, "rssi": -58, "temperature_c": "24.31"},
                )
            time.sleep(POLL_S)

    # ---------------------------------------------------------- comandos

    def press(self, keys: str) -> None:
        for key in keys:
            code = self.code_of.get(key)
            if code is None:
                print(f"   tecla desconocida: {key!r}")
                continue
            with self.lock:
                self.runtime.on_ir_code(code)
            time.sleep(0.15)

    def set_door(self, is_open: bool) -> None:
        self.door.level = 1 if is_open else 0
        print("   puerta", "ABIERTA" if is_open else "cerrada")

    def show(self) -> None:
        with self.lock:
            snap = self.controller.snapshot()
        print("  ", snap)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pico virtual para probar la interfaz Flet")
    parser.add_argument("--broker", default=config.BROKER)
    parser.add_argument("--port", type=int, default=config.PORT)
    parser.add_argument("--prefix", default=config.PREFIX)
    parser.add_argument("--password", default="1234")
    args = parser.parse_args()

    pico = SimulatedPico(args.broker, args.port, args.prefix, args.password)
    pico.start()
    print(f"Pico virtual en {args.broker}:{args.port}, prefijo {args.prefix}")
    print(f"Clave: {args.password}. Comandos:{HELP}")

    try:
        while True:
            line = input("> ").strip().lower()
            if line == "q":
                break
            elif line == "s":
                pico.show()
            elif line in ("h", "?"):
                print(HELP)
            elif line == KEY_CLEAR.lower():
                pico.press(KEY_CLEAR)
            elif line:
                pico.press(line)
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        pico.stop()


if __name__ == "__main__":
    main()
