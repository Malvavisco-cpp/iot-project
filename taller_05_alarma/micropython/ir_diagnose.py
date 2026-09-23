"""Diagnóstico del control IR: se ejecuta UNA vez desde Thonny (no necesita WiFi)
para ver, en vivo, qué está pasando cuando algo no cuadra con la clave.

Por cada trama que llegue del control muestra el código crudo, a qué tecla
mapea según `IR_KEYMAP` de config.py, y cómo se va armando el buffer de la
clave. Al completar `PASSWORD_LENGTH` dígitos, dice si coincide o no con
`ALARM_PASSWORD`. Así se detecta a simple vista:

  - una tecla que manda un código que NO está en IR_KEYMAP ("SIN MAPEAR"),
  - una tecla que se registra dos veces seguidas (trama de repetición mal
    filtrada: revise IR_MIN_BITS),
  - o simplemente que la clave configurada no es la que creen.

    1. Conecte el receptor IR (config.IR_GPIO).
    2. Abra este archivo en Thonny y ejecútelo (F5).
    3. Digite su clave en el control, tal como lo haría normalmente.
    4. Ctrl+C para salir.
"""

import config
from ir_keypad import KeypadIR
from safe_scheduler import SafeScheduler


class Diagnostico:

    def __init__(self, keymap, password, password_length):
        self.keymap = keymap
        self.password = password
        self.password_length = password_length
        self.buffer = ""

    def on_code(self, code):
        key = self.keymap.get(code)

        if key is None:
            print("0x%X -> SIN MAPEAR (no está en IR_KEYMAP)" % code)
            return

        if key == "C":
            self.buffer = ""
            print("0x%X -> 'C' (borrar). Buffer vacío." % code)
            return

        self.buffer += key
        print(
            "0x%X -> '%s'   buffer='%s' (%d/%d)"
            % (code, key, self.buffer, len(self.buffer), self.password_length)
        )

        if len(self.buffer) < self.password_length:
            return

        if self.buffer == self.password:
            print("  == coincide con ALARM_PASSWORD ==\n")
        else:
            print("  != NO coincide con ALARM_PASSWORD ('%s') ==\n" % self.password)
        self.buffer = ""


def main():
    print("ALARM_PASSWORD configurada:", config.ALARM_PASSWORD)
    print("IR_MIN_BITS:", config.IR_MIN_BITS)
    print("Digite su clave en el control. Ctrl+C para salir.\n")

    scheduler = SafeScheduler()
    diag = Diagnostico(config.IR_KEYMAP, config.ALARM_PASSWORD, config.PASSWORD_LENGTH)
    KeypadIR(
        scheduler,
        pin_ir=config.IR_GPIO,
        on_code=diag.on_code,
        min_bits=config.IR_MIN_BITS,
    )
    scheduler.run()


main()
