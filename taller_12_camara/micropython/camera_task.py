"""Cámara OV7670 como tarea: captura una imagen y la publica en bruto (RGB565).

Tópico:  <PREFIX>camera/frame/rgb565_<ancho>x<alto>
Si la cámara no inicia, make() lo dice y devuelve None (no tumba el programa).
"""

import gc
import sys

from machine import I2C, Pin

from task import Task


class CameraTask(Task):

    def __init__(self, scheduler, node, sensor, width, height, period_ms, is_online=None):
        super().__init__(scheduler, period_ms, name="Camera")
        self.node = node
        self.sensor = sensor
        self.topic = "camera/frame/rgb565_%dx%d" % (width, height)
        self.frame = bytearray(width * height * 2)   # 2 bytes por píxel
        self.is_online = is_online
        gc.collect()

    def update(self):
        if self.is_online is not None and not self.is_online():
            return
        if not self.sensor.capture(self.frame):
            print("Cámara: no llegó imagen (revise PCLK, HREF, VSYNC y D0-D7)")
            return
        self.node.publish(self.topic, memoryview(self.frame))


def make_sensor(config):
    from drivers.ov7670_wrapper import OV7670Wrapper

    p = config.CAMERA_PINS
    i2c = I2C(config.CAMERA_I2C_ID, scl=Pin(p["scl1"]), sda=Pin(p["sda1"]), freq=400000)
    sensor = OV7670Wrapper(
        i2c_bus=i2c, mclk_pin_no=p["mclk"], pclk_pin_no=p["pclk"], data_pin_base=p["data_0"],
        vsync_pin_no=p["vsync"], href_pin_no=p["href"], reset_pin_no=p["reset"],
        shutdown_pin_no=p["shutdown"],
    )
    sensor.wrapper_configure_rgb()
    sensor.wrapper_configure_base()
    size = sensor.wrapper_configure_size(config.CAMERA_SIZE_DIV)
    sensor.wrapper_configure_test_pattern(config.CAMERA_TEST_PATTERN)
    return sensor, size


def make(config, scheduler, node, is_online=None):
    try:
        sensor, (width, height) = make_sensor(config)
        print("Cámara lista: %dx%d" % (width, height))
        return CameraTask(scheduler, node, sensor, width, height, config.CAMERA_PERIOD_MS, is_online)
    except Exception as e:
        print("Cámara: no se pudo iniciar:")
        sys.print_exception(e)
        return None
