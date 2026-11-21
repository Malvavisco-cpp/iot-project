"""Prueba de la cámara OV7670 desde Thonny, sin WiFi ni MQTT. Suba a la raíz del Pico:
camara_test.py, config.py, la carpeta drivers/ y la carpeta common/ (con camera.py).

F5 hace todo. Luego en la Shell se puede repetir:
    escanear()        ¿aparece la cámara (0x21) en el I2C de la cámara?
    capturar()        toma UNA imagen y dice si llegó y cómo se ve (barras = 16 colores distintos)
    barras(True)      pone la cámara en barras de color (prueba sin depender de la escena)
    barras(False)     imagen real
"""

import time

from machine import I2C, PWM, Pin

import config
from common import camera as camera_msg
from drivers.ov7670_wrapper import OV7670Wrapper

_pins = config.CAMERA_PINS
_sensor = None
_size = None


def escanear():
    i2c = I2C(config.CAMERA_I2C_ID, scl=Pin(_pins["scl1"]), sda=Pin(_pins["sda1"]), freq=400000)
    # El reloj tiene que estar corriendo para que la cámara conteste.
    pwm = PWM(Pin(_pins["mclk"]))
    pwm.freq(16_000_000)
    pwm.duty_u16(32768)
    time.sleep_ms(50)
    found = i2c.scan()
    print("I2C%d (SDA GP%d, SCL GP%d):" % (config.CAMERA_I2C_ID, _pins["sda1"], _pins["scl1"]),
          [hex(a) for a in found], "-> OK" if 0x21 in found else "-> NO aparece 0x21: revise SDA/SCL, 3V3 y GND")
    pwm.deinit()
    return found


def iniciar():
    global _sensor, _size
    if _sensor is not None:
        return _sensor
    i2c = I2C(config.CAMERA_I2C_ID, scl=Pin(_pins["scl1"]), sda=Pin(_pins["sda1"]), freq=400000)
    _sensor = OV7670Wrapper(
        i2c_bus=i2c, mclk_pin_no=_pins["mclk"], pclk_pin_no=_pins["pclk"], data_pin_base=_pins["data_0"],
        vsync_pin_no=_pins["vsync"], href_pin_no=_pins["href"], reset_pin_no=_pins["reset"],
        shutdown_pin_no=_pins["shutdown"],
    )
    _sensor.wrapper_configure_rgb()
    _sensor.wrapper_configure_base()
    _size = _sensor.wrapper_configure_size(config.CAMERA_SIZE_DIV)
    _sensor.wrapper_configure_test_pattern(config.CAMERA_TEST_PATTERN)
    print("cámara iniciada:", _size[0], "x", _size[1])
    return _sensor


def barras(si=True):
    iniciar().wrapper_configure_test_pattern(2 if si else 0)
    print("barras de color" if si else "imagen real")


def capturar():
    s = iniciar()
    w, h = _size
    buf = bytearray(camera_msg.frame_size(w, h))
    t0 = time.ticks_ms()
    ok = s.capture(buf)
    ms = time.ticks_diff(time.ticks_ms(), t0)
    if not ok:
        print("NO llegó imagen en %d ms: revise PCLK (GP%d), HREF (GP%d), VSYNC (GP%d) y los datos GP%d-GP%d"
              % (ms, _pins["pclk"], _pins["href"], _pins["vsync"], _pins["data_0"], _pins["data_0"] + 7))
        return None
    colores = set()
    for i in range(0, len(buf), 2):
        colores.add((buf[i] << 8) | buf[i + 1])
        if len(colores) > 64:
            break
    todo_cero = not any(buf)
    print("imagen %dx%d (%d bytes) en %d ms | colores distintos: %s%s"
          % (w, h, len(buf), ms, ">64" if len(colores) > 64 else len(colores),
             " | TODO EN CERO: la cámara no manda datos" if todo_cero else ""))
    return buf


if __name__ == "__main__":
    if 0x21 in escanear():
        barras(True)
        capturar()
        barras(False)
        capturar()
