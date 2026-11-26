"""Cámara OV7670 como tarea del robot: captura una imagen cada `period_ms` y la publica.

Adaptada de IoT_ws/coreografia/upy/drivers/camera.py. Diferencias, pensadas para que la
cámara nunca tumbe al robot:
  * Si la cámara no inicia (cable suelto, sin reloj) `make()` devuelve None y el robot
    sigue sin ella; el original hacía sys.exit(1) y apagaba todo.
  * `capture()` tiene límite de tiempo: sin VSYNC el DMA no termina y el robot se colgaría.
  * `should_defer()` permite no mandar imágenes mientras el robot se mueve: publicar 38 KB
    por WiFi puede tardar cientos de milisegundos y retrasaría la coreografía.
  * No publica si no hay conexión MQTT.

Tópico:  <PREFIX>camera/frame/rgb565_<ancho>x<alto>   (bytes en bruto, RGB565)
"""

import gc
import sys

from machine import Pin

from common import camera as camera_msg
from task import Task


class CameraTask(Task):

    def __init__(self, scheduler, node, sensor, width, height, period_ms=2000, should_defer=None,
                 is_online=None, on_frame=None):
        super().__init__(scheduler, period_ms, name="Camera")
        self.node = node
        self.sensor = sensor
        self.topic = camera_msg.frame_topic(width, height)
        self.frame = bytearray(camera_msg.frame_size(width, height))
        self.should_defer = should_defer
        self.is_online = is_online
        self.on_frame = on_frame    # on_frame(frame, ancho, alto): lo usa la misión autónoma
        self.width = width
        self.height = height
        self.sent = 0
        self.failed = 0
        gc.collect()

    def update(self):
        if self.should_defer is not None and self.should_defer():
            return
        online = self.is_online is None or self.is_online()
        if not online and self.on_frame is None:
            return  # sin broker y sin nadie que use la imagen no vale la pena ni capturar
        if not self.sensor.capture(self.frame):
            self.failed += 1
            if self.failed in (1, 10, 100):
                print("Cámara: no llegó imagen (¿VSYNC/PCLK/HREF mal conectados?) x%d" % self.failed)
            return
        if online:
            self.node.publish(self.topic, memoryview(self.frame))   # Flet la muestra
            self.sent += 1
        if self.on_frame is not None:
            self.on_frame(self.frame, self.width, self.height)


def make(config, scheduler, node, should_defer=None, is_online=None, on_frame=None):
    """Crea la cámara y su tarea. Devuelve None (y dice por qué) si algo falla."""
    if not getattr(config, "CAMERA_ENABLED", False):
        if not hasattr(config, "CAMERA_ENABLED"):
            print("Cámara: este config.py no tiene la parte de la cámara (CAMERA_*): es una versión vieja. Sin cámara.")
        return None
    try:
        from machine import I2C

        from drivers.ov7670_wrapper import OV7670Wrapper

        pins = config.CAMERA_PINS
        i2c = I2C(config.CAMERA_I2C_ID, scl=Pin(pins["scl1"]), sda=Pin(pins["sda1"]), freq=400000)

        sensor = OV7670Wrapper(
            i2c_bus=i2c,
            mclk_pin_no=pins["mclk"],
            pclk_pin_no=pins["pclk"],
            data_pin_base=pins["data_0"],
            vsync_pin_no=pins["vsync"],
            href_pin_no=pins["href"],
            reset_pin_no=pins["reset"],
            shutdown_pin_no=pins["shutdown"],
        )
        sensor.wrapper_configure_rgb()
        sensor.wrapper_configure_base()
        width, height = sensor.wrapper_configure_size(config.CAMERA_SIZE_DIV)
        sensor.wrapper_configure_test_pattern(config.CAMERA_TEST_PATTERN)
        task = CameraTask(scheduler, node, sensor, width, height, config.CAMERA_PERIOD_MS,
                          should_defer, is_online, on_frame)
        print("Cámara OV7670 lista: %dx%d, una imagen cada %d ms" % (width, height, config.CAMERA_PERIOD_MS))
        return task
    except Exception as e:
        print("Cámara: no se pudo iniciar, el robot sigue sin ella:")
        sys.print_exception(e)
        return None
