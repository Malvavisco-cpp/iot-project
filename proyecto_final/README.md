# Proyecto final: el carro va a un punto de color y lo marca con el brazo

## 1. Qué hay que lograr

El carro (con el brazo MeArm y la cámara OV7670 encima) debe:

1. Ver en la cámara un **punto de color que está quieto en el piso**.
2. Moverse hacia él.
3. Parar a la distancia justa, **estirar el brazo completamente hacia abajo** y, con un
   lápiz o marcador en la punta, **poner un punto en el centro** del punto de color.

Esta rama (`proyecto_final`) parte de `taller_12`, así que ya trae el robot completo con todas
las calibraciones de los talleres anteriores: carro, brazo de 2 servos (con alpha1/alpha2
invertidos), OLED, cámara, MQTT y Flet.

## 2. Puntos de partida (lo que ya está decidido)

- **El punto no se mueve.** Es lo que se mueve el carro. Por eso la cámara no necesita
  muchos fps: con una imagen cada 1–2 s alcanza. La pausa de la cámara mientras el carro se mueve
  (`CAMERA_PAUSE_WHILE_MOVING = True`) no estorba.
- **La visión va en el PC, no en el Pico.** El Pico solo captura y publica la imagen
  (la RAM del Pico no da para visión). El PC detecta el punto con OpenCV y le manda
  comandos al robot por MQTT.
- **Los motores se accionan con los comandos que el robot ya entiende**: velocidad lineal
  `v`, velocidad de giro `w` y una duración. No hace falta código nuevo en el Pico para mover el carro.
- **No hay sensor en las ruedas**, así que el movimiento es por tiempo y nunca sale exacto.
  Por eso no se calcula todo de una vez: se repite **mirar → corregir** (sección 4).
- **Saber si los motores consumen (corriente) es opcional.** Se sabe qué se mandó, y la cámara
  confirma el resultado porque el punto cambia de lugar en la imagen. Ver sección 6.

## 3. Cómo se reparte el trabajo

```
OV7670 ─► Pico W ──MQTT camera/frame/rgb565_160x120──► PC (OpenCV)
                                                          │ decide
motores y servos ◄─ Pico W ◄──MQTT motion/state o motion/sequence
```

Todos los tópicos llevan el prefijo del robot: `UDFJC/iot_ws/robot<NN>/` (`NN` de 2 dígitos).

## 4. El ciclo: mirar → girar → avanzar → parar → mirar

1. **Mirar.** El PC recibe una imagen y `vision.buscar_punto` devuelve la posición del punto
   y `error_x` (de -1 a 1: negativo = punto a la izquierda del centro, positivo = a la derecha).
2. **Girar en el sitio** (`v = 0`) para centrar el punto. Ángulo = `error_x × FOV_horizontal / 2`;
   tiempo = ángulo / `w`.
3. **Avanzar.** Distancia = la que da la geometría a partir de la fila del punto en la imagen
   (`vision.distancia_al_piso`) menos `ALCANCE_BRAZO_M`. Tiempo = distancia / `v`.
4. **Parar, esperar una imagen nueva y volver al paso 1.** Se repite hasta que el punto quede
   centrado y a la distancia del brazo.
5. **Marcar.** Estirar el brazo hacia abajo, tocar el centro y volver a subirlo.

Cerca del punto este sale de la imagen (zona ciega justo delante de la cámara). Por eso los
últimos centímetros se avanzan "a ciegas" con la última distancia conocida.

### Cómo se manda un movimiento al robot

Con `motion/sequence` (el mismo formato de la coreografía del profesor), `run_at: "now"`:

```json
{"action": "create", "name": "paso", "run_at": "now",
 "states": [{"v_dm/s": 0, "w_deg/s": -20, "alpha0_deg": 0, "duration_s": 1.5},
            {"v_dm/s": 1.0, "w_deg/s": 0, "duration_s": 2.0}]}
```

- `v_dm/s` va en **decímetros por segundo** (1.0 = 0,1 m/s); `w_deg/s` en grados por segundo
  (positivo = izquierda).
- `alpha0_deg` se ignora (el robot no tiene base).
- El brazo se mueve con `alpha1_deg` y `alpha2_deg`. Rangos permitidos: alpha1 en [0, 180],
  alpha2 en [-90, 90] y `-160 ≤ alpha2 - alpha1 ≤ -20`. "Hacia abajo del todo" debe quedar dentro
  de esos límites (ver `taller_09_arm/common/config.py`).
- Si un paso no trae las alphas, el brazo conserva su posición actual.

## 5. Tareas y estado

| # | Tarea | Estado | Dónde |
|---|-------|--------|-------|
| 0 | Calibrar la cámara: fps, jitter y huecos reales que llegan al PC | script listo; falta correrlo con el robot | `pc/calibrar_camara.py` |
| 1 | Detectar el punto de color en la imagen con OpenCV | hecho, con pruebas | `pc/vision.py` |
| 2 | Medir la geometría (altura e inclinación de la cámara, campo de visión, alcance del brazo) | **pendiente: medir y llenar `pc/ajustes.py`** | `pc/ajustes.py` |
| 3 | Bucle de la sección 4 (mirar, girar, avanzar, parar, repetir) | pendiente | `pc/` |
| 4 | Estirar el brazo hacia abajo y marcar el centro | pendiente | `MeArm` de `taller_09_arm` |
| – | Medir corriente de los motores (opcional) | script listo, **sin probar** | `micropython/prueba_corriente.py` |

### Tarea 0: calibrar la cámara

1. Robot encendido con `main.py` (o el de `taller_12_camara`) y el `PREFIX` con su número de robot.
2. En el PC: `pip install -r pc/requirements.txt`, luego `cd pc && python calibrar_camara.py 30 --png`.
3. El resultado: `fps`, `jitter_s` (qué tan irregular es el ritmo), `huecos` (imágenes que faltan
   o llegaron tarde) y cuántas llegaron corruptas. Guarda `ultima.png` para ver qué ve la cámara.
4. Si hay huecos o corruptas: subir `CAMERA_PERIOD_MS` o bajar la resolución
   (`CAMERA_SIZE_DIV`: 2 = 160x120, 3 = 80x60). Hoy la cámara manda una imagen cada 2 s.

### Tarea 2: geometría que hay que medir

Están en cero a propósito en `pc/ajustes.py`:

- `CAM_ALTURA_M`: altura de la cámara sobre el piso.
- `CAM_INCLINACION_DEG`: cuánto mira hacia abajo respecto a la horizontal.
- `CAM_FOV_VERT_DEG` (y el horizontal, para el giro): campo de visión del OV7670 con su lente.
- `ALCANCE_BRAZO_M`: hasta dónde llega la punta del marcador con el brazo estirado (~8 cm).
- `DIST_PARADA_M`: a qué distancia del punto se detiene el carro para bajar el brazo.

Con estos valores, la fila `cy` del punto en la imagen da su distancia al piso.

## 6. Corriente de los motores (opcional)

Un pin del Pico **no puede medir corriente**: un GPIO lee 0 o 1 y el ADC lee voltaje. Para
medirla hace falta un sensor en serie con la batería de los motores. `micropython/prueba_corriente.py`
usa un **INA219** (módulo I2C barato) en el mismo bus de la OLED (GP20/GP21, dirección 0x40).
Mide la corriente en reposo y marca `MOVIENDO` cuando sube más de `UMBRAL_MA`. Solo ayudaría a
detectar un carro trabado. Está escrito sin tener el módulo: lo primero es que `scan()` lo encuentre.

## 7. Pruebas y configuración

```
python -m pytest proyecto_final/tests -q
```

Todo se configura en `pc/ajustes.py`: color objetivo (rangos HSV; rojo por defecto, hay que
medir el suyo con la cámara real) y la geometría. El broker y el `PREFIX` se leen de
`taller_09_arm/common/config.py`: el `PREFIX` de ahí debe tener **su número de robot con
2 dígitos** (hoy dice `robot4`).
