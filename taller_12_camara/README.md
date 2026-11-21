# Taller 12 — Cámara OV7670 (versión corta)

Un Pico con la cámara solo, como pide `IoT_ws/12_Taller_OV7670.md`: captura una imagen
**RGB565** y la publica por MQTT en

```text
<PREFIX>camera/frame/rgb565_160x120      (bytes en bruto, 38 400 bytes; no es JSON)
```

No lleva carro ni brazo. La versión integrada al robot está en `taller_09_arm/` de esta rama.

## 1. Conexiones (tabla del taller; números GPIO, no pata)

| OV7670 | Pico | | OV7670 | Pico |
|---|---|---|---|---|
| PWDN | GP0 | | PCLK | GP11 |
| RESET | GP1 | | HREF | GP12 |
| D0–D7 | GP2–GP9 (en orden) | | VSYNC | GP13 |
| XCLK / MCLK | GP10 | | SDA / SCL | GP14 / GP15 |
| 3V3, GND | 3V3, GND | | | |

Las pines están en `micropython/config.py`; revise el módulo (cada fabricante rotula distinto).

## 2. Subir al Pico (Thonny → "Subir a /", no copien y peguen)

Todo el contenido de `micropython/` (incluidas las carpetas `drivers/` y `umqtt/`) a la raíz del Pico, y un archivo `.env` con **solo** la contraseña del WiFi.
Antes edite en `config.py`: `WIFI_SSID` y `PREFIX` (`UDFJC/iot_ws/robot<NN>/`, con su número de 2 dígitos).

## 3. Probar, en este orden

1. **Sin WiFi:** abra `camara_test.py` y pulse **F5**. Debe salir `0x21 -> OK` y dos capturas.
   Con barras de color (`barras(True)`; `capturar()`) salen muchos colores distintos.
   `NO llegó imagen` o `TODO EN CERO` = cableado de PCLK, HREF, VSYNC o D0–D7.
2. **Por MQTT:** deje `main.py` en el Pico (se guarda en la raíz) y reinícielo. Salen `Cámara lista: 160x120` y `MQTT conectado`.
3. **Ver la imagen:** la página del profesor `PubSub_client_web.html` (suscribe `camera/frame/+`) con el mismo prefijo.
4. Para ver la escena real y no las barras: `CAMERA_TEST_PATTERN = 0` en `config.py`.

## Si algo falla

| Síntoma | Causa probable |
|---|---|
| `I2C device 33 not found` | SDA/SCL mal, o sin 3V3/GND; el reloj XCLK tiene que estar corriendo para que conteste |
| `no llegó imagen` | PCLK, HREF o VSYNC mal conectados, o D0–D7 fuera de orden |
| No sale nada en la página | Prefijo distinto en el Pico y en la página, o el broker rechaza los 38 KB (pruebe `CAMERA_SIZE_DIV = 3`) |
| Imagen con colores raros | D0–D7 en otro orden; el PIO exige GP2…GP9 seguidos |

> Probado solo con módulos simulados en el PC; falta probarlo con la cámara real.
