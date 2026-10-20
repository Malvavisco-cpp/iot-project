# Taller 09 — Brazo MeArm en el Carrobot

Solución de `IoT_ws/09_Taller_Arm.ipynb`: la cinemática del MeArm (ley de cosenos, problema del
tercer punto, cinemática directa e inversa) y el ejercicio final:

> *Implemente en el Carrobot una clase que se suscriba a los tópicos `motion` y ejecute los comandos.*

Esa clase es **`Carrobot`** (`common/carrobot.py`). Se suscribe a `motion/state` y `motion/sequence`
(los de `motionTopics.md`) y mueve el carro y el MeArm **igual que el gemelo virtual**.

Carpeta autocontenida: se ejecuta **desde dentro de `taller_09_arm/`** y trae **todo** lo que
necesita el Pico (base de PicoROS, driver del OLED). Parte del proyecto de coreografía (rama
`coreografia`): reproductor de estados, coreografías con hora `run_at`, reloj NTP, OLED con
Watchdog. Lo nuevo es la cinemática del MeArm y cómo se traducen los ángulos a sus servos.

```text
  Flet ─┬─► motion/state    ─► Carrobot ─► MotionPlayer ─┬─► DiffDrive ─► 2 motores (L298N mini)
        └─► motion/sequence ─►          ─► Choreographer └─► MeArm    ─► servos base / hombro / codo
            (el gemelo virtual recibe exactamente los mismos mensajes)
```

## Qué pide el notebook y dónde está

| Notebook | Dónde | Prueba |
|---|---|---|
| Parte 1: ley de cosenos, problema del tercer punto | `common/mearm.py` (`law_cos`, `solve_third_point`) | `tests/common/test_mearm.py` |
| Parte 2: robot planar 2R | `common/mearm.py` (`inverse`: ley de cosenos + `atan2`) | `test_mearm.py` |
| Parte 3: cinemática directa del MeArm | `mearm.forward` (todos los pivotes `a`..`j`) | comparada contra el código del notebook |
| Cinemática inversa del MeArm | `mearm.inverse` (a la punta de la pinza o a la muñeca) | ida y vuelta con `forward` |
| Ejercicio: clase suscrita a `motion` | `common/carrobot.py` (`Carrobot`) + `common/arm.py` (`MeArm`) | `test_robot_node.py`, `test_hardware_logic.py` |

`test_mearm.py` compara las posiciones de los pivotes contra valores sacados corriendo el código
original del notebook (`solve_third_point` + `update11`).

## Lo que dice la geometría del MeArm (y por qué importa)

El MeArm es un mecanismo de **dos paralelogramos** (`a-e-f-d` y `d-g-h-i`). Verificado con el
código del notebook:

1. **El servo del codo (q2) fija el ángulo ABSOLUTO del antebrazo:** `antebrazo = q2 + 180°`, sin
   importar el hombro.
2. **La pinza siempre queda a 15°** respecto a la horizontal (`beta1 + beta2 − 180`). Por eso la
   cinemática inversa solo necesita el punto: la muñeca está a un vector fijo de la punta.
3. **El codo solo dobla hacia abajo.** El ángulo del antebrazo respecto al brazo (`alpha2 − alpha1`)
   tiene que estar entre −180° y 0°. En 0° el paralelogramo se aplana, y con valores positivos
   `solve_third_point` da la otra solución (el notebook lo muestra con `q1 = 45, q2 = −120`).

El gemelo (`RoDifArm.js`) usa ángulos absolutos: `alpha1` es el brazo y `alpha2` el antebrazo,
los dos respecto a la horizontal. Entonces, en el MeArm:

| Gemelo | Servo del MeArm |
|---|---|
| `alpha0` | base |
| `alpha1` | hombro: `q1 = alpha1` |
| `alpha2` | codo: `q2 = alpha2 − 180°` (con el servo centrado en `q2 = −180°`, recibe `alpha2` directo) |

Esto **corrige** al proyecto de coreografía, que suponía un brazo en serie (codo = `alpha2 − alpha1`).

Si un estado pide un codo imposible (por ejemplo el último estado del ejemplo de `motionTopics.md`,
`alpha1 = 0, alpha2 = 90`), el servo del codo se detiene en el límite (`MEARM_MIN/MAX_REL_DEG`) y
la Shell lo avisa. El robot guarda el ángulo pedido, como el gemelo, para que la interpolación
siga sincronizada.

## Cómo interpreta el robot los mensajes (igual que el gemelo)

* `v_dm/s` en dm/s, `w_deg/s` y ángulos en grados; `w > 0` gira a la izquierda.
* Falta `v` o `w` → 0; falta `duration_s` → 1 s; **falta un ángulo → el brazo se queda donde está**.
* El brazo va **en línea recta durante `duration_s`** hasta los ángulos pedidos (esa es "la demora").
* Un `motion/state` reemplaza lo que se esté ejecutando; al acabar una secuencia el carro frena.
* Se aceptan `alpha0_deg` y `alfa0_deg` (cada gemelo usa una); la app manda las dos.
* Las secuencias arrancan a la hora `run_at` (UTC) con el reloj NTP del Pico.

## Estructura

```text
taller_09_arm/
├── common/                 # corre igual en el Pico y en el PC  -> carpeta common/ del Pico
│   ├── mearm.py            #   cinemática del MeArm (Partes 1-3 del notebook)
│   ├── arm.py              #   MeArm: ángulos del gemelo -> servos, con límites del mecanismo
│   ├── carrobot.py         #   Carrobot: LA CLASE DEL EJERCICIO (tópicos motion)
│   ├── player.py           #   ejecuta estados (v, w, brazo interpolado)
│   ├── choreographer.py    #   secuencias: create / delete / schedule / execute_now
│   ├── motion.py           #   tópicos + cómo se lee un estado
│   ├── config.py           #   broker, PREFIX, carro, servos y límites del MeArm
│   ├── drive.py, motor.py, kinematics.py, maneuvers.py, servo.py
│   └── oled_view.py, timeutil.py, wallclock.py, ticks.py
├── micropython/            # -> RAÍZ del Pico (main.py, config.py, tasks.py, ... + PicoROS)
├── flet_ui/                # app del PC (bloque 5: MeArm con cinemática inversa)
├── tools/
│   ├── robot_simulator.py  #   robot virtual con las mismas clases
│   └── mearm_svg.py        #   dibuja el MeArm en SVG (como las figuras del notebook)
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
| `GP10` | señal del servo de la **base** del MeArm (alpha0) | |
| `GP11` | señal del servo del **hombro** (alpha1 = q1) | |
| `GP12` | señal del servo del **codo** (q2, mueve el antebrazo) | |
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

1. En "Este computador", vayan a `taller_09_arm/`.
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
└── common/  __init__.py arm.py carrobot.py choreographer.py config.py drive.py kinematics.py
             maneuvers.py mearm.py motion.py motor.py oled_view.py player.py servo.py ticks.py
             timeutil.py wallclock.py
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
Robot listo | nodo: mearm_node_<id> | prefijo: UDFJC/iot_ws/robot4/
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
| 5. Brazo MeArm | **Llevar la pinza a (x, y)**: cinemática inversa en el PC y se manda como `motion/state` normal, así el gemelo también se mueve. **Revisar ángulos del bloque 1**: dice dónde queda la pinza y si el MeArm puede hacer esa pose | taller 09 |

"Ejecutar ya" y "Programar" mandan primero `create` y luego `schedule`, así nadie se queda sin la secuencia. La app muestra dónde termina la coreografía (pose final estimada) y la duración total.

### 6. Armar y calibrar el MeArm

**Al armarlo** (servos ya conectados y el robot encendido, para que estén centrados en 1.5 ms):

1. Bloque 1, **Solo brazo** con `alpha0 = 0, alpha1 = 90, alpha2 = 0` y 1 s: hombro y codo quedan **centrados**.
2. Pongan los cuernos de los servos para que, en esa posición, el **brazo quede vertical** y el
   **antebrazo horizontal** hacia adelante (eso dicen `MEARM_SHOULDER_CENTER_DEG = 90` y
   `MEARM_CRANK_CENTER_DEG = -180`). La base, mirando al frente.

**Después**, ajuste fino en `common/config.py`:

3. `alpha1 = 60`: el brazo debe inclinarse **hacia adelante** como en el gemelo. Si va hacia atrás,
   `inverted: True` en `alpha1` de `ARM_JOINTS`. En el MeArm los servos del hombro y del codo van
   en espejo, así que es normal que uno de los dos quede invertido.
4. `alpha2 = -30`: el antebrazo debe bajar. Si sube, `inverted: True` en `alpha2`.
5. Si algo queda unos grados corrido, súmenlo en `offset_deg`.
6. Si el brazo choca antes de llegar a un límite, achiquen `MEARM_MIN_REL_DEG` / `MEARM_MAX_REL_DEG`.
7. Vuelvan a subir `common/config.py` y reinicien después de cada cambio.

**Comprobar la cinemática:** en el bloque 5, **Llevar la pinza a (x, y)** con `x = 1.2, y = 0.8` dm
y midan con una regla desde el eje del hombro: la punta debe quedar a 12 cm hacia adelante y 8 cm
hacia arriba. Si las barras de su MeArm no miden como las del notebook (`B` = `J` = 0.8 dm,
`M` = 0.25 dm), ajusten `LINKS` en `common/mearm.py`.

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
python -m tools.mearm_svg --alpha1 67.5 --alpha2 -67.5     # dibuja esa pose en mearm.svg
python -m tools.mearm_svg --x 1.2 --y 0.8                  # pinza a ese punto (cinemática inversa)
```

`mearm_svg` dibuja todos los pivotes como las figuras del notebook, e indica si la pose está fuera
del rango del MeArm.

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
| `MeArm: el codo no llega a ...` | Ese estado pide un codo imposible para el MeArm; se queda en el límite. Es normal con el ejemplo de `motionTopics.md` |
| La pinza no llega al punto del bloque 5 | Cuernos de los servos mal puestos al armar (§6) o barras de otra medida (`LINKS`) |
| `... está fuera del alcance del brazo` | El punto está más lejos de lo que miden brazo + antebrazo (1.6 dm a la muñeca) |
| `Drive: rueda saturada` | La coreografía pide más rapidez de la que da el carro: se reduce la rapidez y se mantiene la duración (para no desincronizarse), así que recorre menos |
