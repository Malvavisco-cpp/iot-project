# Pruebas de hardware, componente por componente

Scripts para probar **a mano** cada parte del robot desde Thonny, sin el programa completo.
Cada uno es independiente: corre con **F5** una demo corta y deja sus funciones disponibles en
la **Shell**, para llamarlas a mano (`ir("hombro", 20)`, `rueda("izq", 0.7, 2)`...).

## Cómo usarlos

1. Intérprete en **MicroPython (Raspberry Pi Pico)**. Detengan el programa del robot si está corriendo (comparten pines).
2. Editen **[`pines.py`](pines.py)** para que coincida con su montaje. Todas las pruebas leen de ahí.
3. Suban al Pico (**Ver > Archivos**, clic derecho → "Subir a /"): `pines.py`, el script que van a usar y, según el caso, `sh1106.py` / `ssd1306.py` (OLED) y la carpeta `umqtt` (MQTT). **Suban los archivos; no copien y peguen código** (se dañan los `__init__`).
4. Abran el script en Thonny y pulsen **F5**. Después llamen a sus funciones en la Shell.

> Un script con `import pines` necesita `pines.py` en el Pico. `prueba_pot.py` y `prueba_todo.py` importan además a otras pruebas (`prueba_oled`, `prueba_wifi`...): suban también esas.

## Qué prueba cada uno

| Script | Componente | Funciones en la Shell |
|---|---|---|
| [`prueba_i2c.py`](prueba_i2c.py) | Bus I²C | `escanear()`, `todos_los_pares()` |
| [`prueba_oled.py`](prueba_oled.py) | Pantalla OLED (SH1106 / SSD1306) | `texto()`, `renglon()`, `limpiar()`, `llenar()`, `contraste()`, `invertir()`, `rotar()` |
| [`prueba_servos.py`](prueba_servos.py) | Servos del brazo (hombro y codo) | `ir()`, `centrar()`, `barrer()`, `pulso()`, `manual()`, `liberar()` |
| [`prueba_motores.py`](prueba_motores.py) | Motores (L298N mini) | `rueda()`, `adelante()`, `atras()`, `girar_izq()`, `girar_der()`, `parar()` |
| [`prueba_pot.py`](prueba_pot.py) | Potenciómetro (ADC) | `leer()`, `seguir()`, `en_oled()` |
| [`prueba_pines.py`](prueba_pines.py) | Cableado pin por pin | `nivel()`, `contacto_3v3()`, `contacto_gnd()`, `adc()`, `adc_todos()`, `salida()`, `pwm()`, `led()` |
| [`prueba_wifi.py`](prueba_wifi.py) | WiFi del Pico W | `redes()`, `conectar()`, `estado()` |
| [`prueba_mqtt.py`](prueba_mqtt.py) | Broker MQTT | `conectar()`, `publicar()`, `escuchar()` |
| [`prueba_ntp.py`](prueba_ntp.py) | Hora por NTP | `sincronizar()` |
| [`prueba_todo.py`](prueba_todo.py) | Resumen OK / FALLA sin mover nada | `main()` |

## Antes de mover algo

* **Motores:** ruedas **en el aire**. Parten con `MOTOR_DUTY_MIN` (en `pines.py`) para que arranquen; si una gira al revés, cambien su `invertido`.
* **Servos:** fuente de **5 V aparte** (no el 5 V del Pico) y **tierra común** con el Pico. Mueven despacio y `liberar()` los suelta.
* **Frecuencia I²C:** la OLED va a 400 kHz. A 100 kHz, un `show()` completo se pasa del tiempo límite por defecto y da `ETIMEDOUT`.

## Si algo no responde

| Síntoma | Qué revisar |
|---|---|
| `escanear()` sale vacío | Cambien los jumpers; `todos_los_pares()` dice si la pantalla quedó en otros pines |
| Pantalla se enciende pero queda negra o con basura | Cambien `OLED_CONTROLADOR` en `pines.py` |
| El potenciómetro siempre da el mismo valor | `contacto_3v3(g)` y `contacto_gnd(g)` en ese pin: `1` y `0` si el cable hace contacto |
| `WiFi: status = -2` / `-3` | Red no encontrada (¿5 GHz?, `redes()`) / contraseña mal en `.env` |
| `NTP falló` | La red bloquea UDP 123: usen otro servidor o red |
| `No module named 'prueba_oled'`, `'pines'`... | Falta subir ese archivo al Pico |
