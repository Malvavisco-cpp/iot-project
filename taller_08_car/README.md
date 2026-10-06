# Taller 08 — CAR: robot diferencial controlado por MQTT desde Flet

Carpeta autocontenida (como `taller_05_alarma/` y `taller_07_servo/`): se ejecuta
**desde dentro de `taller_08_car/`**, y trae **todo** lo que necesita el Pico,
incluidos los archivos base de PicoROS. No se asume nada cargado en la placa.

```text
  Flet ──► car/cmd {v, w, t} ──► Car ──(cinemática inversa)──► v_l, v_r ──► Motor izq / der ──► puente H
  Flet ──► car/stop {}       ──► Car.stop()
  Flet ◄── car/state         ◄── Car (moviéndose / detenido)
```

## Qué pide el taller y dónde está

| Pedido | Dónde | Prueba |
|---|---|---|
| Cinemática diferencial (directa e inversa) | `common/kinematics.py` | `tests/common/test_kinematics.py` |
| Clase **CAR**: se suscribe a los tópicos y avanza con `v` y `w` durante `t` | `common/car.py` | `tests/common/test_car.py` |
| Motores (L298N mini, L298N grande / TB6612) | `common/motor.py` | `tests/common/test_motor.py` |
| Flet: línea recta 1 m, 1/4 de círculo R = 1 m a derecha e izquierda | `flet_ui/main.py` + `common/maneuvers.py` | `tests/common/test_maneuvers.py` |
| Tópicos | `common/messages.py` | `tests/common/test_messages.py` |

`Car`, `Motor` y la cinemática no importan `machine`: reciben los pines y el
`node` ya creados. Por eso corren igual en el Pico, en el simulador del PC y en
las pruebas (como `Servo` en el taller 07 y `AlarmController` en el 05).

## La matemática de cada botón

Con `d` = distancia del centro a cada rueda (mitad de la distancia entre ruedas):

* Cinemática inversa: `v_l = v − w·d`, `v_r = v + w·d`
* Cinemática directa: `v = (v_r + v_l)/2`, `w = (v_r − v_l)/(2d)`
* `w > 0` gira a la **izquierda** (antihorario); `w < 0` a la **derecha**.

| Botón (con v = 0.2 m/s) | v | w | t | Termina en (sale de (0,0) mirando a +x) |
|---|---|---|---|---|
| Línea recta 1 m | 0.2 | 0 | 1 / 0.2 = **5 s** | (1, 0), mirando a +x |
| 1/4 círculo R = 1 m izquierda | 0.2 | v/R = **+0.2 rad/s** | (π/2)/0.2 = **7.85 s** | (1, 1), mirando a +y |
| 1/4 círculo R = 1 m derecha | 0.2 | **−0.2 rad/s** | 7.85 s | (1, −1), mirando a −y |

El arco recorrido es `v·t = (π/2)·R ≈ 1.57 m`. Cambiar `v` solo cambia el
tiempo, no la trayectoria. Si una rueda no alcanza la rapidez pedida, `Car`
baja **las dos** en la misma proporción (mismo radio) y alarga `t` para
recorrer lo mismo.

## Estructura

```text
taller_08_car/
├── common/                  # corre igual en el Pico y en el PC  -> se sube al Pico
│   ├── config.py            #   broker, PREFIX, d y calibración de las ruedas
│   ├── kinematics.py        #   cinemática directa / inversa e integración de la pose
│   ├── maneuvers.py         #   recta y arcos como comandos (v, w, t)
│   ├── messages.py          #   tópicos + validación
│   ├── motor.py             #   MiniMotor (L298N mini) y Motor (L298N grande / TB6612)
│   └── car.py               #   Car: la clase del taller
├── micropython/             # -> se sube a la RAÍZ del Pico
│   ├── main.py              #   punto de entrada (arranca solo)
│   ├── config.py            #   pines del puente H y WiFi
│   ├── car_task.py          #   llama a car.tick() cada 20 ms
│   ├── mqtt.py, wifi.py, safe_scheduler.py      # infraestructura (de los talleres 05/07)
│   ├── node.py, task.py, scheduler.py,
│   │   util.py, ring_buffer.py, umqtt/simple.py # base de PicoROS (minimum_PicoROS.zip)
│   └── .env.example         #   formato del archivo con la contraseña del WiFi
├── flet_ui/                 # la app del PC
│   ├── main.py
│   └── mqtt_client.py
├── tools/car_simulator.py   # carro virtual para probar sin hardware
└── tests/
```

---

## Paso a paso (desde cero)

### 0. Instalar MicroPython en el Pico (solo la primera vez)

1. Instalen **Thonny** (thonny.org).
2. Desconecten el Pico, mantengan presionado el botón **BOOTSEL**, conecten el cable USB y suelten el botón: aparece como una memoria USB (`RPI-RP2` o `RP2350`).
3. En Thonny: **Herramientas > Opciones > Intérprete** (*Tools > Options > Interpreter*) → abajo, **"Instalar o actualizar MicroPython"**. Elijan el dispositivo, la familia **RP2** y la variante de su placa (**Raspberry Pi Pico 2 W** o **Pico W**; tiene que ser la "W", con WiFi) → **Instalar**.
4. En esa misma ventana, en el intérprete elijan **"MicroPython (Raspberry Pi Pico)"** y el puerto que aparece → **OK**. En la Shell debe salir algo como `MicroPython v1.xx ... Raspberry Pi Pico 2 W`.

> ⚠️ **"No module named 'machine'" / "machine no está instalado"**: Thonny está corriendo el archivo con el **Python de su PC**, no en el Pico. Abajo a la derecha de Thonny debe decir **"MicroPython (Raspberry Pi Pico)"**, no "Local Python 3". Haga clic ahí y cámbielo. Y **no** se le da *Run* a `main.py` abierto desde el PC: se sube al Pico y se reinicia la placa (paso 4). Si el intérprete sí es MicroPython y aun así falla, la placa tiene **CircuitPython** instalado: repitan el paso 0.

### 1. Conexiones

Ajusten los pines en [`micropython/config.py`](micropython/config.py) para que coincidan con el diagrama de conexiones de la clase (`CAR_HW.png`). Los números son **GPIO** (`GP2` = `2`), no el número de pata física.

**L298N mini** (placa roja pequeña, `MOTOR_DRIVER = "mini"`, el valor por defecto). No tiene ENA/ENB: la velocidad va con PWM directo en los IN.

| Pico | L298N mini | |
|---|---|---|
| `GP2` | IN1 | motor izquierdo (PWM = adelante) |
| `GP3` | IN2 | motor izquierdo (PWM = atrás) |
| `GP6` | IN3 | motor derecho (PWM = adelante) |
| `GP7` | IN4 | motor derecho (PWM = atrás) |
| `GND` | `-` (GND) | **tierra común** (obligatoria) |
| — | MOTOR-A, MOTOR-B | motores izquierdo y derecho |
| — | `+` / `-` | batería de los motores (2–10 V) |

**L298N grande o TB6612** (`MOTOR_DRIVER = "l298n"`): además de IN1..IN4 usan `LEFT_PWM_GPIO` (ENA/PWMA, `GP4`) y `RIGHT_PWM_GPIO` (ENB/PWMB, `GP8`). En el L298N grande quiten los jumpers de ENA y ENB; en el TB6612 el pin STBY va a 3V3 (o a `STBY_GPIO`).

> ⚠️ Los motores **no** se alimentan del Pico: van con su propia batería al puente H, y la tierra se comparte con el Pico.
>
> Con el mini, los dos pines de un mismo motor no pueden compartir canal PWM del Pico. Por ejemplo, `GP0` y `GP16` comparten canal. Usen dos pines seguidos, como `GP2`/`GP3` o `GP6`/`GP7`, y no hay problema.

### 2. Configurar antes de subir

Editen **en su copia local** (son los mismos archivos que se suben en el paso 3; si cambian algo después, hay que volver a subir ese archivo):

1. [`common/config.py`](common/config.py)
   - `PREFIX`: cambien `robot0` por el número de su grupo. **El Pico y Flet deben usar el mismo.**
   - `WHEEL_HALF_TRACK_M` (`d`): midan con una regla la distancia entre los **centros** de las dos ruedas y divídanla por 2 (en metros).
   - `MAX_WHEEL_SPEED_M_S`: déjenlo así por ahora; se calibra en el paso 6.
2. [`micropython/config.py`](micropython/config.py)
   - `WIFI_SSID`: el nombre de su red (2.4 GHz; el Pico no se conecta a 5 GHz).
   - Los pines, si su montaje es distinto a la tabla del paso 1.

### 3. Subir el código al Pico con Thonny

Con el Pico conectado y el intérprete en **MicroPython (Raspberry Pi Pico)**: **Ver > Archivos** (*View > Files*). Arriba queda **"Este computador"** y abajo **"Raspberry Pi Pico"**.

1. En "Este computador", naveguen hasta `taller_08_car/`.
2. Clic derecho en la carpeta **`common`** → **"Subir a /"** (*Upload to /*). Queda como carpeta `common/` en el Pico.
3. Entren a `taller_08_car/micropython/`, seleccionen **todo** lo que hay adentro (todos los `.py` **y la carpeta `umqtt`**) → clic derecho → **"Subir a /"**. Quedan sueltos en la raíz del Pico (no dentro de una carpeta `micropython`).
4. Crear la contraseña del WiFi: **Archivo > Nuevo**, escriban **solo** la contraseña (una línea), **Archivo > Guardar como...** → **Raspberry Pi Pico** → nombre **`.env`**.

Al final, el Pico debe tener exactamente esto:

```text
/
├── .env
├── main.py  config.py  car_task.py
├── mqtt.py  wifi.py  safe_scheduler.py
├── node.py  task.py  scheduler.py  util.py  ring_buffer.py
├── umqtt/simple.py
└── common/  __init__.py  config.py  kinematics.py  maneuvers.py  messages.py  motor.py  car.py
```

### 4. Arrancar y verificar

Reinicien el Pico: botón rojo **Detener/Reiniciar** de Thonny, o `Ctrl+D` en la Shell. `main.py` arranca solo. En la Shell deben ver, entre otras líneas:

```text
Carro listo | nodo: car_node_<id>
WiFi conectado, IP: 192.168.x.x
MQTT conectado a broker.hivemq.com
```

Desde ahí el Pico ya no necesita Thonny: puede alimentarse con batería y arranca solo.

### 5. Correr la app Flet en el PC

Dentro de `taller_08_car/`:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m flet_ui.main
```

Deben ver **"Broker: conectado"** y, cuando el Pico esté en línea, **"Carro: detenido"**. Botones:

* **Línea recta 1 m**, **1/4 círculo a la derecha**, **1/4 círculo a la izquierda** (con la rapidez `v` del campo de arriba).
* **Comando manual**: cualquier `v`, `w`, `t` (para calibrar).
* **DETENER**: frena de inmediato.

La tarjeta "Último comando" muestra `v`, `w`, `t` y lo que le toca a cada rueda (`v_l`, `v_r`). Al enviar, la Shell de Thonny imprime `Car: v=... w=... t=... -> v_l=... v_r=...`.

### 6. Calibrar (con las ruedas en el aire primero)

1. **Sentido de giro.** Comando manual `v=0.1, w=0, t=2`: las dos ruedas deben girar hacia adelante. Si una gira al revés, pongan `LEFT_INVERTED` o `RIGHT_INVERTED = True` en `micropython/config.py`.
2. **Izquierda/derecha.** Comando manual `v=0, w=1, t=2` (giro a la izquierda sobre su centro): la rueda **derecha** va hacia adelante y la izquierda hacia atrás. Si es al contrario, intercambien los pines `LEFT_*` con los `RIGHT_*`.
3. **Rapidez máxima** (en el piso). Botón **Línea recta 1 m** y midan cuánto avanzó de verdad (`D`, en metros). Pongan `MAX_WHEEL_SPEED_M_S = valor_actual × D`. Ej.: avanzó 0.8 m con 0.5 → `0.4`.
4. **d (opcional, ajuste fino).** Comando manual `v=0, w=1, t=6.28` (una vuelta completa). Si giró `A` grados, `WHEEL_HALF_TRACK_M = valor_actual × 360 / A`.

Después de cada cambio de configuración: vuelvan a subir el archivo que cambiaron (`common/config.py` o `config.py`) y reinicien el Pico.

### 7. Probar sin hardware: el simulador

```bash
python -m tools.car_simulator
```

Levanta un carro virtual que usa la **misma** clase `Car`. En otra terminal, `python -m flet_ui.main` y usen los botones: el simulador imprime la pose final (debe dar `x=1.00 y=0.00`, `x=1.00 y=1.00 theta=90°` o `x=1.00 y=-1.00 theta=-90°`). Apaguen el simulador cuando usen el carro real (si no, ambos responden al mismo `PREFIX`).

### 8. Pruebas automatizadas

```bash
python -m pytest -q
```

---

## Contrato MQTT

| Tópico | Sentido | Retenido | Contenido |
|---|---|---|---|
| `car/cmd` | Flet → Pico | no | `{"v": m/s, "w": rad/s, "t": s}` — `t > 0`; un comando nuevo reemplaza al que esté corriendo |
| `car/stop` | Flet → Pico | no | `{}` — frena ya |
| `car/state` | Pico → Flet | sí | `{"moving", "v", "w", "t", "v_l", "v_r"}` — al arrancar y al frenar |

Ningún comando dura más de `MAX_COMMAND_S` (30 s): si se cae la red a mitad de camino, el carro frena solo al cumplirse `t`.

## Si algo no funciona

| Síntoma | Causa probable |
|---|---|
| `No module named 'machine'` | Thonny en "Local Python 3" o placa con CircuitPython → paso 0 |
| `ImportError: no module named 'node'` / `'umqtt'` / `'common'` | Falta subir ese archivo o carpeta → paso 3 y comparen con el árbol |
| `Device is busy or does not respond` | Desconecten y conecten el USB, o botón Detener/Reiniciar |
| `WiFi: reintentando, status = -2` | No encuentra la red: `WIFI_SSID` mal escrito o red de 5 GHz |
| `WiFi: reintentando, status = -3` | Contraseña mal en `.env` |
| Flet dice "Carro: sin datos" | `PREFIX` distinto entre el PC y el Pico, o el Pico sin WiFi |
| Las ruedas no giran pero la Shell imprime `Car: v=...` | `MOTOR_DRIVER` no corresponde a su placa, batería de motores, tierra común, o `STBY` del TB6612 |
| Siempre giran a tope (L298N grande) | Jumpers ENA/ENB puestos |
| Se va hacia un lado en la recta | Un motor más rápido que el otro: es normal en motores baratos; bajen la rapidez o compensen con `w` en el comando manual |
