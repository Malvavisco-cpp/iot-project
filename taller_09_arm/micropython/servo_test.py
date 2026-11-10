"""Diagnóstico de los servos. Se corre desde Thonny (F5); NO se llama main.py.

No usa WiFi, MQTT ni nada de common/: solo PWM. Mueve cada servo despacio, uno por
uno, alrededor del centro, e imprime qué está haciendo para que pueda comparar con lo
que ve. Detenga antes cualquier otro programa que esté usando los mismos pines.

Antes de correrlo:
  * Los servos van a una fuente de 5 V aparte (no al Pico) y con TIERRA COMÚN con el Pico.
  * Con el brazo armado, deje RANGE_DEG pequeño: el movimiento arranca desde el centro.
"""

import time

from machine import PWM, Pin

# --- Ajuste aquí ---------------------------------------------------------------
SERVOS = (            # (nombre, GPIO)
    ("hombro (alpha1)", 11),
    ("codo (alpha2)", 12),
)
RANGE_DEG = 30        # cuánto se mueve a cada lado del centro
STEP_DEG = 2          # tamaño de cada paso: más chico = más suave
STEP_MS = 25          # pausa entre pasos
FREQ_HZ = 50
MIN_PULSE_MS = 0.5    # SG90 / MG90S: 0.5 ms = -90 grados
MAX_PULSE_MS = 2.5    # 2.5 ms = +90 grados   (1.5 ms = centro)


def duty_u16(angle):
    angle = max(-90, min(90, angle))
    pulse_ms = MIN_PULSE_MS + (angle + 90) / 180 * (MAX_PULSE_MS - MIN_PULSE_MS)
    return int(pulse_ms / (1000 / FREQ_HZ) * 65535)


def go(pwm, angle):
    pwm.duty_u16(duty_u16(angle))


def sweep(pwm, start, stop):
    step = STEP_DEG if stop >= start else -STEP_DEG
    for angle in range(start, stop + (1 if step > 0 else -1), step):
        go(pwm, angle)
        time.sleep_ms(STEP_MS)


def test_servo(name, gpio):
    print("\n--- %s en GP%d ---" % (name, gpio))
    pwm = PWM(Pin(gpio))
    pwm.freq(FREQ_HZ)
    try:
        print("centro (0 grados), 1.5 ms")
        go(pwm, 0)
        time.sleep(1.5)
        print("hacia +%d" % RANGE_DEG)
        sweep(pwm, 0, RANGE_DEG)
        time.sleep(0.5)
        print("de vuelta al centro")
        sweep(pwm, RANGE_DEG, 0)
        time.sleep(0.5)
        print("hacia -%d" % RANGE_DEG)
        sweep(pwm, 0, -RANGE_DEG)
        time.sleep(0.5)
        print("de vuelta al centro")
        sweep(pwm, -RANGE_DEG, 0)
        time.sleep(0.8)
    finally:
        pwm.duty_u16(0)   # sin pulso: el servo queda libre y no zumba
        pwm.deinit()


def main():
    print("=== Diagnóstico de servos (rango +-%d grados) ===" % RANGE_DEG)
    for name, gpio in SERVOS:
        test_servo(name, gpio)
    print("\nListo. Compare con lo que vio:")
    print("  * No se movió: fuente de 5 V, tierra común con el Pico, señal en el GPIO correcto.")
    print("  * Tiembla o el Pico se reinicia: alimentación insuficiente (no usar el 5 V del Pico).")
    print("  * Se movió al revés del gemelo: invertir esa articulación en ARM_JOINTS (common/config.py).")
    print("  * Quedó corrido en el centro: ajustar offset_deg de esa articulación.")


main()
