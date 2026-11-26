# Proyecto final: el carro va a un punto de color y lo marca con el brazo

## 1. Qué pide el profesor (enunciado)

> El CarroBot deberá encontrar un objetivo (de color **rojo, de 1 cm de diámetro, ubicado en el
> suelo a 10 cm de la posición inicial**), desplazarse autónomamente hasta él y posicionar con
> su brazo robótico la punta de un lápiz sobre el objetivo. Usará la cámara OV7670 para
> observar, identificar el color objetivo y tomar decisiones. **La misión debe realizarse sin
> control remoto ni intervención humana durante su ejecución.**

Esta rama (`proyecto_final`) parte de `taller_12`, así que ya trae el robot completo con todas
las calibraciones de los talleres anteriores: carro, brazo de 2 servos (con alpha1/alpha2
invertidos), OLED, cámara, MQTT y Flet.

## 2. Decisiones de diseño

- **La misión es autónoma: corre en el Pico.** Detectar el color y decidir los movimientos
  lo hace el propio robot. Una imagen de 160x120 son 38 KB y el Pico tiene 264 KB de RAM, así
  que cabe; si la detección va lenta se baja a 80x60. Si el PC estuviera en el lazo de control,
  contaría como control remoto.
- **Flet no controla la misión: solo la arranca y la muestra.**
  - **Arrancar / detener:** un botón que manda un solo mensaje (`mission/cmd`). Después el
    robot hace todo solo.
  - **Ver lo que ve el robot:** Flet muestra la imagen de la cámara (`camera/frame/...`) y
    dibuja encima el punto que el robot detectó y el estado de la misión (`mission/status`).
- **El PC es herramienta de calibración**, no parte de la misión: `pc/vision.py` (OpenCV)
  sirve para probar el color con imágenes reales y `pc/calibrar_camara.py` para medir el ritmo
  de imágenes.
- **El punto no se mueve**, lo que se mueve es el carro. Basta con pocas imágenes por segundo.
- **No hay sensor en las ruedas**: el movimiento es por tiempo y nunca sale exacto, así que se
  repite **mirar -> corregir** (sección 4) en vez de calcularlo todo de una vez.
- **Saber si los motores consumen (corriente) es opcional** (sección 6).

### Lo que hace especial a este enunciado

- **El objetivo es muy pequeño y cercano.** 1 cm a 160x120 son pocos píxeles: el
  `AREA_MIN_PX` de `pc/ajustes.py` (12) probablemente lo descarta; hay que probarlo con la cámara
  real. A 10 cm el punto puede quedar en la zona ciega o en el borde inferior de la imagen: hay
  que encontrar una altura e inclinación de la cámara que lo vean a esa distancia.
- **El brazo estirado llega a unos 8 cm y el objetivo está a 10 cm**, así que el carro casi no
  avanza: serán uno o dos pasos cortos.
- **"Encontrar" el objetivo:** si no lo ve, debe girar un poco y volver a mirar (barrido).
- **Se pide posicionar la punta del lápiz sobre el objetivo.** Marcar un punto sería un extra.

## 3. Cómo se reparte el trabajo

```
                 ┌──────────────── Pico W (autónomo) ────────────────┐
OV7670 ─► imagen ─► detectar rojo ─► decidir ─► motores y servos      │
                 └──────┬───────────────────────────▲─────────────────┘
        camera/frame/…  │  mission/status           │ mission/cmd (solo "arrancar"/"detener")
                        ▼                           │
                      Flet: ve la imagen y el punto detectado, botón Arrancar
```

Los tópicos llevan el prefijo del robot: `UDFJC/iot_ws/robot<NN>/` (`NN` de 2 dígitos).
`mission/cmd` y `mission/status` son tópicos nuevos de este proyecto (aún sin implementar).

## 4. El ciclo que corre el robot: mirar -> girar -> avanzar -> parar -> mirar

1. **Mirar.** Toma una imagen y busca el rojo. Obtiene la posición del punto y `error_x`
   (de -1 a 1: negativo = a la izquierda del centro, positivo = a la derecha).
   Si no lo ve: barrido (girar un poco y mirar de nuevo).
2. **Girar en el sitio** (`v = 0`) para centrar el punto. Ángulo = `error_x × FOV_horizontal / 2`;
   tiempo = ángulo / `w`.
3. **Avanzar.** Distancia = la que da la geometría a partir de la fila del punto en la imagen
   (`vision.distancia_al_piso`) menos `ALCANCE_BRAZO_M`. Tiempo = distancia / `v`.
4. **Parar, esperar una imagen nueva y volver al paso 1** hasta que el punto quede centrado y
   al alcance del brazo.
5. **Posicionar el brazo:** estirarlo hacia abajo hasta que la punta del lápiz quede sobre el
   objetivo.

Cerca del objetivo este sale de la imagen (zona ciega justo delante de la cámara): los últimos
centímetros se avanzan con la última distancia conocida.

### Cómo se mueve el robot

Con los mismos comandos de la coreografía (`motion/sequence`, `run_at: "now"`), que el Pico
ya sabe ejecutar; en la misión autónoma el robot los usa internamente:

```json
{"action": "create", "name": "paso", "run_at": "now",
 "states": [{"v_dm/s": 0, "w_deg/s": -20, "alpha0_deg": 0, "duration_s": 1.5},
            {"v_dm/s": 1.0, "w_deg/s": 0, "duration_s": 2.0}]}
```

- `v_dm/s` en **decímetros por segundo** (1.0 = 0,1 m/s); `w_deg/s` en grados por segundo
  (positivo = izquierda). `alpha0_deg` se ignora (no hay base).
- Brazo: `alpha1_deg` en [0, 180], `alpha2_deg` en [-90, 90] y `-160 <= alpha2 - alpha1 <= -20`
  (ver `taller_09_arm/common/config.py`). "Hacia abajo del todo" debe quedar dentro de esos límites.
- Si un paso no trae las alphas, el brazo conserva su posición.

## 5. Tareas y estado

| # | Tarea | Estado | Dónde |
|---|-------|--------|-------|
| 0 | Calibrar la cámara: fps, jitter y huecos reales | script listo; falta correrlo con el robot | `pc/calibrar_camara.py` |
| 1 | Detectar el punto rojo (prototipo con OpenCV para calibrar el color) | hecho, con pruebas | `pc/vision.py` |
| 2 | Medir la geometría y llenar `MISION` | **pendiente: llenar las medidas** | `taller_09_arm/common/config.py` |
| 3 | Detección de rojo en el Pico (sin OpenCV) | escrito y probado en el PC; **falta probarlo en el Pico** | `common/vision_rojo.py`, `micropython/deteccion_test.py` |
| 4 | Ciclo autónomo (mirar, girar, avanzar, parar, barrido) | escrito y probado con un simulador; **falta probarlo en el robot** | `common/mision.py`, `micropython/mision_task.py` |
| 5 | Bajar el brazo sobre el objetivo | escrito (pose `brazo_abajo`); **falta probarlo en el robot** | `MISION["brazo_abajo"]` |
| 6 | Flet: imagen con el punto detectado, estado y botones Arrancar/Detener | escrito; **sin probar con el robot** | tarjeta 7 de `taller_09_arm/flet_ui` |
| – | Medir corriente de los motores (opcional) | script listo, **sin probar** | `micropython/prueba_corriente.py` |

### Tarea 0: calibrar la cámara

1. Robot encendido con `main.py` (o el de `taller_12_camara`) y el `PREFIX` con su número de robot.
2. En el PC: `pip install -r pc/requirements.txt`, luego `cd pc && python calibrar_camara.py 30 --png`.
3. El resultado: `fps`, `jitter_s` (qué tan irregular es el ritmo), `huecos` (imágenes que faltan
   o llegaron tarde) y cuántas llegaron corruptas. Guarda `ultima.png` para ver qué ve la cámara.
4. Si hay huecos o corruptas: subir `CAMERA_PERIOD_MS` o bajar la resolución
   (`CAMERA_SIZE_DIV`: 2 = 160x120, 3 = 80x60). Hoy la cámara manda una imagen cada 2 s.

### Tarea 2: las medidas (diccionario `MISION`)

Se llenan **una sola vez**, en `taller_09_arm/common/config.py`, dentro de `MISION`. El robot las
lee de ahí y el PC también. Mientras alguna siga en `None`, **la misión se niega a arrancar** y
Flet muestra cuál falta: así el robot nunca se mueve con números inventados.

| Clave | Qué es | Cómo se mide |
|---|---|---|
| `cam_altura_m` | altura de la cámara sobre el piso | regla |
| `cam_inclinacion_deg` | cuánto mira hacia abajo respecto a la horizontal | transportador o `atan((altura - h_punto)/dist)` |
| `fov_v_deg`, `fov_h_deg` | campo de visión vertical y horizontal | `2·atan((alto_visible/2)/distancia)` contra una pared (ver abajo) |
| `punta_dist_m` | distancia horizontal de la cámara a la punta del lápiz con el brazo abajo | regla, con el brazo en `brazo_abajo` |

Medir el campo de visión: cámara de frente a una pared a una distancia `d` conocida; mire cuántos
cm de pared caben de arriba a abajo en la imagen (`h`) y de lado a lado (`a`).
`fov_v = 2·atan(h/2/d)`, `fov_h = 2·atan(a/2/d)`.

Lo demás de `MISION` ya tiene un valor razonable que se afina probando: `w_giro_deg_s` y `v_dm_s`
(velocidades del carro), `tol_err_x`, `tol_dist_m`, `barrido_deg`, `settle_ms`, y los umbrales del
rojo `rojo_r_min` y `rojo_dif_min`.

**Pose del brazo:** `brazo_abajo = (0, 0, -90)`. Con la cinemática del MeArm es la punta más baja y
adelantada (~10 cm del hombro), y cumple `-160 <= alpha2 - alpha1 <= -20`.

## Cómo probar, de a una pieza

Suba al Pico: `main.py`, `config.py`, `mision_task.py`, `camera_task.py`, `deteccion_test.py`,
`camara_test.py`, `drivers/`, `common/` (con `vision_rojo.py` y `mision.py`) y lo demás de siempre.

1. **Detección (sin motores):** `deteccion_test.py`, F5, `ver()`. Con un punto rojo de 1 cm a 10 cm
   debe decir `VISTO` con `area >= 2` y cuánto tardó. Si dice `no veo rojo`, imprime el color del
   píxel más rojo: así se ajustan `rojo_r_min` y `rojo_dif_min`. Con `repetir(10)` se mueve el punto
   y `cx`, `cy` deben cambiar.
2. **Geometría:** con el punto a 10 cm, `ver()` da su fila `cy`. Compare con la distancia real; si
   no cuadra, revise altura, inclinación y `fov_v`.
3. **Misión completa:** con el robot en el piso, el punto a 10 cm y las medidas llenas, abra Flet y
   pulse **ARRANCAR misión** (tarjeta 7). Después no se toca nada. Mire la cruz verde y el estado.
   Si algo sale mal, **DETENER misión**.
4. **Sin Flet:** también se arranca publicando `{"action": "start"}` en `<PREFIX>mission/cmd`.

Qué esperar en la Shell del Pico (cada vuelta): `Misión: buscando | detección 180 ms | {...}`.

## Qué ya está hecho y qué no

- Probado en el PC (217 pruebas): detección del rojo, geometría, máquina de estados, una simulación
  completa del carro llegando al punto, y la tarea de misión con un robot simulado.
- **No probado en hardware:** nada de lo anterior se ha corrido en el Pico ni con la cámara real.
  Lo más probable que haya que ajustar: los umbrales del rojo (la OV7670 tiñe los colores), el
  tiempo de la detección en el Pico (si pasa de ~0,5 s, se baja a 80x60) y las velocidades del carro.
- El giro en el sitio no tiene calibración de ganancia: si gira más o menos de lo debido, se ajusta
  `w_giro_deg_s` (o `MOTOR_MIN_DUTY` en `micropython/config.py`).

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
