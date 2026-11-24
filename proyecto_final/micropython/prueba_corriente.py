"""Tarea 0b: ¿se están moviendo los motores? Se mide la CORRIENTE con un INA219.

Un pin del Pico NO mide corriente (un GPIO solo lee 0 o 1 y el ADC lee voltaje). Para saber
si el motor consume hace falta un sensor en serie con la alimentación de los motores:
  - INA219 (módulo de ~2 USD, I2C, resistencia shunt de 0,1 ohm incluida), o
  - una resistencia shunt pequeña + el ADC (menos preciso).
Conexión del INA219: VCC -> 3V3, GND -> GND, SDA/SCL al mismo I2C0 de la OLED (GP20/GP21;
la dirección 0x40 no choca con la 0x3C), y el positivo de la batería de los motores pasa por
VIN+ -> VIN- hacia el puente H. NO se conecta a pines del Pico lo que va a los motores.

Sin cablear: SIN PROBAR en hardware (este archivo se escribió sin el módulo a la mano).

Uso desde Thonny:  F5 y luego  monitor()   (Ctrl+C para parar)
"""

import time

from machine import I2C, Pin

import config

INA_ADDR = 0x40
R_SHUNT_OHM = 0.1          # la del módulo estándar; si es otra, cámbiela
UMBRAL_MA = 40             # por encima de la corriente en reposo + esto se considera "moviéndose"

_i2c = I2C(0, sda=Pin(config.OLED_SDA_GPIO), scl=Pin(config.OLED_SCL_GPIO), freq=400000)


def corriente_ma():
    """Corriente (mA) por el shunt: V_shunt / R. Registro 0x01: 10 uV por bit, con signo."""
    raw = _i2c.readfrom_mem(INA_ADDR, 0x01, 2)
    v = (raw[0] << 8) | raw[1]
    if v & 0x8000:
        v -= 0x10000
    return (v * 10e-6) / R_SHUNT_OHM * 1000.0


def tension_bus_v():
    raw = _i2c.readfrom_mem(INA_ADDR, 0x02, 2)
    return (((raw[0] << 8) | raw[1]) >> 3) * 0.004


def reposo_ma(n=50):
    """Promedio con los motores quietos: es la referencia."""
    total = 0.0
    for _ in range(n):
        total += corriente_ma()
        time.sleep_ms(10)
    return total / n


def monitor(periodo_ms=100):
    if INA_ADDR not in _i2c.scan():
        print("No aparece el INA219 (0x%02x) en I2C0: revise SDA/SCL, 3V3 y GND" % INA_ADDR)
        return
    base = reposo_ma()
    print("Reposo: %.1f mA. Mande un movimiento..." % base)
    while True:
        i = corriente_ma()
        mov = (i - base) > UMBRAL_MA
        print("%7.1f mA  %5.2f V  %s" % (i, tension_bus_v(), "MOVIENDO" if mov else "quieto"))
        time.sleep_ms(periodo_ms)
