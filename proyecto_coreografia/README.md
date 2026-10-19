# Proyecto segundo corte — Coreografía

El robot (carro diferencial + brazo de 3 servos) recibe una secuencia de pasos por MQTT y la
ejecuta **a la hora indicada, sincronizado con su gemelo virtual** (`IoT_ws/coreografia`).

Carpeta autocontenida (como `taller_05_alarma/`, `taller_07_servo/` y `taller_08_car/`): se
ejecuta **desde dentro de `proyecto_coreografia/`** y trae **todo** lo que necesita el Pico,
incluidos los archivos base de PicoROS y el driver del OLED. No se asume nada cargado en la placa.

```text
  Flet ─┬─► motion/state    ─► MotionPlayer ─┬─► DiffDrive ─► 2 motores (L298N mini)
        │                                    └─► Arm       ─► 3 servos (alpha0, alpha1, alpha2)
        └─► motion/sequence ─► Choreographer ─► (a la hora run_at, con reloj NTP) ─► MotionPlayer
            (el gemelo virtual recibe exactamente los mismos mensajes)

  WatchdogTask ─► watchdog/stats ─► Flet
              └─► OLED (scroll con el potenciómetro)
  Robot ─► motion/status (retenido) ─► Flet
```

## Las 6 evaluaciones y dónde se cumplen

| # | Evaluación | Dónde | Prueba |
|---|---|---|---|
| 1 | Control del carro con tópicos (`motionTopics.md`) | `common/motion.py`, `common/robot.py`, `common/player.py` | `test_motion_parse.py`, `test_robot_node.py`, `test_player.py` |
| 2 | Interfaz amigable en el PC | `flet_ui/main.py` | `tests/flet_ui/test_model.py` |
| 3 | Línea recta y 1/4 de círculo | `common/maneuvers.py` (bloque 2 de la app) | `test_oled_and_maneuvers.py` |
| 4 | Brazo en los ángulos asignados, con la demora asignada | `common/arm.py`, `common/servo.py`, interpolación en `player.py` | `test_player.py`, `test_hardware_logic.py` |
| 5 | Watchdog en el OLED, scroll con el potenciómetro | `common/oled_view.py`, `micropython/tasks.py` (`OledTask`) | `test_oled_and_maneuvers.py` |
| 6 | Recibir la secuencia y ejecutarla junto al gemelo | `common/choreographer.py`, `common/wallclock.py`, `micropython/sntp.py` | `tests/integration/test_twin_sync.py` |

`test_twin_sync.py` porta a Python la lógica del gemelo (`3D/RoDifArm.js`), corre la misma
coreografía en los dos y verifica que arrancan al mismo tiempo, que el brazo va igual en cada
instante y que terminan en el mismo lugar.

## Cómo interpreta el robot los mensajes (igual que el gemelo)

Lo que sigue se copió del código del gemelo (`RoDifArm.js`), porque es lo que define "estar sincronizado":

* **Unidades:** `v_dm/s` en dm/s, `w_deg/s` y los ángulos en grados. `w > 0` gira a la **izquierda**.
* **Campos que faltan:** `v` o `w` → 0; `duration_s` → 1 s; **un ángulo que falta deja el brazo donde está** (el `.md` dice "cero", pero el gemelo lo mantiene, y se sigue al gemelo).
* **El brazo se mueve en línea recta durante `duration_s`** desde donde estaba hasta los ángulos pedidos. No salta.
* **`alpha2` es el ángulo absoluto del antebrazo.** El gemelo dibuja el codo con `alpha2 − alpha1`, así que el servo del codo recibe `alpha2 − alpha1`.
* Un `motion/state` **reemplaza** lo que se esté ejecutando. Al acabar una secuencia, el carro frena.
* `run_at` en el pasado → arranca ya. Programar dos veces la misma secuencia → vale la última hora.
* Los dos gemelos escriben distinto los ángulos: `alpha0_deg` (`RoDifArm.js` y el `.md`) y `alfa0_deg` (`robot_coreografia_mqtt.html`). La app manda **las dos** y el robot acepta las dos.

**Sincronización:** el robot pone su hora por **NTP con milisegundos** (el `ntptime` de MicroPython solo da segundos enteros) y la mantiene con `ticks_ms()`. El gemelo usa la hora del PC, así que **el PC también debe tener la hora sincronizada** (Windows: Configuración → Hora e idioma → *Sincronizar ahora*). Si el Pico se traba un momento, cada paso empieza cuando debía (no cuando pudo), así que no se va desfasando.

## Estructura

```text
proyecto_coreografia/
├── common/                 # corre igual en el Pico y en el PC  -> carpeta common/ del Pico
│   ├── config.py           #   broker, PREFIX, d, rapidez máx., ajuste de los servos
│   ├── motion.py           #   tópicos + cómo se lee un estado (igual que el gemelo)
│   ├── player.py           #   MotionPlayer: ejecuta estados (v, w, brazo interpolado)
│   ├── choreographer.py    #   create / delete / schedule / execute_now con run_at
│   ├── robot.py            #   RobotNode: conecta los tópicos con lo anterior
│   ├── drive.py            #   DiffDrive: (v, w) -> ruedas (cinemática inversa)
│   ├── arm.py, servo.py    #   brazo de 3 servos
│   ├── motor.py            #   MiniMotor (L298N mini) y Motor (L298N grande / TB6612)
│   ├── kinematics.py       #   cinemática diferencial (del taller 08)
│   ├── maneuvers.py        #   recta 1 m y 1/4 de círculo en dm y °
│   ├── oled_view.py        #   qué mostrar en el OLED y scroll del potenciómetro
│   ├── timeutil.py, wallclock.py, ticks.py   # fechas ISO, NTP, hora real en ms
├── micropython/            # -> RAÍZ del Pico
│   ├── main.py             #   punto de entrada (arranca solo)
│   ├── config.py           #   WiFi y pines
│   ├── tasks.py            #   MotionTask, ClockSyncTask, OledTask, StatsTap
│   ├── sntp.py             #   consulta NTP con milisegundos
│   ├── ssd1306.py          #   driver del OLED (micropython-lib)
│   ├── mqtt.py, wifi.py, safe_scheduler.py               # infraestructura (talleres 05-08)
│   ├── node.py, task.py, scheduler.py, util.py,
│   │   ring_buffer.py, watchdog_task.py, umqtt/simple.py # base de PicoROS
│   └── .env.example
├── flet_ui/                # la app del PC: main.py, model.py, mqtt_client.py
├── tools/robot_simulator.py  # robot virtual con las mismas clases (sin hardware)
└── tests/
```

---

## Paso a paso (desde cero)

### 0. MicroPython en el Pico (solo la primera vez)

1. Instalen **Thonny** (thonny.org).
2. Desconecten el Pico, mantengan presionado **BOOTSEL**, conecten el USB y suelten: aparece como memoria USB (`RPI-RP2` o `RP2350`).
3. En Thonny: **Herramientas > Opciones > Intérprete** → **"Instalar o actualizar MicroPython"** → familia **RP2**, variante de su placa (**Raspberry Pi Pico 2 W** o **Pico W**, tiene que ser la "W") → **Instalar**.
4. En esa ventana, intérprete **"MicroPython (Raspberry Pi Pico)"** → **OK**. La Shell debe decir `MicroPython v1.xx ... Pico 2 W`.

> ⚠️ **"No module named 'machine'"**: Thonny está corriendo el archivo con el Python del PC. Abajo a la derecha debe decir **"MicroPython (Raspberry Pi Pico)"**, no "Local Python 3". Y a `main.py` no se le da *Run* desde el PC: se sube al Pico y se reinicia (paso 4).

### 1. Conexiones

Pines en [`micropython/config.py`](micropython/config.py). Son números **GPIO** (`GP2` = `2`), no el número de pata.

| Pico | Va a | |
|---|---|---|
| `GP2`, `GP3` | IN1, IN2 del L298N mini | motor izquierdo |
| `GP6`, `GP7` | IN3, IN4 del L298N mini | motor derecho |
| `GP10` | señal servo **alpha0** (base) | |
| `GP11` | señal servo **alpha1** (hombro) | |
| `GP12` | señal servo **alpha2** (codo) | |
| `GP4` (SDA), `GP5` (SCL) | OLED SSD1306 128x64 I2C | VCC → 3V3, GND → GND |
| `GP26` (ADC0) | pata **central** del potenciómetro | las otras dos a 3V3 y GND |
| `GND` | GND del L298N, de los servos y de las baterías | **tierra común obligatoria** |

> ⚠️ **Alimentación:** los motores van con su batería al `+`/`-` del L298N mini. Los **servos van a una fuente de 5 V aparte** (3 servos moviéndose piden más de lo que da el Pico por USB; si se alimentan del Pico, se reinicia en plena coreografía). Todas las tierras unidas.
>
> ⚠️ **PWM:** dos pines que comparten *slice* comparten frecuencia, y los motores van a 1000 Hz y los servos a 50 Hz. Slice = `(GPIO // 2) % 8`: GP2/3 = 1, GP6/7 = 3, GP10/11 = 5, GP12 = 6 → no chocan. Si cambian pines, revisen que un servo no quede en el mismo slice que un motor (p. ej. **GP18/19 comparten slice con GP2/3**).

Si tienen un L298N grande o un TB6612, pongan `MOTOR_DRIVER = "l298n"` y usen `LEFT_PWM_GPIO`/`RIGHT_PWM_GPIO` (ENA/ENB), como en el taller 08.

### 2. Configurar antes de subir

Editen **en su copia local** (si cambian algo después, hay que volver a subir ese archivo):

1. [`common/config.py`](common/config.py)
   - `PREFIX`: `UDFJC/iot_ws/robot4/` (su grupo). Debe ser igual en Pico, Flet y gemelo.
   - `BROKER`: `broker.hivemq.com`, o la IP del broker de la clase (ver §7).
   - `WHEEL_HALF_TRACK_M` y `MAX_WHEEL_SPEED_M_S`: copien los que calibraron en el taller 08.
2. [`micropython/config.py`](micropython/config.py): `WIFI_SSID` (2.4 GHz) y pines si cambiaron.

### 3. Subir el código al Pico con Thonny

> ⚠️ **No copien y peguen código desde el chat o una página web.** En el taller 08 eso convirtió `__init__` en `_init_` y la clase dejó de funcionar sin dar un error claro. **Suban los archivos** desde la carpeta del repo.

Con el intérprete en **MicroPython (Raspberry Pi Pico)**: **Ver > Archivos**. Arriba "Este computador", abajo "Raspberry Pi Pico".

1. En "Este computador", vayan a `proyecto_coreografia/`.
2. Clic derecho en la carpeta **`common`** → **"Subir a /"**.
3. Entren a `micropython/`, seleccionen **todo** (todos los `.py` **y la carpeta `umqtt`**) → clic derecho → **"Subir a /"**. Quedan sueltos en la raíz.
4. **Archivo > Nuevo**, escriban **solo** la contraseña del WiFi, **Archivo > Guardar como... → Raspberry Pi Pico → `.env`**.
5. Si el Pico tenía archivos de otro taller (`car_task.py`, `pwm_out.py`...), bórrenlos o no estorban; lo importante es que `main.py`, `config.py` y `common/` sean los de este proyecto.

El Pico debe quedar así:

```text
/
├── .env
├── main.py  config.py  tasks.py  sntp.py  ssd1306.py
├── mqtt.py  wifi.py  safe_scheduler.py
├── node.py  task.py  scheduler.py  util.py  ring_buffer.py  watchdog_task.py
├── umqtt/simple.py
└── common/  __init__.py arm.py choreographer.py config.py drive.py kinematics.py maneuvers.py
             motion.py motor.py oled_view.py player.py robot.py servo.py ticks.py timeutil.py wallclock.py
```

Para confirmar que ningún archivo quedó dañado, detengan el programa y peguen esto en la Shell (esto sí se puede pegar, es corto):

```python
import os
for d in ('/', '/common'):
    for f in os.listdir(d):
        if f.endswith('.py') and 'def _init_(' in open(d.rstrip('/') + '/' + f).read():
            print('DAÑADO:', d, f)
print('revisión lista')
```

### 4. Arrancar y verificar

Reinicien con `Ctrl+D` (o el botón rojo **Detener/Reiniciar**). En la Shell deben ver, entre otras líneas:

```text
Robot listo | nodo: coreo_node_<id> | prefijo: UDFJC/iot_ws/robot4/
WiFi conectado, IP: 192.168.x.x
MQTT conectado a broker.hivemq.com
Reloj sincronizado (UTC): 2026-10-19T20:00:01.234Z
```

En el OLED aparece el estado del robot y los datos del Watchdog. **Girar el potenciómetro hace scroll** (la barra de la derecha indica dónde va). Si no hay OLED, el robot funciona igual.

### 5. App Flet en el PC

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m flet_ui.main
```

Arriba deben ver **Broker: conectado**, **Robot: quieto** y **Hora robot: OK (NTP)**.

| Bloque | Para qué | Evaluación |
|---|---|---|
| 1. Estado inmediato | Mandar un `motion/state` con v, w, ángulos y duración. **Solo brazo** manda v = w = 0. **DETENER** manda un estado quieto de 0.1 s (frena robot y gemelo, el brazo se queda) | 1 y 4 |
| 2. Maniobras | **Recta 1 m**, **1/4 círculo izquierda/derecha** (R = 1 m), con la rapidez que pongan | 3 |
| 3. Coreografía | Armar pasos (o **Ejemplo del enunciado**), **Cargar en robot**, **Ejecutar ya**, **Programar en N s**, **Programar a esa hora**, **Borrar del robot** | 6 |
| 4. Robot | Qué está haciendo, secuencias cargadas, programadas, y el Watchdog (lo mismo que el OLED) | 5 |

"Ejecutar ya" y "Programar" mandan primero `create` y luego `schedule`, así nadie se queda sin la secuencia. La app muestra dónde termina la coreografía (pose final estimada) y la duración total.

### 6. Calibrar el brazo

1. Bloque 1, **Solo brazo** con `0, 0, 0` y 1 s: los tres servos deben quedar como el brazo del gemelo en reposo. Si alguno queda corrido, ajusten su `offset_deg` en `ARM_JOINTS` de `common/config.py`.
2. `alpha0 = 45`: la base debe girar hacia el **mismo lado** que en el gemelo. Si gira al revés, `inverted: True` en esa articulación. Repitan con `alpha1` y `alpha2`.
3. Recuerden que `alpha2` es el ángulo absoluto del antebrazo: `alpha1 = 45, alpha2 = 45` deja el codo **recto** (servo del codo en 0°).
4. Vuelvan a subir `common/config.py` y reinicien después de cada cambio.

### 7. El gemelo virtual

Los dos gemelos reciben los mismos mensajes que el robot; solo hay que apuntarlos al mismo broker y prefijo.

**Opción A — gemelo alterno, funciona con `broker.hivemq.com` desde cualquier parte:**
abran `robot_coreografia_mqtt.html` (en `IoT_ws/coreografia/`, o en la página del profesor),
*Broker WebSocket URL* `wss://broker.hivemq.com:8884/mqtt`, *Topic base* `UDFJC/iot_ws/robot4/motion`,
*Robot index* 0 → **Connect**.

**Opción B — gemelo oficial (`PubSub_client_web.html` + `RoDifArm.js`), con el broker de la clase:**
ese cliente arma la dirección como `ws://IP:puerto` (sin TLS), así que se usa con el broker
local de la clase (p. ej. Mosquitto con websockets en el puerto 9001):

1. En `common/config.py` pongan `BROKER = "<IP del broker>"` (puerto 1883) y vuelvan a subirlo al Pico.
2. Sirvan la carpeta del gemelo por http (los navegadores bloquean `ws://` desde una página https):
   ```bash
   cd IoT_ws/coreografia
   python -m http.server 8080
   ```
3. Abran `http://localhost:8080/PubSub_client_web.html?transport=mqtt&host=<IP>&port=9001&prefix=UDFJC/iot_ws&robot=4`
   → **Connect** → **Subscribe Robot**.

En ambos casos el robot 4 del gemelo escucha `UDFJC/iot_ws/robot4/motion/state` y `.../motion/sequence`.

### 8. La demostración

1. Robot en el piso, gemelo abierto, app conectada y **Hora robot: OK**.
2. Bloque 3 → **Ejemplo del enunciado** (o su coreografía) → **Programar en N s** con 10 s.
3. A los 10 s el robot y el gemelo arrancan juntos. En la Shell sale `Coreografía: arranca 'hello' (X ms después de lo programado)` — X debe ser menor que 20.

### 9. Probar sin hardware

```bash
python -m tools.robot_simulator
```

Robot virtual con **las mismas clases**, usando la hora del PC como NTP. Con la app y el gemelo abiertos, imprime cada paso con la pose y el brazo. Apáguenlo cuando usen el robot real (si no, los dos responden al mismo `PREFIX`).

### 10. Pruebas automatizadas

```bash
python -m pytest -q
```

---

## Contrato MQTT

| Tópico | Sentido | Retenido | Contenido |
|---|---|---|---|
| `motion/state` | PC → robot y gemelo | no | `{"v_dm/s", "w_deg/s", "alpha0_deg", "alpha1_deg", "alpha2_deg", "duration_s"}` |
| `motion/sequence` | PC → robot y gemelo | no | `create` (`name`, `states`, `run_at` opcional), `delete`, `schedule` (`run_at`: `"now"` o ISO UTC), `execute_now` |
| `motion/status` | robot → PC | sí | `{"mode", "name", "step", "steps", "arm_deg", "sequences", "scheduled", "clock_synced"}` |
| `watchdog/stats` | robot → PC | no | telemetría del `WatchdogTask` de PicoROS |
| `node/online` | robot → PC | sí | `{"online": bool}`; Last Will si el robot se cae |

`create` con `run_at` programa la secuencia en el robot (lo dice el `.md`), pero **los gemelos lo ignoran**; por eso la app manda siempre un `schedule` aparte.

## Si algo no funciona

| Síntoma | Causa probable |
|---|---|
| `No module named 'machine'` | Thonny en "Local Python 3" → paso 0 |
| `'X' object has no attribute ...` raro, o una clase "vacía" | Código copiado y pegado (`_init_`) → suban el archivo (paso 3) y corran la revisión |
| `ImportError: no module named ...` | Falta subir ese archivo o carpeta → comparen con el árbol del paso 3 |
| `WiFi: reintentando, status = -2` / `-3` | Red no encontrada (SSID, 5 GHz) / contraseña mal en `.env` |
| **Hora robot: SIN sincronizar** | Sin internet hacia `pool.ntp.org` (red de la U bloquea UDP 123): cambien `NTP_HOST` a la IP del servidor NTP de la red o usen otra red |
| El robot arranca antes o después que el gemelo | Hora del PC desincronizada → sincronícenla |
| El gemelo no se mueve | Broker o *Topic base* / *Robot ID* distintos (§7) |
| `OLED: no aparece en el I2C (scan: [])` | SDA/SCL invertidos, sin alimentación, o dirección distinta: si el scan da `0x3d`, cambien `OLED_I2C_ADDR` |
| La pantalla tiembla al hacer scroll | Potenciómetro sin tierra común |
| Un servo tiembla o el Pico se reinicia al mover el brazo | Servos alimentados del Pico → fuente de 5 V aparte, tierra común |
| Un servo no responde y un motor hace ruido raro | Comparten slice PWM → revisen los pines (§1) |
| `Drive: rueda saturada` | La coreografía pide más rapidez de la que da el carro: se reduce la rapidez y se mantiene la duración (para no desincronizarse), así que recorre menos |
