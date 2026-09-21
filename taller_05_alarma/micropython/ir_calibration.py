"""Calibración del control remoto IR. Se ejecuta UNA vez desde Thonny (no necesita WiFi).

Le pide, en orden, las teclas 0..9 y la tecla de borrar, y al final imprime el
diccionario listo para pegar en `IR_KEYMAP` de config.py.

    1. Conecte el receptor IR (config.IR_GPIO).
    2. Abra este archivo en Thonny y ejecútelo (F5).
    3. Presione cada tecla que se le pida, una sola vez y sin mantenerla.
    4. Copie el resultado en config.py.

Si un código no coincide con el mapa por defecto, su control es distinto: use el suyo.
"""

import config
from ir_keypad import KeypadIR
from safe_scheduler import SafeScheduler

ASKED = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "C"]
LABEL = {"C": "BORRAR (elija una tecla que no sea un dígito)"}


class Calibration:

    def __init__(self):
        self.mapping = {}
        self.index = 0
        self._announce()

    def _announce(self):
        key = ASKED[self.index]
        print("\nPresione la tecla:", LABEL.get(key, key))

    def on_code(self, code):
        key = ASKED[self.index]

        if code in self.mapping:
            print("  0x%X ya fue asignado a '%s'. Presione una tecla distinta." % (code, self.mapping[code]))
            return

        self.mapping[code] = key
        print("  '%s' -> 0x%X" % (key, code))
        self.index += 1

        if self.index < len(ASKED):
            self._announce()
            return

        print("\n=== Copie esto en config.py ===")
        print("IR_KEYMAP = {")
        for code, key in self.mapping.items():
            print('    0x%X: "%s",' % (code, key))
        print("}")
        print("===============================")
        raise KeyboardInterrupt  # detiene el Scheduler; Thonny lo muestra como "Stop"


def main():
    scheduler = SafeScheduler()
    calibration = Calibration()
    KeypadIR(
        scheduler,
        pin_ir=config.IR_GPIO,
        on_code=calibration.on_code,
        min_bits=config.IR_MIN_BITS,
    )
    scheduler.run()


main()
