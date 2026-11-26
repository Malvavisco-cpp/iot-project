# Proyecto final: el carro va al punto rojo y le pone el lápiz encima

## 1. Qué pide el profesor (enunciado)

> El CarroBot deberá encontrar un objetivo (de color **rojo, de 1 cm de diámetro, ubicado en el
> suelo a 10 cm de la posición inicial**), desplazarse autónomamente hasta él y posicionar con
> su brazo robótico la punta de un lápiz sobre el objetivo. Usará la cámara OV7670 para
> observar, identificar el color objetivo y tomar decisiones. **La misión debe realizarse sin
> control remoto ni intervención humana durante su ejecución.**

Esta rama (`proyecto_final`) parte de `taller_12`, así que trae el robot completo con todas las
calibraciones de los talleres anteriores: carro, brazo de 2 servos (con alpha1/alpha2 invertidos),
OLED, cámara, MQTT y Flet.

## 2. Estado de un vistazo

| # | Tarea | Estado | Dónde |
|---|-------|--------|-------|
| 0 | Calibrar la cámara: fps, jitter y huecos reales | script listo; falta correrlo con el robot (sección 7) | `pc/calibrar_camara.py` |
| 1 | Detectar el punto rojo con OpenCV (para calibrar el color en el PC) | hecho, con pruebas | `pc/vision.py` |
| 2 | Medir la geometría y llenar `MISION` | **pendiente: llenar las medidas** | `taller_09_arm/common/config.py` |
| 3 | Detección del rojo en el Pico (sin OpenCV) | escrito y probado en el PC; **falta probarlo en el Pico** | `common/vision_rojo.py`, `micropython/deteccion_test.py` |
| 4 | Ciclo autónomo: mirar, girar, avanzar, parar, barrido | escrito y probado con un simulador; **falta probarlo en el robot** | `common/mision.py`, `micropython/mision_task.py` |
| 5 | Bajar el brazo sobre el objetivo | escrito (pose `brazo_abajo`); **falta probarlo en el robot** | `MISION["brazo_abajo"]` |
| 6 | Flet: imagen con el punto detectado, estado y botones Arrancar/Detener | escrito; **sin probar con el robot** | tarjeta 7 de `taller_09_arm/flet_ui` |
| – | Medir la corriente de los motores (opcional) | script listo, **sin probar** | `micropython/prueba_corriente.py` |

Probado en el PC (217 pruebas): detección del rojo, geometría, máquina de estados, una simulación
completa del carro llegando al punto y la tarea de misión con un robot simulado.
**Nada de esto se ha corrido todavía en el Pico, con la cámara real ni con Flet.**

## 3. Decisiones de diseño

- **La misión es autónoma: corre en el Pico.** Detectar el color y decidir los movimientos lo hace
  el propio robot. Una imagen de 160x120 son 38 KB y el Pico tiene 264 KB de RAM, así que cabe.
  Si el PC estuviera en el lazo de control, contaría como control remoto.
- **Flet no controla la misión: solo la arranca y la muestra.**
  - **Arrancar / detener:** un solo mensaje a `mission/cmd`. Después el robot hace todo solo.
  - **Ver lo que ve el robot:** Flet muestra la imagen de la cámara (`camera/frame/...`), dibuja
    una cruz verde sobre el punto que el robot detectó y muestra el estado (`mission/status`).
- **El PC es herramienta de calibración**, no parte de la misión: `pc/vision.py` (OpenCV) prueba el
  color con imágenes reales y `pc/calibrar_camara.py` mide el ritmo de imágenes.
- **El punto no se mueve**, lo que se mueve es el carro. Bastan pocas imágenes por segundo.
- **No hay sensor en las ruedas**: el movimiento es por tiempo y nunca sale exacto, así que se
  repite **mirar -> corregir** (sección 5) en vez de calcularlo todo de una vez.
- **Medir corriente es opcional** (sección 9): se sabe qué se mandó y la cámara confirma el resultado.
- **Sin medidas no se mueve:** las medidas de `MISION` empiezan en `None` y la misión se niega a
  arrancar hasta que se llenen.

### Lo que hace especial a este enunciado

- **El objetivo es muy pequeño y cercano.** 1 cm a 160x120 son pocos píxeles (`area_min` = 2 en
  `MISION`). A 10 cm el punto puede quedar en la zona ciega o en el borde inferior de la imagen: hay
  que encontrar una altura e inclinación de la cámara que lo vean a esa distancia.
- **La punta del brazo abajo queda a ~10 cm del hombro** (cinemática del MeArm) y el objetivo está a
  10 cm de la posición inicial: el carro casi no avanza, serán uno o dos pasos cortos.
- **"Encontrar" el objetivo:** si no lo ve, gira un poco y vuelve a mirar (barrido).
- **Se pide posicionar la punta del lápiz sobre el objetivo.** Marcar un punto sería un extra.

## 4. Cómo se reparte el trabajo

```
                 ┌──────────────── Pico W (autónomo) ────────────────┐
OV7670 ─► imagen ─► detectar rojo ─► decidir ─► motores y servos      │
                 └──────┬───────────────────────────▲─────────────────┘
        camera/frame/…  │  mission/status           │ mission/cmd (solo "start" / "stop")
                        ▼                           │
                      Flet: ve la imagen y el punto detectado, botones Arrancar/Detener
```

Los tópicos llevan el prefijo del robot: `UDFJC/iot_ws/robot<NN>/` (`NN` de 2 dígitos).

| Tópico | Sentido | Contenido |
|---|---|---|
| `mission/cmd` | Flet -> robot | `{"action": "start"}` o `{"action": "stop"}` |
| `mission/status` | robot -> Flet | `fase`, `iter`, `motivo`, `visto`, `cx`, `cy`, `err_x`, `ang_deg`, `dist_m` |
| `camera/frame/rgb565_WxH` | robot -> Flet | imagen en bruto (RGB565) |

## 5. El ciclo que corre el robot: mirar -> girar -> avanzar -> parar -> mirar

1. **Mirar.** Espera a que el carro frene y se asiente (`settle_ms`), captura una imagen y busca el
   rojo. Obtiene la posición del punto y `err_x` (de -1 a 1: negativo = a la izquierda del centro).
   Si no lo ve: **barrido** (gira `barrido_deg` y mira de nuevo, hasta `barrido_max` veces).
2. **Girar en el sitio** (`v = 0`) si `|err_x| > tol_err_x`. Ángulo = `atan(err_x · tan(fov_h/2))`;
   tiempo = ángulo / `w_giro_deg_s`. Si el punto está a la derecha, el carro gira a la derecha
   (`w < 0`; `w > 0` es izquierda, como el gemelo).
3. **Avanzar.** Distancia al punto = geometría a partir de la fila `cy` (altura e inclinación de la
   cámara y `fov_v`). Avanza `distancia - punta_dist_m` (nunca más de `avance_max_m` de una vez);
   tiempo = distancia / `v`.
4. **Parar, esperar una imagen nueva y volver al paso 1.** Máximo `max_iter` correcciones.
5. **Bajar el brazo** (`brazo_abajo`) cuando falta menos de `tol_dist_m`, o cuando perdió el punto de
   vista justo al llegar (la zona ciega de la cámara) y lo que quedaba por avanzar era menos de
   `ciego_m`. Termina en fase `listo` con el brazo abajo.
6. **Falla con un motivo** (`fallo`) si no encuentra el punto tras el barrido, si no llega en
   `max_iter` intentos, si la geometría no cuadra o si hay una excepción. En cualquier falla frena el carro.

Cada paso es una lista de estados que ejecuta el mismo `MotionPlayer` de las coreografías:

```json
[{"v_dm/s": 0, "w_deg/s": -20, "duration_s": 1.5},
 {"v_dm/s": 1.0, "w_deg/s": 0, "duration_s": 2.0}]
```

- `v_dm/s` en **decímetros por segundo** (1.0 = 0,1 m/s); `w_deg/s` en grados por segundo.
- Brazo: `alpha1_deg` en [0, 180], `alpha2_deg` en [-90, 90] y `-160 <= alpha2 - alpha1 <= -20`
  (ver `taller_09_arm/common/config.py`). Si un paso no trae las alphas, el brazo conserva su posición.

## 6. Las medidas (diccionario `MISION`)

Se llenan **una sola vez**, en `taller_09_arm/common/config.py`, dentro de `MISION`. El robot y el PC
las leen de ahí. Mientras alguna siga en `None`, la misión no arranca y Flet muestra cuál falta.

| Clave | Qué es | Cómo se mide |
|---|---|---|
| `cam_altura_m` | altura de la cámara sobre el piso | regla |
| `cam_inclinacion_deg` | cuánto mira hacia abajo respecto a la horizontal | transportador |
| `fov_v_deg`, `fov_h_deg` | campo de visión vertical y horizontal de la imagen | ver abajo |
| `punta_dist_m` | distancia horizontal de la cámara a la punta del lápiz con el brazo abajo | regla, con el brazo en `brazo_abajo` |

**Medir el campo de visión:** cámara de frente a una pared a una distancia `d` conocida; mire cuántos
cm de pared caben de arriba a abajo en la imagen (`h`) y de lado a lado (`a`):
`fov_v = 2·atan(h/2/d)`, `fov_h = 2·atan(a/2/d)`.

Lo demás de `MISION` ya tiene un valor razonable que se afina probando:

| Clave | Para qué |
|---|---|
| `w_giro_deg_s`, `v_dm_s`, `avance_max_m` | velocidades del carro y largo máximo de un avance |
| `tol_err_x`, `tol_dist_m`, `ciego_m` | cuándo dar por centrado / por llegado |
| `barrido_deg`, `barrido_max`, `max_iter` | búsqueda y número de intentos |
| `settle_ms` | espera tras frenar antes de mirar (pasa el temblor del carro) |
| `rojo_r_min`, `rojo_dif_min`, `area_min` | qué cuenta como rojo (R alto y G, B bajos; escala 0-255) |
| `brazo_abajo`, `brazo_t_s` | pose del brazo abajo y lo que tarda en bajar |

**Pose del brazo:** `brazo_abajo = (0, 0, -90)`. Con la cinemática del MeArm es la punta más baja y
adelantada (~10 cm del hombro) y cumple `-160 <= alpha2 - alpha1 <= -20`.

El `PREFIX` está en el mismo archivo y debe llevar **su número de robot con 2 dígitos**
(hoy dice `robot4`). El color en HSV para el prototipo del PC está en `pc/ajustes.py`.

## 7. Cómo correr las tareas que faltan

Se hacen **en este orden**: cada una necesita que la anterior funcione.

### Antes de todo: dejar el robot listo (una vez)

1. **Su número de robot.** En `taller_09_arm/common/config.py` ponga `PREFIX = "UDFJC/iot_ws/robot34/"`
   (su número, 2 dígitos y la barra final). El mismo archivo lo usa el robot y Flet.
2. **WiFi.** En `taller_09_arm/micropython/config.py` ponga `WIFI_SSID` (red de 2.4 GHz). La contraseña
   va sola en un archivo `.env` en la raíz del Pico (Thonny: Archivo > Nuevo, escriba solo la contraseña,
   Guardar como > Raspberry Pi Pico > `.env`).
3. **Subir el código al Pico con Thonny** (no copiar y pegar: se suben los archivos). Intérprete en
   *MicroPython (Raspberry Pi Pico)*, Ver > Archivos:
   - clic derecho en la carpeta `taller_09_arm/common` > **Subir a /**
   - entre a `taller_09_arm/micropython/`, seleccione **todo** (los `.py` y las carpetas `drivers` y
     `umqtt`) > clic derecho > **Subir a /**
4. Reinicie el Pico (botón Stop/Restart de Thonny). En la Shell debe salir
   `Robot listo | nodo: ... | prefijo: UDFJC/iot_ws/robot34/` y `Cámara OV7670 lista: 160x120`.

> **Cada vez que cambie `common/config.py`** (las medidas de `MISION`, el `PREFIX`) hay que volver a
> subir la carpeta `common` al Pico y reiniciarlo, porque el robot lee las medidas de ahí.

### Tarea 0 · Calibrar la cámara (en el PC)

Con el robot encendido y publicando imágenes:

```bash
cd proyecto_final/pc
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python calibrar_camara.py 30 --png
```

Escucha 30 s y muestra `fps`, `jitter_s`, `huecos` y cuántas imágenes llegaron corruptas; guarda
`ultima.png` para ver qué ve la cámara. Si dice que no llegaron imágenes: revise el `PREFIX` y corra
`camara_test.py` en el Pico (F5; debe salir `0x21 -> OK`). Si hay huecos o corruptas, suba
`CAMERA_PERIOD_MS` o baje la resolución (`CAMERA_SIZE_DIV`: 2 = 160x120, 3 = 80x60).

### Tarea 2 · Medir y llenar `MISION`

1. Mida lo de la sección 6 (altura, inclinación, campos de visión, `punta_dist_m`).
2. Para el campo de visión use `calibrar_camara.py 5 --png` con la cámara de frente a una pared a una
   distancia conocida, y mida en `ultima.png` cuánto cabe.
3. Escríbalos en `MISION` (`taller_09_arm/common/config.py`), **suba `common` al Pico y reinícielo**.

Para medir `punta_dist_m`, baje el brazo desde Flet (tarjeta 5 del brazo, o tarjeta 1 con
`alpha1 = 0`, `alpha2 = -90` y **Solo brazo**; la misma pose que usará la misión) y mida en el piso la
distancia entre la cámara y la punta del lápiz.

### Tarea 3 · Detección del rojo en el Pico (sin motores)

1. En Thonny abra `deteccion_test.py` (en el Pico o en `micropython/`) y pulse **F5**.
2. Ponga el punto rojo de 1 cm a 10 cm frente a la cámara. En la Shell escriba `ver()`.
   - Bien: `VISTO (xx ms): cx=... cy=... area=... err_x=...`.
   - `no veo rojo`: imprime el color del píxel más rojo. Con ese R, G, B ajuste `rojo_r_min` y
     `rojo_dif_min` en `MISION` (suba `common` y reinicie).
3. `repetir(10)` mientras mueve el punto: `cx` y `cy` deben cambiar. Anote cuántos ms tarda; si pasa de
   ~500 ms, baje la resolución (`CAMERA_SIZE_DIV = 3`).

### Tareas 4 y 5 · Ciclo autónomo y brazo (el robot)

**Primera prueba con las ruedas en el aire** (levante el carro): así se ve hacia dónde gira y cuánto
avanza sin que se vaya. Después, en el piso.

1. Pico reiniciado con `main.py` (sección "Antes de todo"), medidas llenas, punto rojo a 10 cm.
2. Arranque Flet (Tarea 6) y pulse **ARRANCAR misión**. Sin Flet también sirve publicar
   `{"action": "start"}` en `<PREFIX>mission/cmd` (MQTTX o la página del profesor).
3. **No toque nada.** En la Shell del Pico sale cada vuelta:
   `Misión: buscando | detección 180 ms | {'visto': True, 'err_x': 0.31, 'dist_m': 0.18, ...}`.
   Debe girar hasta centrar el punto, avanzar, frenar, volver a mirar y, al final, bajar el brazo
   (`fase: listo`).
4. Para frenarla: **DETENER misión** en Flet o `{"action": "stop"}`.
5. Si no arranca, el motivo sale en la Shell y en Flet (`faltan medidas: ...`).

Ajustes típicos: gira de más o de menos → `w_giro_deg_s`; avanza de más o de menos → `v_dm_s`; para
muy lejos o muy cerca → `punta_dist_m`; no lo ve al acercarse → `ciego_m`. Siempre: cambiar
`common/config.py`, subir `common`, reiniciar.

### Tarea 6 · Flet

```bash
cd taller_09_arm
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m flet_ui.main
```

Arriba debe decir **Broker: conectado** y **Robot: quieto**. Baje a la tarjeta **6. Cámara** (debe
mostrar la imagen) y a la **7. Misión autónoma**: **ARRANCAR misión** / **DETENER misión**, el estado y la
cruz verde sobre el punto que detectó el robot. Flet y el robot deben usar el mismo broker y `PREFIX`.

## 8. Lo que probablemente haya que ajustar en el robot

- **Los umbrales del rojo:** la OV7670 suele teñir los colores.
- **El tiempo de la detección en el Pico:** si pasa de ~0,5 s, se baja la resolución a 80x60.
- **Las velocidades del carro:** el giro en el sitio no tiene ganancia calibrada; si gira de más o de
  menos, se ajusta `w_giro_deg_s` (o `MOTOR_MIN_DUTY` en `micropython/config.py`). Mientras corre la
  misión, la cámara captura cada `CAMERA_PERIOD_MISION_MS` (700 ms).
- **La zona ciega:** a 10 cm el punto puede salir de la imagen al acercarse; para eso existe `ciego_m`.

## 9. Medir la corriente de los motores (opcional)

Un pin del Pico **no puede medir corriente**: un GPIO lee 0 o 1 y el ADC lee voltaje. Para medirla
hace falta un sensor en serie con la batería de los motores. `micropython/prueba_corriente.py` usa un
**INA219** (módulo I2C barato) en el mismo bus de la OLED (GP20/GP21, dirección 0x40): mide la
corriente en reposo y marca `MOVIENDO` cuando sube más de `UMBRAL_MA`. Solo ayudaría a detectar un
carro trabado. Está escrito sin tener el módulo: lo primero es que `scan()` lo encuentre.

## 10. Pruebas automáticas

```
cd taller_09_arm && python -m pytest tests -q        # 217: robot, detección, misión, tarea de misión
cd .. && python -m pytest proyecto_final/tests -q    # 6: prototipo OpenCV y calibración de la cámara
```
