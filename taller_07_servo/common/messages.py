"""Contrato de mensajes entre la app Flet y el Pico.

Los tópicos van SIN prefijo; el transporte MQTT antepone `config.PREFIX`.

    Flet -> Pico
      servo/angle    {"angle": float}      mueve el servo a ese ángulo (grados)
      pwm/duty       {"duty_u16": int}     fija el ciclo de trabajo crudo (0-65535)

`servo/angle` es la que usa la app de pasos. `pwm/duty` es genérica (la
entiende PWMOut directamente): sirve para cualquier otra salida PWM que no
sea un servo, por ejemplo el brillo de un LED o la velocidad de un motor DC.
"""

TOPIC_SERVO_ANGLE = "servo/angle"
TOPIC_PWM_DUTY = "pwm/duty"

DUTY_U16_MAX = 65535


def build_angle(angle: float) -> dict:
    return {"angle": angle}


def validate_angle(msg) -> None:
    """Lanza ValueError si `msg` no es un servo/angle válido (el broker es público)."""
    if not isinstance(msg, dict):
        raise ValueError("servo/angle debe ser un objeto JSON")
    angle = msg.get("angle")
    if not isinstance(angle, (int, float)) or isinstance(angle, bool):
        raise ValueError("angle debe ser numérico")


def build_duty(duty_u16: int) -> dict:
    return {"duty_u16": duty_u16}


def validate_duty(msg) -> None:
    """Lanza ValueError si `msg` no es un pwm/duty válido."""
    if not isinstance(msg, dict):
        raise ValueError("pwm/duty debe ser un objeto JSON")
    duty = msg.get("duty_u16")
    if not isinstance(duty, int) or isinstance(duty, bool):
        raise ValueError("duty_u16 debe ser un entero")
    if not (0 <= duty <= DUTY_U16_MAX):
        raise ValueError("duty_u16 debe estar entre 0 y %d" % DUTY_U16_MAX)
