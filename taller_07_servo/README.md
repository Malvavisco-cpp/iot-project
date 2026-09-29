# Taller 07 — Servo por PWM + secuencia de pasos en Flet

Carpeta autocontenida (como `taller_05_alarma/`): se ejecuta **desde dentro de
`taller_07_servo/`**.

```text
  Flet (app de pasos) ──► servo/angle ──► Servo.set_angle() ──► PWMOut ──► pin PWM ──► servo
                      └──► pwm/duty  ─────────────────────────► PWMOut (uso genérico, sin Servo)
```

## Qué hace cada pieza

| Requisito | Dónde está | Test que lo cubre |
|---|---|---|
| `PWMOut`: recibe tópicos y actualiza el ciclo de trabajo | `micropython/pwm_out.py` | `tests/micropython/test_pwm_out.py` |
| `Servo`: configura el PWM a partir de un ángulo | `common/servo.py` | `tests/common/test_servo.py` |
| Tópicos de configuración del servo | `common/messages.py` (`servo/angle`, `pwm/duty`) | `tests/common/test_messages.py` |
| App Flet con ventana de pasos | `flet_ui/main.py` + `flet_ui/steps.py` | `tests/flet_ui/test_steps.py` |

`Servo` es lógica pura (sin `machine` ni MQTT): recibe cualquier objeto con
`set_duty_u16(int)` — en el Pico real es un `PWMOut`, en las pruebas un doble.
Por eso corre igual en CPython y en MicroPython, y se prueba sin hardware.

## Estructura

```text
taller_07_servo/
├── common/                    # corre igual en el Pico y en el PC
│   ├── config.py              #   broker, PREFIX, rango de ángulo/pulso del servo
│   ├── messages.py            #   contrato de tópicos Flet <-> Pico + validación
│   └── servo.py               #   Servo: ángulo -> ciclo de trabajo (lógica pura)
├── micropython/                # lo que se sube al Pico
│   ├── main.py                #   punto de entrada
│   ├── config.py               #   pines, WiFi
│   ├── pwm_out.py              #   PWMOut: actuador PWM genérico controlado por MQTT
│   ├── mqtt.py, wifi.py,
│   │   safe_scheduler.py       #   infraestructura genérica (copiada del taller 05)
│   └── .env.example            #   formato del archivo con la contraseña del WiFi
├── flet_ui/                    # interfaz
│   ├── main.py                 #   la ventana de pasos
│   ├── steps.py                #   modelo de la secuencia: sin Flet, por eso es testeable
│   └── mqtt_client.py          #   cliente paho-mqtt (solo publica)
├── tools/servo_simulator.py    # un "Pico virtual" para probar la UI sin hardware
├── tests/                      # common/, micropython/, flet_ui/
└── requirements.txt
```

## 1. Montaje del hardware

Los pines están en [`micropython/config.py`](micropython/config.py).

| Componente | Pin por defecto | Conexión |
|---|---|---|
| Señal PWM del servo | `GP15` | Servo: rojo → 5V (fuente externa, no el 3V3 de la Pico), negro → GND común, señal → `GP15` |

> ⚠️ Un servo puede pedir más corriente de la que da el regulador 3V3 de la Pico. Aliméntenlo con una fuente externa de 5V y compartan tierra (GND) con la Pico.

Ajusten `SERVO_MIN_ANGLE` / `SERVO_MAX_ANGLE` / `SERVO_MIN_PULSE_MS` / `SERVO_MAX_PULSE_MS` en [`common/config.py`](common/config.py) según la hoja de datos de su servo (los valores por defecto son los típicos de un SG90).

## 2. Poner el código en el Pico

1. Editar `WIFI_SSID` en `micropython/config.py`, `ALARM_...` no aplica aquí; solo el `PREFIX` de su grupo en `common/config.py` (ver §4).
2. Subir la carpeta `common/` completa.
3. Subir los archivos de `micropython/`: `main.py`, `config.py`, `pwm_out.py`, `mqtt.py`, `wifi.py`, `safe_scheduler.py`.
4. Crear en el Pico el archivo `.env` con la contraseña del WiFi (ver `micropython/.env.example`).
5. Reiniciar. Debe imprimir `Servo listo. Ángulo: ...`.

Requiere que el Pico ya tenga los archivos base de PicoROS (`task.py`, `scheduler.py`, `node.py`, `util.py`, `ring_buffer.py`, `umqtt/`), igual que en el taller 05.

## 3. App Flet (secuencia de pasos)

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m flet_ui.main
```

Se arma una secuencia de pasos —"poner el servo a X grados" o "esperar N
segundos"— y se ejecuta en orden con **Ejecutar**. Cada paso de ángulo publica
en `servo/angle`; **Detener** corta la secuencia antes del siguiente paso. El
formato de los pasos es intencionalmente mínimo: se estandariza en la próxima
clase.

## 4. Grupos: cambien el `PREFIX`

El broker `broker.hivemq.com` es público. En [`common/config.py`](common/config.py) cambien `robot0` por el número de su grupo. El **Pico y Flet deben usar el mismo `PREFIX`**.

## 5. Probar sin hardware: el simulador

```bash
python -m tools.servo_simulator
```

Levanta un servo virtual que usa la **misma** clase `Servo` y escucha por MQTT. En otra terminal se abre `python -m flet_ui.main` y se arma/ejecuta la secuencia normalmente; el simulador imprime el ciclo de trabajo resultante de cada paso.

## 6. Pruebas

```bash
python -m pytest -q
```

> Ejecutar **desde dentro de `taller_07_servo/`**, no desde la raíz del repo.

## Contrato MQTT

| Tópico | Contenido |
|---|---|
| `servo/angle` | `{"angle": float}` — Flet → Pico; mueve el servo a ese ángulo |
| `pwm/duty` | `{"duty_u16": int}` — Flet → Pico; ciclo de trabajo crudo (0-65535), uso genérico sin pasar por `Servo` |
