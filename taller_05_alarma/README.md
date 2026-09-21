# Taller 05 — Control de acceso y alarma (GPIO + IR + Flet)

Solución del **taller integrador** de `05_Taller_GPIO_IR`: una alarma con Raspberry Pi Pico 2 W, un botón que hace de puerta, un LED, una sirena y un receptor IR, monitoreada desde una interfaz Flet.

La idea central: **toda la lógica corre en el Pico**. Flet solo muestra lo que pasa. Si se apaga el PC, se cierra la ventana o se cae el WiFi, la alarma sigue decidiendo y sonando.

```text
  Botón (puerta) ─┐                                    ┌─► LED  (fijo = activa, parpadea = disparada)
  Receptor IR ────┼─► AlarmController (estado) ────────┼─► Sirena (buzzer)
                  │        │  (todo esto es local, en el Pico)
                  │        └─► Node ─► MQTTTransport ──► broker MQTT ──► Flet (solo lectura)
```

## Requisitos de la pizarra y qué prueba cada uno

| Requisito | Dónde se cumple | Test que lo demuestra |
|---|---|---|
| La clave IR de **4 dígitos** activa y desactiva la alarma | `common/alarm.py` | `test_rule1_correct_password_arms_then_disarms` |
| Clave **equivocada** → se dispara la sirena | `common/alarm.py` | `test_rule2_wrong_password_triggers_siren_when_disarmed` / `..._when_armed` |
| Alarma **activa** + puerta abierta → sirena | `common/alarm.py` | `test_rule3_door_open_while_armed_triggers_siren` |
| Alarma **desactivada** + puerta abierta → **no** suena | `common/alarm.py` | `test_rule4_door_open_while_disarmed_does_not_trigger` |
| Debe funcionar **desconectado del PC** | `main.py` autónomo + lógica en el Pico | `test_alarm_keeps_deciding_when_the_ui_and_network_are_gone`, `test_alarm_still_works_when_publishing_raises` |

## Cómo se comporta (máquina de estados)

Responde la pregunta 16 del informe: *¿cómo organizaría el sistema mediante una máquina de estados?*

```text
                 clave OK                     clave OK
   DESACTIVADA ─────────────► ACTIVADA ─────────────────────► DESACTIVADA
        │                        │
        │ clave mala             │ clave mala  ó  puerta abierta
        ▼                        ▼
                     DISPARADA (sirena)
                          │  clave OK  → DESACTIVADA (y la sirena se silencia)
                          │  clave mala → sigue disparada, suma un intento
```

Decisiones que el enunciado no fija (están en el código y cubiertas por tests):

- **La clave silencia la sirena.** Estando disparada, la clave correcta la apaga y deja la alarma desactivada; para volver a activarla hay que digitarla otra vez.
- **La intrusión se evalúa por nivel** (como en el §22 del taller): si se activa la alarma con la puerta ya abierta, suena de inmediato.
- **Clave a medias**: si se digita parte de la clave y pasan 5 s sin teclas, se descarta sola. La tecla **borrar** (`C`) también la descarta.
- **Códigos IR desconocidos se ignoran**: el ruido y las tramas de "repetición" (cuando se deja la tecla presionada) nunca cuentan como clave equivocada.
- **La clave no sale del Pico.** Ni los dígitos ni los códigos IR se publican; a Flet solo llega *cuántas* teclas van (los puntos ●●○○).

## Estructura

Sigue la organización del taller 03. Es una carpeta autocontenida: se ejecuta **desde dentro de `taller_05_alarma/`**.

```text
taller_05_alarma/
├── common/                    # corre igual en el Pico (MicroPython) y en el PC
│   ├── alarm.py               #   AlarmController: la máquina de estados (lógica pura)
│   ├── alarm_runtime.py       #   une la lógica con puerta, LED, sirena y publicación
│   ├── messages.py            #   contrato de mensajes Pico ↔ Flet + validación
│   └── config.py              #   broker, PREFIX, mapa de teclas por defecto
├── micropython/               # lo que se sube al Pico
│   ├── main.py                #   punto de entrada (arranca solo al energizar)
│   ├── config.py              #   pines, WiFi, clave: lo único que hay que ajustar
│   ├── ir_in.py               #   IRIn del taller 05 (PIO), copia sin cambios de lógica
│   ├── ir_keypad.py           #   entrega cada tecla IR a la alarma
│   ├── alarm_task.py          #   Task que ejecuta el runtime cada 20 ms
│   ├── mqtt.py                #   transporte MQTT que se reconecta solo
│   ├── wifi.py                #   WiFi no bloqueante
│   ├── safe_scheduler.py      #   Scheduler de PicoROS que no muere si una tarea falla
│   ├── ir_calibration.py      #   herramienta para aprender los códigos de SU control
│   └── .env.example           #   formato del archivo con la contraseña del WiFi
├── flet_ui/                   # interfaz (se llama flet_ui para no tapar al paquete flet)
│   ├── main.py                #   la pantalla
│   ├── monitor.py             #   modelo de la UI: sin Flet ni MQTT, por eso es testeable
│   └── mqtt_client.py         #   cliente paho-mqtt
├── tools/pico_simulator.py    # un "Pico virtual" para probar la UI sin hardware
├── tests/                     # common/, micropython/, flet_ui/, integration/
└── requirements.txt
```

## 1. Montaje del hardware

Los pines están en [`micropython/config.py`](micropython/config.py); si el montaje es distinto, se cambian ahí sin tocar código.

| Componente | Pin por defecto | Conexión |
|---|---|---|
| Receptor IR (Vout) | `GP22` | Vcc → 3V3, GND → GND (igual que el taller) |
| Puerta (botón) | `GP16` | Botón entre **3V3** y `GP16`. Pulsado = `1` = **abierta**. Se usa el pull-down interno |
| LED de estado | `GP0` | Con resistencia en serie hacia GND |
| Sirena (buzzer activo) | `GP2` | Opcional. Con `SIREN_GPIO = None` el LED parpadea como sirena |

> ⚠️ La Pico trabaja a **3.3 V**. No conectar señales de 5 V a un GPIO. Un buzzer que consuma más de unos pocos mA debe ir con transistor, no directo al GPIO.

Si el sensor de puerta es un interruptor normalmente cerrado (reed switch), se ajustan `DOOR_OPEN_LEVEL` y `DOOR_PULL` en `config.py`.

## 2. Poner el código en el Pico

**Requisito previo:** el Pico debe tener los archivos de PicoROS de `04_Taller_RPiPico2W/minimum_PicoROS.zip` (los mismos de los talleres 04–06): `task.py`, `scheduler.py`, `node.py`, `util.py`, `ring_buffer.py`, `watchdog_task.py` y la carpeta `umqtt/`.
Este taller **reemplaza** `wifi_manager.py` y `pubsub_mqtt.py` por `wifi.py` y `mqtt.py` (no los use).

**Paso a paso con Thonny** (todo va en la raíz `/` del Pico):

1. **Antes de subir**, editar en el repo: `WIFI_SSID` y `ALARM_PASSWORD` en `micropython/config.py`, y el `PREFIX` de su grupo en `common/config.py` (ver §5).
2. Subir la carpeta `common/` completa (con sus 5 archivos).
3. Subir los archivos de `micropython/`: `main.py`, `config.py`, `ir_in.py`, `ir_keypad.py`, `alarm_task.py`, `mqtt.py`, `wifi.py`, `safe_scheduler.py` (y `ir_calibration.py`).
4. Crear en el Pico el archivo `.env` con **solo** la contraseña del WiFi en una línea (ver `micropython/.env.example`). Está en `.gitignore`: no se sube a git.
5. Calibrar el control IR (§3), pegar el `IR_KEYMAP` en `config.py`, volver a subirlo y reiniciar el Pico. `main.py` arranca solo y ya no necesita Thonny ni el PC.

Alternativa con `mpremote` (`pip install mpremote`), desde `taller_05_alarma/` (comandos sin probar en placa):

```bash
mpremote cp -r common/ :
mpremote cp micropython/main.py micropython/config.py micropython/ir_in.py micropython/ir_keypad.py :
mpremote cp micropython/alarm_task.py micropython/mqtt.py micropython/wifi.py micropython/safe_scheduler.py micropython/ir_calibration.py :
```

Al arrancar debe imprimir `Alarma lista. Estado: disarmed`. Si no hay WiFi o broker, **igual arranca**: verá `WiFi caído; la alarma sigue funcionando sin red` y lo único que falta es el monitoreo.

## 3. Calibrar el control remoto

Cada control IR manda códigos distintos. El mapa por defecto sirve para el control de 21 teclas (NEC) típico de los kits, pero hay que **verificarlo con el suyo**:

1. Abrir `ir_calibration.py` en Thonny y ejecutarlo (no necesita WiFi).
2. Presionar las teclas que pide (0–9 y una tecla para *borrar*), una vez cada una.
3. Copiar el diccionario `IR_KEYMAP = {...}` que imprime al final dentro de `micropython/config.py`.

## 4. Interfaz Flet

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows   (Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m flet_ui.main
```

Muestra: estado de la alarma (con parpadeo rojo al dispararse), puerta abierta/cerrada, progreso de la clave (●●○○), claves incorrectas, bitácora de eventos, telemetría del Pico (RAM, WiFi, temperatura, tiempo activo) y si el Pico está en línea.

Si el Pico se cae, la tarjeta se atenúa y aparece un aviso: *"la alarma sigue funcionando en el dispositivo"*. Es una ventana de **solo lectura**: no puede armar ni desarmar la alarma.

## 5. Grupos: cambien el `PREFIX`

El broker `broker.hivemq.com` es público y compartido. En [`common/config.py`](common/config.py) cambien `robot0` por el número de su grupo (`UDFJC/iot_ws/robot3/`). El **Pico y Flet deben usar el mismo `PREFIX`**; si no, no se ven.

## 6. Probar sin hardware: el simulador

```bash
python -m tools.pico_simulator
```

Levanta un Pico virtual que usa la **misma** lógica de la alarma y publica por MQTT. En otra terminal se abre `python -m flet_ui.main` y se maneja por teclado:

| Comando | Efecto |
|---|---|
| `1234` | digita esas teclas, como en el control IR |
| `o` / `x` | abre / cierra la puerta |
| `c` | tecla *borrar* |
| `s` | muestra el estado |
| `q` | salir |

Escenario para la demo: `1234` (activa) → `o` (dispara por intrusión) → `1234` (silencia) → `9999` (dispara por clave equivocada) → `1234` (silencia).

## 7. Pruebas

```bash
python -m pytest -q                                  # todo, sin red
RUN_MQTT_TESTS=1 python -m pytest -m network -q      # solo la prueba contra el broker real
```

(En PowerShell: `$env:RUN_MQTT_TESTS=1; python -m pytest -m network -q`.)

> Ejecutar **desde dentro de `taller_05_alarma/`**, no desde la raíz del repo (tiene su propio `common/` y `tests/`).

| Carpeta | Qué cubre |
|---|---|
| `tests/common/` | La máquina de estados (incluye cada regla de la pizarra), el runtime con pines falsos (debounce, sirena, LED) y el contrato de mensajes |
| `tests/micropython/` | `mqtt.py` (reconexión, Last Will, sin fugas de socket), `safe_scheduler.py` y `ir_keypad.py` decodificando una trama NEC simulada de la PIO |
| `tests/flet_ui/` | `AlarmMonitor` y la vista contra la API real de Flet 1.0 |
| `tests/integration/` | Pico → JSON → monitor de Flet, y que la clave nunca viaja por la red |

Los tests de GitHub Actions están en `.github/workflows/taller-05-alarma.yml` (raíz del repo).

## Contrato MQTT

Los tópicos van precedidos por el `PREFIX`. El Pico no escucha ningún tópico de la alarma (solo `node/get_second_ts`, la medición de latencia que trae `Node` de PicoROS): nadie puede inyectar teclas ni cambiar el estado por MQTT.

| Tópico | Retenido | Contenido |
|---|---|---|
| `alarm/state` | sí | `{"state","door_open","siren","keys_entered","wrong_attempts","reason","uptime_s"}` — cada cambio y cada 5 s |
| `alarm/event` | no | `{"seq","event","detail","uptime_s"}` — bitácora (`armed`, `disarmed`, `triggered`, `wrong_password`, `door`, `keys_cleared`) |
| `node/online` | sí | `{"online": bool}` — el broker publica `false` (Last Will) si el Pico se cae |
| `watchdog/stats` | no | telemetría del `WatchdogTask` de PicoROS |

`state` ∈ `disarmed` · `armed` · `triggered`. `reason` ∈ `door_open` · `wrong_password` · `null`.

## Por qué no se usan tal cual `GPIOIn`, `GPIOOut` y `PubSubMQTT`

Se reutiliza `IRIn` (la PIO). Las otras piezas se reemplazan por una razón concreta cada una:

- **`GPIOIn`** publica por periodo (5 s por defecto), sin antirrebote: una puerta que se abre debe detectarse en milisegundos. Aquí la puerta se lee cada 20 ms con antirrebote de 50 ms.
- **`GPIOOut`** obedece a cualquiera que publique en su tópico. Las salidas de una alarma las decide solo la máquina de estados local.
- **`Node.subscribe("IRIn/value")`** haría que cada tecla se contara **dos veces**: `Node` también suscribe el tópico en el broker y este devuelve el eco de lo que el propio Pico publicó. Por eso `KeypadIR` entrega las teclas directo a la alarma (además evita publicar la clave en un broker público).
- **`PubSubMQTT`** no se reconecta y una excepción de red mata el `Scheduler`. **`WiFiManager`** bloquea el arranque hasta que haya WiFi. Para una alarma que debe funcionar sola se reemplazan por `mqtt.py`, `wifi.py` y `safe_scheduler.py`.

## Límites conocidos

- **El código MicroPython se probó en el PC con dobles** de `rp2`, `umqtt`, etc., y la lógica de la alarma, la UI y el flujo simulador → broker real → UI están verificados. **Falta la prueba con la placa real**; en particular, confirmar los códigos IR de su control (§3).
- **Broker público, sin TLS ni autenticación.** La clave no viaja, pero el estado de la alarma sí es visible para quien conozca el `PREFIX`, y un tercero podría publicar estados falsos que la UI mostraría. Para producción: broker propio con TLS y usuario.
- **Al reiniciar el Pico la alarma vuelve a `desactivada`** (el estado no se guarda en flash).
- **Sin bloqueo por intentos**: no hay límite de claves equivocadas seguidas.
- Si el broker no responde, cada reintento de conexión puede bloquear el Pico hasta 3 s. Por eso no se intenta conectar mientras alguien digita la clave (si una tecla llega justo durante ese bloqueo, puede perderse).
- La interfaz es solo visual: no reproduce sonido.
