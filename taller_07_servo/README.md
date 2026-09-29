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

## Guía rápida (de cero a servo moviéndose)

1. [Montar el hardware](#1-montaje-del-hardware).
2. [Configurar antes de subir](#2-configurar-antes-de-subir) (`PREFIX`, `WIFI_SSID`, rango del servo).
3. [Subir el código al Pico con Thonny](#3-subir-el-código-al-pico-con-thonny) y reiniciar.
4. [Verificar en la consola de Thonny](#4-verificar-que-el-pico-arrancó-bien) que arrancó bien.
5. [Instalar y correr la app Flet](#5-app-flet-secuencia-de-pasos) en el PC.
6. Armar una secuencia de pasos y darle **Ejecutar**: el servo debe moverse.
7. (Opcional) [Probar sin hardware con el simulador](#6-probar-sin-hardware-el-simulador).
8. [Correr las pruebas automatizadas](#7-pruebas).

## 1. Montaje del hardware

Los pines están en [`micropython/config.py`](micropython/config.py).

| Componente | Pin por defecto | Conexión |
|---|---|---|
| Señal PWM del servo | `GP15` | Servo: rojo → 5V (fuente externa, no el 3V3 de la Pico), negro → GND común, señal → `GP15` |

> ⚠️ Un servo puede pedir más corriente de la que da el regulador 3V3 de la Pico. Aliméntenlo con una fuente externa de 5V y compartan tierra (GND) con la Pico.

## 2. Configurar antes de subir

Antes de tocar Thonny, edite estos dos archivos **en su copia local** (los que va a subir en el paso 3):

1. En [`common/config.py`](common/config.py):
   - `PREFIX`: cambien `robot0` por el número de su grupo (`UDFJC/iot_ws/robot3/`). El broker `broker.hivemq.com` es público y compartido; si no lo cambian, se mezclan con otro equipo. **El Pico y Flet deben usar el mismo `PREFIX`.**
   - `SERVO_MIN_ANGLE` / `SERVO_MAX_ANGLE` / `SERVO_MIN_PULSE_MS` / `SERVO_MAX_PULSE_MS`: ajústenlos según la hoja de datos de su servo (los valores por defecto son los típicos de un SG90, 0.5-2.5 ms a 50 Hz).
2. En [`micropython/config.py`](micropython/config.py):
   - `WIFI_SSID`: el nombre de su red (2.4 GHz; la Pico W no se conecta a 5 GHz).
   - `SERVO_GPIO`: solo si conectaron la señal del servo en un pin distinto a `GP15`.

## 3. Subir el código al Pico con Thonny

**Requisito previo:** el Pico debe tener ya los archivos base de PicoROS (`task.py`, `scheduler.py`, `node.py`, `util.py`, `ring_buffer.py` y la carpeta `umqtt/`), los mismos del taller 04/05. Si ya hicieron el taller 05 en esta misma placa, ya los tienen.

Con el Pico conectado por USB y Thonny abierto (intérprete "MicroPython (Raspberry Pi Pico)" seleccionado abajo a la derecha):

1. **Subir `common/` completa.** En el panel de archivos de Thonny (columna izquierda = su PC, columna derecha = el Pico): naveguen a `taller_07_servo/common/` en su PC, seleccionen los 4 archivos (`__init__.py`, `config.py`, `messages.py`, `servo.py`), clic derecho → **"Upload to /"** (o arrástrenlos a la columna del Pico). Deben quedar dentro de una carpeta `common/` en la raíz del Pico — si Thonny los sube sueltos a la raíz, creen la carpeta `common` a mano en el Pico primero (clic derecho en la columna del Pico → "New directory") y suban ahí adentro.
2. **Subir los archivos de `micropython/` a la raíz del Pico** (sueltos, sin subcarpeta): `main.py`, `config.py`, `pwm_out.py`, `mqtt.py`, `wifi.py`, `safe_scheduler.py`. Naveguen a `taller_07_servo/micropython/` en su PC, selecciónenlos y súbanlos igual que en el paso anterior, pero esta vez a la raíz `/` del Pico (junto a `task.py`, `node.py`, etc., no dentro de una carpeta `micropython/`).
3. **Crear el archivo `.env`** en la raíz del Pico con **solo** la contraseña del WiFi en una línea (formato en `micropython/.env.example`): en Thonny, `File > New`, escriban la contraseña, `File > Save As...` → elijan **Raspberry Pi Pico** → nombre `.env`. No se sube desde su PC (está en `.gitignore`, no va en git).
4. **Reiniciar el Pico**: botón rojo *Stop/Restart* de Thonny, o `Ctrl+D` en la Shell. `main.py` se ejecuta solo al arrancar.

Alternativa con `mpremote` (`pip install mpremote`), desde `taller_07_servo/` (comandos sin probar en placa):

```bash
mpremote cp -r common/ :
mpremote cp micropython/main.py micropython/config.py micropython/pwm_out.py :
mpremote cp micropython/mqtt.py micropython/wifi.py micropython/safe_scheduler.py :
```

## 4. Verificar que el Pico arrancó bien

En la Shell de Thonny, después de reiniciar, deben ver:

```text
Servo listo. Ángulo: None | nodo: servo_node_<id>
```

(`Ángulo: None` es normal: todavía no ha llegado ningún comando `servo/angle`). Si en cambio ven `MQTT: fallo en connect ...` repetido, revisen `WIFI_SSID`/`.env` y que el `PREFIX` sea igual al de su `common/config.py` local.

## 5. App Flet (secuencia de pasos)

En su PC, dentro de `taller_07_servo/`:

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

## 6. Probar sin hardware: el simulador

```bash
python -m tools.servo_simulator
```

Levanta un servo virtual que usa la **misma** clase `Servo` y escucha por MQTT. En otra terminal se abre `python -m flet_ui.main` y se arma/ejecuta la secuencia normalmente; el simulador imprime el ciclo de trabajo resultante de cada paso.

## 7. Pruebas

```bash
python -m pytest -q
```

> Ejecutar **desde dentro de `taller_07_servo/`**, no desde la raíz del repo.

## Contrato MQTT

| Tópico | Contenido |
|---|---|
| `servo/angle` | `{"angle": float}` — Flet → Pico; mueve el servo a ese ángulo |
| `pwm/duty` | `{"duty_u16": int}` — Flet → Pico; ciclo de trabajo crudo (0-65535), uso genérico sin pasar por `Servo` |
