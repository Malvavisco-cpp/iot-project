"""Diagnóstico rápido SIN mover nada: I2C/OLED, potenciómetro, WiFi y hora.

F5 corre todo y al final imprime un resumen OK / FALLA. No mueve motores ni servos
(para eso, prueba_motores.py y prueba_servos.py).
"""

import pines


def _correr(nombre, f):
    try:
        ok = f()
        return nombre, bool(ok), ""
    except Exception as e:
        return nombre, False, str(e)


def i2c():
    import prueba_i2c
    return pines.OLED_ADDR in prueba_i2c.escanear()


def oled():
    import prueba_oled
    prueba_oled.texto("Prueba OK", 0, 0)
    return True


def pot():
    import prueba_pot
    v = prueba_pot.leer()
    print("potenciómetro =", v, "(gírelo y corra de nuevo: debe cambiar)")
    return True


def wifi():
    import prueba_wifi
    return prueba_wifi.conectar()


def hora():
    import prueba_ntp
    return prueba_ntp.sincronizar()


def main():
    pruebas = [("I2C: OLED en %s" % hex(pines.OLED_ADDR), i2c), ("OLED escribe", oled),
               ("Potenciómetro (GP%d)" % pines.POT_GPIO, pot), ("WiFi", wifi), ("Hora NTP", hora)]
    resumen = [_correr(n, f) for n, f in pruebas]
    print("\n=== RESUMEN ===")
    for nombre, ok, err in resumen:
        print("%-28s %s %s" % (nombre, "OK" if ok else "FALLA", err))


if __name__ == "__main__":
    main()
