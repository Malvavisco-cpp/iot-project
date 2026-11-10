# Taller 10 — Pantalla OLED I²C controlada por MQTT desde Flet

Solución de `IoT_ws/10_Taller_I2C_OLED.md`. El ejercicio final dice:

> *Crea una clase llamada `OLED` que se suscriba al tópico `oled/text` y permita escribir texto en la pantalla OLED utilizando los argumentos correspondientes.*

Carpeta autocontenida (como `taller_05_alarma/`, `taller_07_servo/` y `taller_08_car/`): se ejecuta
**desde dentro de `taller_10_oled/`**, y trae **todo** lo que necesita el Pico, incluidos los
archivos base de PicoROS y el driver `ssd1306.py`. No se asume nada cargado en la placa.

```text
  Flet ──► oled/text {text, x, y, color, clear} ──► OLED ──► ssd1306 ──(I²C: SDA/SCL)──► pantalla
```

## Qué pide el taller y dónde está

| Pedido | Dónde | Prueba |
|---|---|---|
| Conectar la OLED por I²C e identificar su dirección | `micropython/main.py` (`make_display`: `i2c.scan()`) | Shell de Thonny |
| Escribir texto con el driver SSD1306 | `micropython/ssd1306.py` (de `micropython-lib`) | — |
| Clase **OLED**: se suscribe a `oled/text` y escribe con sus argumentos | `common/oled.py` | `tests/common/test_oled.py` |
| Argumentos del mensaje (`text`, `x`, `y`, `color`, `clear`) | `common/messages.py` | `tests/common/test_messages.py` |
| Actualizar la pantalla sin bloquear el programa | `OLED` solo dibuja cuando llega un mensaje; el Scheduler sigue atendiendo WiFi y MQTT | — |

`OLED` no importa `machine`: recibe el `node` ya creado y un `display` con la interfaz de
`ssd1306.SSD1306_I2C` (`fill`, `text`, `show`). Por eso corre igual en el Pico, en el simulador del
PC y en las pruebas (como `Car` en el taller 08).

## Los argumentos de `oled/text`

Solo `text` es obligatorio. El mensaje es JSON:

| Campo | Tipo | Por defecto | Qué hace |
|---|---|---|---|
| `text` | cadena | — | Lo que se escribe. Puede ir vacío **solo** si `clear` es `true`. |
| `x` | entero, 0–127 | `0` | Columna (en píxeles) de la esquina superior izquierda del texto. |
| `y` | entero, 0–63 | `0` | Renglón (en píxeles) de esa esquina. |
| `color` | `0` o `1` | `1` | `1` enciende los píxeles; `0` los apaga (borra con la forma del texto). |
| `clear` | `true` / `false` | `false` | Apaga toda la pantalla **antes** de escribir. |

Ejemplos (el `PREFIX` se antepone: `UDFJC/iot_ws/robot4/oled/text`):

```json
{"text": "Hola OLED"}
{"text": "Temp: 24 C", "x": 0, "y": 16}
{"text": "", "clear": true}
```

La fuente de `framebuf` mide **8 × 8 píxeles**, así que la pantalla de 128 × 64 son
**16 columnas × 8 renglones** de texto: `x` múltiplo de 8 y `y` múltiplo de 8 alinean el texto con la
cuadrícula. Lo que no cabe en el renglón se corta. Escribir encima de texto viejo sin `clear` mezcla
los píxeles: para reemplazar un renglón, borren primero (`clear: true`) o escriban el texto viejo con
`color: 0`.

Mensajes mal formados (tipos incorrectos, `x` fuera de rango, `color` distinto de 0/1...) se ignoran y
la Shell dice por qué: el broker es público y cualquiera puede publicar.

## Estructura

```text
taller_10_oled/
├── common/                  # corre igual en el Pico y en el PC  -> se sube al Pico
│   ├── config.py            #   broker, PREFIX, tamaño de la pantalla
│   ├── messages.py          #   tópico + validación de oled/text
│   └── oled.py              #   OLED: la clase del taller
├── micropython/             # -> se sube a la RAÍZ del Pico
│   ├── main.py              #   punto de entrada (arranca solo)
│   ├── config.py            #   pines I²C, dirección de la OLED y WiFi
│   ├── ssd1306.py           #   driver de la pantalla SSD1306 (micropython-lib)
│   ├── sh1106.py            #   driver para pantallas SH1106 (1.3"); se elige con OLED_CONTROLLER
│   ├── oled_test.py         #   prueba de conexión: se corre con F5 desde Thonny
│   ├── mqtt.py, wifi.py, safe_scheduler.py      # infraestructura (de los talleres 05/07/08)
│   ├── node.py, task.py, scheduler.py,
│   │   util.py, ring_buffer.py, umqtt/simple.py # base de PicoROS (minimum_PicoROS.zip)
│   └── .env.example         #   formato del archivo con la contraseña del WiFi
├── flet_ui/                 # la app del PC
│   ├── main.py
│   └── mqtt_client.py
├── tools/oled_simulator.py  # OLED virtual para probar sin hardware
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

Pines en [`micropython/config.py`](micropython/config.py). Son números **GPIO** (`GP4` = `4`), no el número de pata.

| Pico | OLED | |
|---|---|---|
| `3V3(OUT)` | `VCC` | alimentación a 3,3 V |
| `GND` | `GND` | |
| `GP4` | `SDA` | datos I²C (bus I²C0) |
| `GP5` | `SCL` | reloj I²C (bus I²C0) |

> ⚠️ Las resistencias *pull-up* de SDA y SCL las trae el módulo OLED, **no** la Pico; casi todos los módulos las incluyen, pero si el escaneo sale vacío con todo bien cableado, agreguen 4.7 kΩ de SDA a 3V3 y de SCL a 3V3. Verifiquen las etiquetas de su módulo: algunos tienen el orden `GND VCC SCL SDA` y otros `VCC GND SCL SDA`. **No** conecten señales de 5 V a los GPIO de la Pico.
>
> Si usan otros pines, tienen que ser del mismo bus: `GP4/GP5` son I²C0 (`OLED_I2C_ID = 0`); `GP26/GP27` (como en el ejemplo del enunciado) son I²C1 (`OLED_I2C_ID = 1`).

### 2. Configurar antes de subir

Editen **en su copia local** (son los mismos archivos que se suben en el paso 3; si cambian algo después, hay que volver a subir ese archivo):

1. [`common/config.py`](common/config.py)
   - `PREFIX`: cambien `robot4` por el número de su grupo. **El Pico y Flet deben usar el mismo.**
2. [`micropython/config.py`](micropython/config.py)
   - `WIFI_SSID`: el nombre de su red (2.4 GHz; el Pico no se conecta a 5 GHz).
   - `OLED_I2C_ADDR`: `0x3C` casi siempre; si el scan del paso 4 da `0x3d`, cámbienlo.

### 3. Subir el código al Pico con Thonny

> ⚠️ **No copien y peguen código desde el chat o una página web.** En el taller 08 eso convirtió `__init__` en `_init_` y la clase dejó de funcionar sin dar un error claro. **Suban los archivos** desde la carpeta del repo.

Con el Pico conectado y el intérprete en **MicroPython (Raspberry Pi Pico)**: **Ver > Archivos** (*View > Files*). Arriba queda **"Este computador"** y abajo **"Raspberry Pi Pico"**.

1. En "Este computador", naveguen hasta `taller_10_oled/`.
2. Clic derecho en la carpeta **`common`** → **"Subir a /"** (*Upload to /*). Queda como carpeta `common/` en el Pico.
3. Entren a `taller_10_oled/micropython/`, seleccionen **todo** lo que hay adentro (todos los `.py` **y la carpeta `umqtt`**) → clic derecho → **"Subir a /"**. Quedan sueltos en la raíz del Pico (no dentro de una carpeta `micropython`).
4. Crear la contraseña del WiFi: **Archivo > Nuevo**, escriban **solo** la contraseña (una línea), **Archivo > Guardar como...** → **Raspberry Pi Pico** → nombre **`.env`**.

Al final, el Pico debe tener exactamente esto:

```text
/
├── .env
├── main.py  config.py  ssd1306.py  (oled_test.py es solo para la prueba)
├── mqtt.py  wifi.py  safe_scheduler.py
├── node.py  task.py  scheduler.py  util.py  ring_buffer.py
├── umqtt/simple.py
└── common/  __init__.py  config.py  messages.py  oled.py
```

### 4. Arrancar y verificar

Reinicien el Pico: botón rojo **Detener/Reiniciar** de Thonny, o `Ctrl+D` en la Shell. `main.py` arranca solo. En la Shell deben ver, entre otras líneas:

```text
I2C scan: ['0x3c']
OLED lista | nodo: oled_node_<id> | prefijo: UDFJC/iot_ws/robot4/
WiFi conectado, IP: 192.168.x.x
MQTT conectado a broker.hivemq.com
```

La pantalla muestra primero **OLED lista / conectando...** y, al conectarse al broker, **MQTT conectado**.

El `I2C scan` es la comprobación del taller: la lista tiene que traer la dirección de su pantalla. Si sale `[]`, el programa se detiene con `OLED: no aparece en 0x3c` (ver "Si algo no funciona").

Desde ahí el Pico ya no necesita Thonny: puede alimentarse con batería y arranca solo.

### Probar solo la conexión de la OLED (opcional, antes del paso 3)

Para saber si la pantalla está bien conectada sin subir todo el taller: suban únicamente `micropython/ssd1306.py` y `micropython/oled_test.py` al Pico (**Ver > Archivos**, clic derecho → **"Subir a /"**), abran `oled_test.py` en Thonny y pulsen **F5** (con el intérprete en *MicroPython (Raspberry Pi Pico)*). No usa WiFi ni MQTT:

1. Escanea el I²C en los pines de la configuración e imprime las direcciones que responden (`Scan: ['0x3c']`).
2. Si no responde nada, prueba todos los pares SDA/SCL válidos de la Pico y dice en cuál encontró la pantalla.
3. Si la encuentra, dibuja texto, un marco, cambia el contraste, invierte la pantalla y mueve un cuadrito. Termina con `OK: la OLED responde y dibuja`.

Si la dirección es `0x3d`, pongan `ADDR = 0x3D` al inicio del archivo.

### 5. Correr la app Flet en el PC

Dentro de `taller_10_oled/`:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m flet_ui.main
```

Debe verse **"Broker: conectado"**. Escriban un texto, su posición `x`, `y` y el color, y pulsen **Enviar**:

* **Borrar la pantalla antes de escribir** marca `clear: true` en el mensaje.
* **Borrar pantalla** manda `{"text": "", "clear": true}`.

La tarjeta "Último mensaje" muestra el JSON enviado. En la Shell del Pico no sale nada si todo va bien; si el mensaje es inválido sale `OLED: oled/text ignorado: ...`.

### 6. Probar sin hardware: el simulador

```bash
python -m tools.oled_simulator
```

Levanta una OLED virtual que usa la **misma** clase `OLED`: en vez de píxeles, imprime la pantalla como una cuadrícula de 16 × 8 caracteres cada vez que llega un mensaje. En otra terminal, `python -m flet_ui.main` y envíen texto. Apaguen el simulador cuando usen la pantalla real (si no, ambos responden al mismo `PREFIX`).

### 7. Pruebas automatizadas

```bash
python -m pytest -q
```

---

## Contrato MQTT

| Tópico | Sentido | Retenido | Contenido |
|---|---|---|---|
| `oled/text` | Flet → Pico | no | `{"text": str, "x": 0–127, "y": 0–63, "color": 0\|1, "clear": bool}` — solo `text` es obligatorio |

La OLED no publica nada: la pantalla es de salida.

## Si algo no funciona

| Síntoma | Causa probable |
|---|---|
| `No module named 'machine'` | Thonny en "Local Python 3" o placa con CircuitPython → paso 0 |
| `ImportError: no module named 'node'` / `'umqtt'` / `'common'` / `'ssd1306'` | Falta subir ese archivo o carpeta → paso 3 y comparen con el árbol |
| `OLED: no aparece en 0x3c (scan: [])` | SDA/SCL invertidos, sin VCC/GND, o pines de otro bus I²C (`OLED_I2C_ID`). **Cambien los jumpers**: un cable dupont malo (que no conduce) dio exactamente este síntoma en las pruebas. `oled_test.py` dice si una línea está pegada a 0 V |
| `OLED: no aparece en 0x3c (scan: ['0x3d'])` | Su módulo usa `0x3D`: cambien `OLED_I2C_ADDR` |
| La pantalla se enciende (o parpadea) pero queda en negro o con basura, y el scan sí da `0x3c` | Su módulo es un **SH1106** (típico de 1.3"), no un SSD1306: pongan `OLED_CONTROLLER = "sh1106"` en `micropython/config.py` (y suban `sh1106.py`). Con el `oled_test.py`, cambien `CONTROLLER` al inicio del archivo |
| `OSError: [Errno 5] EIO` al iniciar | Cableado flojo (jumper sin buen contacto) o dirección incorrecta: el módulo se ve en el scan pero no contesta al escribir |
| `WiFi: reintentando, status = -2` | No encuentra la red: `WIFI_SSID` mal escrito o red de 5 GHz |
| `WiFi: reintentando, status = -3` | Contraseña mal en `.env` |
| La pantalla no cambia al enviar desde Flet | `PREFIX` distinto entre el PC y el Pico, o el Pico sin WiFi/MQTT |
| `OLED: oled/text ignorado: ...` | El mensaje no cumple el contrato: la Shell dice qué campo está mal |
| El texto sale mezclado con el anterior | Escribieron encima sin `clear`: marquen `clear` o borren el texto viejo con `color: 0` |
| Se corta el texto | Son 16 caracteres por renglón; partan el texto en varios renglones (`y` = 0, 8, 16...) |
| Pantalla en blanco pero el scan encuentra la dirección | `OLED_WIDTH`/`OLED_HEIGHT` no corresponden a su módulo (128 × 32 en las pantallas pequeñas) |
