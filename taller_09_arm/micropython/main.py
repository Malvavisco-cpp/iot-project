"""Taller 09: Carrobot con brazo MeArm - punto de entrada del Pico.

Se guarda como main.py en la raíz del Pico: arranca solo al energizar.

    motion/state    -> MotionPlayer (inmediato)  -> DiffDrive (2 motores) + MeArm (3 servos)
    motion/sequence -> Choreographer (create / delete / schedule a la hora UTC)
    NTP             -> WallClock (hora real en ms, para arrancar junto al gemelo)
    WatchdogTask    -> watchdog/stats por MQTT + OLED (scroll con el potenciómetro)
"""

import time

import machine
import ubinascii
from machine import ADC, I2C, PWM, Pin

import config
from common import motion
from common.arm import MeArm
from common.choreographer import Choreographer
from common.drive import DiffDrive
from common.motor import MiniMotor, Motor
from common.player import MotionPlayer
from common.carrobot import Carrobot
from common.servo import Servo
from common.wallclock import WallClock

from mqtt import MQTTTransport
from node import Node
from safe_scheduler import SafeScheduler
from tasks import ClockSyncTask, MotionTask, OledTask, StatsTap
from watchdog_task import WatchdogTask
from wifi import WiFiLink


def read_wifi_password():
    try:
        with open(config.WIFI_PASSWORD_FILE) as f:
            return f.read().strip()
    except OSError:
        print("Sin", config.WIFI_PASSWORD_FILE, "-> se opera sin red")
        return None


def make_pwm(gpio, freq):
    pwm = PWM(Pin(gpio))
    pwm.freq(freq)
    pwm.duty_u16(0)
    return pwm


def make_motor(pwm_gpio, in1_gpio, in2_gpio, inverted):
    f = config.MOTOR_PWM_FREQ_HZ
    if config.MOTOR_DRIVER == "mini":
        return MiniMotor(make_pwm(in1_gpio, f), make_pwm(in2_gpio, f), config.MAX_WHEEL_SPEED_M_S, inverted)
    return Motor(
        make_pwm(pwm_gpio, f),
        Pin(in1_gpio, Pin.OUT, value=0),
        Pin(in2_gpio, Pin.OUT, value=0),
        config.MAX_WHEEL_SPEED_M_S,
        inverted,
    )


def make_servo(gpio, joint):
    j = config.ARM_JOINTS[joint]
    return Servo(
        make_pwm(gpio, config.SERVO_FREQ_HZ),
        min_pulse_ms=config.SERVO_MIN_PULSE_MS,
        max_pulse_ms=config.SERVO_MAX_PULSE_MS,
        freq_hz=config.SERVO_FREQ_HZ,
        limit_deg=config.SERVO_LIMIT_DEG,
        offset_deg=j["offset_deg"],
        inverted=j["inverted"],
    )


def make_oled():
    """El robot funciona igual sin OLED: si no responde, se sigue sin pantalla."""
    try:
        from ssd1306 import SSD1306_I2C

        i2c = I2C(0, sda=Pin(config.OLED_SDA_GPIO), scl=Pin(config.OLED_SCL_GPIO), freq=400000)
        if config.OLED_I2C_ADDR not in i2c.scan():
            print("OLED: no aparece en el I2C (scan:", [hex(a) for a in i2c.scan()], ") -> sin pantalla")
            return None
        oled = SSD1306_I2C(128, 64, i2c, addr=config.OLED_I2C_ADDR)
        oled.text("Coreografia", 0, 0, 1)
        oled.text("arrancando...", 0, 16, 1)
        oled.show()
        return oled
    except Exception as e:
        print("OLED: no se pudo iniciar:", e)
        return None


def main():
    board_id = ubinascii.hexlify(machine.unique_id()).decode()
    client_id = config.NODE_NAME + "_" + board_id
    oled = make_oled()

    if config.STBY_GPIO is not None:
        Pin(config.STBY_GPIO, Pin.OUT, value=1)

    drive = DiffDrive(
        make_motor(config.LEFT_PWM_GPIO, config.LEFT_IN1_GPIO, config.LEFT_IN2_GPIO, config.LEFT_INVERTED),
        make_motor(config.RIGHT_PWM_GPIO, config.RIGHT_IN1_GPIO, config.RIGHT_IN2_GPIO, config.RIGHT_INVERTED),
        config.WHEEL_HALF_TRACK_M,
        config.MAX_WHEEL_SPEED_M_S,
    )
    arm = MeArm(
        make_servo(config.SERVO_ALPHA0_GPIO, "alpha0"),
        make_servo(config.SERVO_ALPHA1_GPIO, "alpha1"),
        make_servo(config.SERVO_ALPHA2_GPIO, "alpha2"),
        shoulder_center_deg=config.MEARM_SHOULDER_CENTER_DEG,
        crank_center_deg=config.MEARM_CRANK_CENTER_DEG,
        min_rel_deg=config.MEARM_MIN_REL_DEG,
        max_rel_deg=config.MEARM_MAX_REL_DEG,
    )

    scheduler = SafeScheduler()
    node = Node(prefix=config.PREFIX, node_name=config.NODE_NAME)
    clock = WallClock(time.ticks_ms)
    player = MotionPlayer(drive, arm, time.ticks_ms)
    choreographer = Choreographer(player, clock.now)
    # Carrobot (la clase del ejercicio) se suscribe a motion/state y motion/sequence; Node le pasa esas
    # suscripciones al MQTTTransport cuando este se registra.
    robot = Carrobot(node, player, choreographer, clock_synced=lambda: clock.synced)

    wifi = WiFiLink(scheduler, config.WIFI_SSID, read_wifi_password())

    MQTTTransport(
        scheduler,
        node,
        wifi,
        client_id=client_id,
        broker=config.BROKER,
        port=config.PORT,
        prefix=config.PREFIX,
        retain_topics=(motion.TOPIC_STATUS, motion.TOPIC_ONLINE),
        # connect() puede bloquear hasta 3 s: no se reintenta en plena coreografía.
        should_defer=lambda: player.active,
        on_connect=robot.publish_status,
    )

    MotionTask(scheduler, player, choreographer, period_ms=config.MOTION_PERIOD_MS)
    ClockSyncTask(
        scheduler,
        wifi,
        clock,
        config.NTP_HOST,
        should_defer=lambda: player.active or choreographer.due_within(5000),
        on_sync=robot.publish_status,
    )

    tap = StatsTap(node)
    WatchdogTask(scheduler, tap, wifi, period_ms=config.WATCHDOG_PERIOD_MS)
    OledTask(scheduler, oled, ADC(Pin(config.POT_GPIO)), tap, player, choreographer, clock,
             period_ms=config.OLED_PERIOD_MS)

    print("Robot listo | nodo:", client_id, "| prefijo:", config.PREFIX)
    scheduler.run()


main()
