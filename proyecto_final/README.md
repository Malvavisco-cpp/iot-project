# Proyecto final: el carro va al punto de color y lo marca con el brazo

El carro (con el brazo MeArm y la cámara OV7670) busca un punto de color en el piso,
se acerca, estira el brazo hacia abajo y pone un punto con un marcador en su centro.
Esta rama parte de `taller_12`: ya trae el robot completo (carro, brazo de 2 servos,
OLED, cámara, MQTT, Flet) con todas las calibraciones hechas hasta ahora.

## Cómo se reparte el trabajo

```
OV7670 ──► Pico W ──MQTT camera/frame/rgb565_160x120──► PC (OpenCV) ──MQTT motion/*──► Pico W ──► motores y servos
```

La cámara del Pico solo captura y publica (la RAM del Pico no da para visión). El PC
detecta el punto con OpenCV, decide y manda comandos `motion/state` o `motion/sequence`,
los mismos que ya entiende el robot.

## Tareas (en orden)

| # | Tarea | Estado | Dónde |
|---|-------|--------|-------|
| 0a | Calibrar la cámara: ritmo de imágenes (fps), jitter y huecos | script listo, falta correrlo con el robot | `pc/calibrar_camara.py` |
| 0b | Saber si los motores consumen (se mueven o no) midiendo corriente | script listo, **sin probar** (falta el INA219) | `micropython/prueba_corriente.py` |
| 1 | Detectar el punto de color en la imagen (OpenCV) | hecho y con pruebas | `pc/vision.py` |
| 2 | Medir la geometría (altura/inclinación de la cámara, alcance del brazo) | pendiente: medir y llenar `pc/ajustes.py` | `pc/ajustes.py` |
| 3 | Bucle de seguimiento: girar hasta centrar el punto, avanzar, parar a `DIST_PARADA_M` | pendiente | `pc/` |
| 4 | Estirar el brazo hacia abajo y marcar el centro | pendiente | usa `MeArm` de `taller_09_arm` |

## Tarea 0a: calibrar la cámara

1. Robot encendido con `main.py` (o `taller_12_camara`) y el `PREFIX` con su número.
2. En el PC: `pip install -r pc/requirements.txt`, luego `cd pc && python calibrar_camara.py 30 --png`.
3. Mire `fps`, `jitter_s` y `huecos`. Hoy la cámara manda una imagen cada 2 s
   (`CAMERA_PERIOD_MS = 2000`) con `CAMERA_PAUSE_WHILE_MOVING = True`, o sea que **no manda
   mientras el carro se mueve**. Para seguir un punto hace falta bajar el período y decidir
   qué se hace al moverse (p. ej. avanzar a pasos cortos: mover, parar, mirar, corregir).
4. Si hay huecos o imágenes corruptas, suba el período o baje la resolución
   (`CAMERA_SIZE_DIV`: 2 = 160x120, 3 = 80x60).

## Tarea 0b: corriente de los motores

Un pin del Pico **no puede medir corriente**: un GPIO lee 0 o 1 y el ADC lee voltaje. Hace
falta un sensor en serie con la alimentación de los motores. El script usa un **INA219**
(módulo I2C barato, shunt de 0,1 ohm) en el mismo bus de la OLED (GP20/GP21, dirección 0x40).
Mide la corriente en reposo y marca `MOVIENDO` cuando sube más de `UMBRAL_MA`.
Sirve para detectar un carro trabado o que no se movió aunque se mandó el comando.
Está escrito sin tener el módulo; lo primero es ver que `scan()` lo encuentra.

## Geometría que hay que tener en cuenta

- **Cámara -> punto:** con la cámara a `CAM_ALTURA_M`, inclinada `CAM_INCLINACION_DEG` y con
  su `CAM_FOV_VERT_DEG`, la fila del punto en la imagen da su distancia al piso
  (`vision.distancia_al_piso`). Hay que medir esos tres valores; están en cero a propósito.
- **Brazo:** estirado alcanza ~8 cm (`ALCANCE_BRAZO_M`). El carro tiene que parar de modo
  que el punto quede a esa distancia del hombro. Ojo con el cuerpo del carro y con la zona
  ciega de la cámara justo delante: cerca del punto el punto sale de la imagen.
- **Rangos del brazo:** alpha1 en [0, 180], alpha2 en [-90, 90] y alpha2 - alpha1 entre -160 y -20
  (ver `taller_09_arm/common/config.py`). "Completamente hacia abajo" debe respetar eso.

## Pruebas

```
python -m pytest proyecto_final/tests -q
```

Configuración (broker, `PREFIX`, color y geometría): `pc/ajustes.py`. El broker y el `PREFIX`
se leen de `taller_09_arm/common/config.py`; el `PREFIX` de ahí debe tener su número de robot
con 2 dígitos (hoy dice `robot4`).
