"""Diagnóstico de la misión EN EL PICO. Suba a la raíz junto con lo demás y ábralo en Thonny.

F5 corre todo(): archivos, importaciones, medidas, memoria, cámara, detección y la lógica de la
misión con datos de prueba. NO mueve nada. Copie lo que salga en la Shell y pásemelo.

Después, para probar el hardware (estas SÍ mueven el robot; con las ruedas en el aire):
    ruedas()      gira en el sitio 1 s y avanza 1 s
    brazo()       baja el brazo a la pose de la misión (alpha1=0, alpha2=-90) y lo vuelve a subir
    brazo_sube()  deja el brazo en la pose inicial
"""

import gc
import os
import sys
import time

import config

ARCHIVOS = [
    "main.py", "config.py", "mision_task.py", "camera_task.py", "camara_test.py", "mqtt.py",
    "task.py", "node.py", "safe_scheduler.py",
    "common/config.py", "common/mision.py", "common/vision_rojo.py", "common/player.py",
    "common/motion.py", "common/drive.py", "common/arm.py", "common/camera.py", "common/ticks.py",
    "drivers/ov7670.py", "drivers/ov7670_wrapper.py",
]
MODULOS = ["common.config", "common.mision", "common.vision_rojo", "common.player", "mision_task",
           "camera_task", "main_ok"]
_fallas = []


def _ok(msg):
    print("  OK    " + msg)


def _mal(msg):
    print("  FALLA " + msg)
    _fallas.append(msg)


def _titulo(t):
    print("\n== " + t + " ==")


def _existe(ruta):
    try:
        os.stat(ruta)
        return True
    except OSError:
        return False


def archivos():
    _titulo("1. Archivos en el Pico")
    for a in ARCHIVOS:
        if _existe(a):
            _ok(a)
        else:
            _mal("falta %s (suba la carpeta common/ y todo micropython/)" % a)


NOMBRES_CONFIG = [
    "WIFI_SSID", "NODE_NAME", "MOTOR_DRIVER", "LEFT_IN1_GPIO", "LEFT_IN2_GPIO", "RIGHT_IN1_GPIO",
    "RIGHT_IN2_GPIO", "SERVO_ALPHA1_GPIO", "SERVO_ALPHA2_GPIO", "OLED_SDA_GPIO", "OLED_SCL_GPIO",
    "CAMERA_ENABLED", "CAMERA_PINS", "CAMERA_I2C_ID", "CAMERA_SIZE_DIV", "CAMERA_TEST_PATTERN",
    "CAMERA_PERIOD_MS", "CAMERA_PAUSE_WHILE_MOVING", "CAMERA_PERIOD_MISION_MS", "SERVO_AL_ARRANCAR",
]


def config_py():
    _titulo("1b. ¿Este config.py del Pico es el nuevo?")
    faltan = [n for n in NOMBRES_CONFIG if not hasattr(config, n)]
    if faltan:
        _mal("a config.py le faltan: %s  -> es una versión vieja; suba el nuevo (guardando antes su WIFI_SSID y pines)"
             % ", ".join(faltan))
    else:
        _ok("config.py tiene todas las opciones")
    print("  pines: motores IN1/IN2 izq=%s/%s der=%s/%s | servos hombro=%s codo=%s | OLED SDA/SCL=%s/%s" % (
        getattr(config, "LEFT_IN1_GPIO", "?"), getattr(config, "LEFT_IN2_GPIO", "?"),
        getattr(config, "RIGHT_IN1_GPIO", "?"), getattr(config, "RIGHT_IN2_GPIO", "?"),
        getattr(config, "SERVO_ALPHA1_GPIO", "?"), getattr(config, "SERVO_ALPHA2_GPIO", "?"),
        getattr(config, "OLED_SDA_GPIO", "?"), getattr(config, "OLED_SCL_GPIO", "?")))


def driver_camara():
    _titulo("1c. ¿El driver de la cámara del Pico es el corregido?")
    for ruta in ("drivers/ov7670.py", "ov7670.py"):
        if _existe(ruta):
            nuevo = "shutdown_pin_no is not None" in open(ruta).read()
            (_ok if nuevo else _mal)("%s: %s" % (ruta, "corregido" if nuevo else "VIEJO (no acepta shutdown=None): suba el del repo"))
    pines = getattr(config, "CAMERA_PINS", None)
    print("  CAMERA_PINS =", pines)
    if pines is not None:
        for k, v in pines.items():
            if v is not None and (not isinstance(v, int) or v < 0 or v > 28):
                _mal("CAMERA_PINS['%s'] = %r no es un GPIO válido (0-28)" % (k, v))
    print("  carpeta del Pico:", sorted(os.listdir()))


def importar():
    _titulo("2. Importaciones (si falla una, sale el error de Python)")
    for m in MODULOS:
        if m == "main_ok":
            continue
        try:
            __import__(m)
            _ok(m)
        except Exception as e:
            _mal("no importa %s" % m)
            sys.print_exception(e)


def medidas():
    _titulo("3. Medidas de MISION (common/config.py)")
    try:
        from common.config import MISION, PREFIX
        from common.mision import faltan_medidas
    except Exception as e:
        _mal("no se pudo leer MISION: %s" % e)
        return None
    print("  PREFIX =", PREFIX, "(debe llevar su número de robot con 2 dígitos y '/' al final)")
    if not PREFIX.endswith("/"):
        _mal("el PREFIX no termina en '/'")
    falta = faltan_medidas(MISION)
    for k in ("cam_altura_m", "cam_inclinacion_deg", "fov_v_deg", "fov_h_deg", "punta_dist_m"):
        print("  %-22s %s" % (k, MISION.get(k)))
    if falta:
        _mal("sin llenar: %s  -> la misión no arranca" % ", ".join(falta))
    else:
        _ok("todas las medidas están llenas")
    return MISION


def memoria():
    _titulo("4. Memoria")
    gc.collect()
    libre = gc.mem_free()
    print("  libre: %d bytes (la imagen 160x120 ocupa 38400)" % libre)
    (_ok if libre > 90000 else _mal)("memoria %s" % ("suficiente" if libre > 90000 else "justa: pueden salir MemoryError"))


def camara():
    _titulo("5. Cámara (I2C 0x21, captura y detección del rojo)")
    try:
        import camara_test
    except Exception as e:
        _mal("no importa camara_test")
        sys.print_exception(e)
        return
    try:
        found = camara_test.escanear()
        if 0x21 not in found:
            _mal("la cámara no aparece en el I2C (0x21): revise cables y 3V3")
            return
        _ok("cámara en 0x21")
        sensor = camara_test.iniciar()
        w, h = camara_test._size
        buf = bytearray(w * h * 2)
        t0 = time.ticks_ms()
        ok = sensor.capture(buf)
        ms = time.ticks_diff(time.ticks_ms(), t0)
        if not ok:
            _mal("no llegó imagen en %d ms (PCLK/HREF/VSYNC/datos)" % ms)
            return
        _ok("imagen %dx%d en %d ms" % (w, h, ms))
        from common.config import MISION
        from common.vision_rojo import detectar_rojo
        t0 = time.ticks_ms()
        det = detectar_rojo(buf, w, h, MISION["rojo_r_min"], MISION["rojo_dif_min"], MISION["area_min"])
        ms = time.ticks_diff(time.ticks_ms(), t0)
        print("  detección tardó %d ms" % ms)
        (_ok if ms < 800 else _mal)("tiempo de detección %s" % ("bien" if ms < 800 else "lento: baje CAMERA_SIZE_DIV a 3"))
        if det is None:
            mejor, mi = -1, 0
            for i in range(0, len(buf), 2):
                r = (buf[i] >> 3) << 3
                if r > mejor:
                    mejor, mi = r, i
            hi, lo = buf[mi], buf[mi + 1]
            print("  NO ve rojo. Píxel más rojo: R=%d G=%d B=%d" % (
                (hi >> 3) << 3, (((hi & 7) << 3) | (lo >> 5)) << 2, (lo & 31) << 3))
            print("  (con el punto rojo delante, esto debe parecerse a rojo: R alto, G y B bajos)")
        else:
            _ok("VISTO cx=%.1f cy=%.1f area=%d err_x=%.2f" % (det["cx"], det["cy"], det["area"], det["err_x"]))
    except Exception as e:
        _mal("error en la cámara")
        sys.print_exception(e)


def simular():
    _titulo("6. Lógica de la misión con datos de prueba (no mueve nada)")
    try:
        from common.config import MISION
        from common.mision import Mision, distancia_al_piso, faltan_medidas
        from common.vision_rojo import detectar_rojo
    except Exception as e:
        _mal("no se pudo importar la misión")
        sys.print_exception(e)
        return
    # a) detector con una imagen sintética: fondo gris y un cuadrado rojo de 3x3
    w, h = 160, 120
    gris = ((200 >> 3) << 11) | ((200 >> 2) << 5) | (200 >> 3)
    rojo = (31 << 11)
    buf = bytearray(w * h * 2)
    for i in range(0, len(buf), 2):
        buf[i], buf[i + 1] = gris >> 8, gris & 255
    for y in (50, 51, 52):
        for x in (100, 101, 102):
            j = (y * w + x) * 2
            buf[j], buf[j + 1] = rojo >> 8, rojo & 255
    t0 = time.ticks_ms()
    det = detectar_rojo(buf, w, h, MISION["rojo_r_min"], MISION["rojo_dif_min"], MISION["area_min"])
    ms = time.ticks_diff(time.ticks_ms(), t0)
    if det is not None and abs(det["cx"] - 101) < 1 and abs(det["cy"] - 51) < 1:
        _ok("el detector encuentra un punto sintético en (101, 51) en %d ms" % ms)
    else:
        _mal("el detector falla con una imagen de prueba: %s" % det)
    # b) decisiones de la misión
    if faltan_medidas(MISION):
        print("  (se omite: faltan medidas)")
        return
    m = Mision(MISION)
    m.start()
    d = distancia_al_piso(60, h, MISION["cam_altura_m"], MISION["cam_inclinacion_deg"], MISION["fov_v_deg"])
    print("  un punto en el centro de la imagen (fila 60) estaría a %s m de la cámara" % (
        None if d is None else round(d, 3)))
    for nombre, cx, cy in (("derecha", 130, 60), ("izquierda", 30, 60), ("centro", 80, 60), ("centro y alto", 80, 30)):
        m.start()
        dd = {"cx": float(cx), "cy": float(cy), "area": 9, "err_x": (cx - w / 2) / (w / 2), "err_y": 0.0}
        print("  punto %-14s -> %s" % (nombre, m.decidir(dd, w, h) or m.estado()))
    m.start()
    print("  sin punto -> %s" % (m.decidir(None, w, h),))


def _robot():
    """Arma carro y brazo igual que main.py (para probar sin WiFi ni MQTT)."""
    from machine import PWM, Pin

    from common.arm import MeArm
    from common.drive import DiffDrive
    from common.motor import MiniMotor, Motor
    from common.servo import Servo

    def pwm(gpio, freq):
        p = PWM(Pin(gpio))
        p.freq(freq)
        p.duty_u16(0)
        return p

    def motor(pwm_gpio, in1, in2, inv, gain):
        f = config.MOTOR_PWM_FREQ_HZ
        if config.MOTOR_DRIVER == "mini":
            return MiniMotor(pwm(in1, f), pwm(in2, f), config.MAX_WHEEL_SPEED_M_S, inv, config.MOTOR_MIN_DUTY, gain)
        return Motor(pwm(pwm_gpio, f), Pin(in1, Pin.OUT, value=0), Pin(in2, Pin.OUT, value=0),
                     config.MAX_WHEEL_SPEED_M_S, inv, config.MOTOR_MIN_DUTY, gain)

    def servo(gpio, joint):
        j = config.ARM_JOINTS[joint]
        return Servo(pwm(gpio, config.SERVO_FREQ_HZ), min_pulse_ms=config.SERVO_MIN_PULSE_MS,
                     max_pulse_ms=config.SERVO_MAX_PULSE_MS, freq_hz=config.SERVO_FREQ_HZ,
                     limit_deg=config.SERVO_LIMIT_DEG, offset_deg=j["offset_deg"], inverted=j["inverted"])

    if config.STBY_GPIO is not None:
        Pin(config.STBY_GPIO, Pin.OUT, value=1)
    drive = DiffDrive(
        motor(config.LEFT_PWM_GPIO, config.LEFT_IN1_GPIO, config.LEFT_IN2_GPIO, config.LEFT_INVERTED, config.LEFT_GAIN),
        motor(config.RIGHT_PWM_GPIO, config.RIGHT_IN1_GPIO, config.RIGHT_IN2_GPIO, config.RIGHT_INVERTED, config.RIGHT_GAIN),
        config.WHEEL_HALF_TRACK_M, config.MAX_WHEEL_SPEED_M_S, config.STRAIGHT_W_TRIM,
        config.ARC_W_GAIN_LEFT, config.ARC_W_GAIN_RIGHT)
    arm = MeArm(None, servo(config.SERVO_ALPHA1_GPIO, "alpha1"), servo(config.SERVO_ALPHA2_GPIO, "alpha2"),
                shoulder_center_deg=config.MEARM_SHOULDER_CENTER_DEG, crank_center_deg=config.MEARM_CRANK_CENTER_DEG,
                min_rel_deg=config.MEARM_MIN_REL_DEG, max_rel_deg=config.MEARM_MAX_REL_DEG,
                initial=(0.0, config.MEARM_SHOULDER_CENTER_DEG, 0.0))
    return drive, arm


def ruedas():
    """Gira en el sitio 1 s (w = w_giro_deg_s) y avanza 1 s (v = v_dm_s). RUEDAS EN EL AIRE."""
    import math

    from common.config import MISION

    drive, _ = _robot()
    try:
        print("giro a la IZQUIERDA (w > 0): la rueda derecha debe ir adelante y la izquierda atrás")
        drive.drive(0.0, math.radians(MISION["w_giro_deg_s"]))
        time.sleep(1)
        drive.stop()
        time.sleep_ms(500)
        print("avance recto: las dos ruedas hacia adelante")
        drive.drive(MISION["v_dm_s"] / 10.0, 0.0)
        time.sleep(1)
    finally:
        drive.stop()
    print("listo. ¿Giró a la izquierda y avanzó hacia adelante? Si no, revise LEFT_INVERTED / RIGHT_INVERTED.")


def velocidades():
    """Prueba giros y avances de la misión a varias velocidades, 1,5 s cada uno. RUEDAS EN EL AIRE.
    Anote desde qué número empieza a moverse y póngalo en MISION (w_giro_deg_s / v_dm_s)."""
    import math

    from common.motor import duty_for

    drive, _ = _robot()
    maxv = config.MAX_WHEEL_SPEED_M_S
    mind = config.MOTOR_MIN_DUTY
    try:
        for w in (30, 60, 90, 150, 220):
            v_rueda = math.radians(w) * config.WHEEL_HALF_TRACK_M
            print("GIRO w=%d grados/s -> PWM %d %%" % (w, 100 * duty_for(v_rueda, maxv, mind) / 65535))
            drive.drive(0.0, math.radians(w))
            time.sleep_ms(1500)
            drive.stop()
            time.sleep_ms(800)
        for v in (1, 2, 3, 4):
            print("AVANCE v=%d dm/s -> PWM %d %%" % (v, 100 * duty_for(v / 10.0, maxv, mind) / 65535))
            drive.drive(v / 10.0, 0.0)
            time.sleep_ms(1500)
            drive.stop()
            time.sleep_ms(800)
    finally:
        drive.stop()
    print("listo: ¿con cuál GIRO y cuál AVANCE empezó a moverse?")


def brazo():
    """Baja el brazo a la pose de la misión y lo vuelve a subir."""
    from common.config import MISION

    _, arm = _robot()
    a0, a1, a2 = MISION["brazo_abajo"]
    print("brazo hacia ABAJO: alpha1=%s alpha2=%s" % (a1, a2))
    pasos = 20
    ini = arm.angles
    for k in range(1, pasos + 1):
        t = k / pasos
        arm.set(a0, ini[1] + (a1 - ini[1]) * t, ini[2] + (a2 - ini[2]) * t)
        time.sleep_ms(100)
    print("abajo. Mida ahora la distancia de la cámara a la punta del lápiz (punta_dist_m).")
    time.sleep(3)
    brazo_sube(arm)


def brazo_sube(arm=None):
    if arm is None:
        _, arm = _robot()
    ini = arm.angles
    fin = (0.0, config.MEARM_SHOULDER_CENTER_DEG, 0.0)
    for k in range(1, 21):
        t = k / 20
        arm.set(0.0, ini[1] + (fin[1] - ini[1]) * t, ini[2] + (fin[2] - ini[2]) * t)
        time.sleep_ms(100)
    print("brazo en la pose inicial")


def todo():
    del _fallas[:]
    print("DIAGNÓSTICO DE LA MISIÓN")
    archivos()
    config_py()
    driver_camara()
    importar()
    medidas()
    memoria()
    camara()
    simular()
    _titulo("RESUMEN")
    if _fallas:
        print("  %d problema(s):" % len(_fallas))
        for f in _fallas:
            print("   -", f)
    else:
        print("  Todo bien en el Pico. Si la misión aún no funciona, corra pc/diagnostico_mqtt.py en el PC.")


todo()
