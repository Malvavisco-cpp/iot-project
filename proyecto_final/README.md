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
| 0 | Calibrar la cámara: fps, jitter y huecos reales | script listo; falta correrlo con el robot | `pc/calibrar_camara.py` |
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

## 7. Cómo probar, de a una pieza

Suba al Pico: `main.py`, `config.py`, `mision_task.py`, `camera_task.py`, `deteccion_test.py`,
`camara_test.py`, `drivers/`, `common/` (con `vision_rojo.py` y `mision.py`) y lo demás de siempre.

0. **Ritmo de la cámara (en el PC):** con el robot publicando, `pip install -r pc/requirements.txt` y
   `cd pc && python calibrar_camara.py 30 --png`. Da `fps`, `jitter_s`, `huecos` y guarda
   `ultima.png`. Si hay huecos o imágenes corruptas, suba `CAMERA_PERIOD_MS` o baje la resolución
   (`CAMERA_SIZE_DIV`: 2 = 160x120, 3 = 80x60).
1. **Detección (sin motores):** `deteccion_test.py`, F5, `ver()`. Con un punto rojo de 1 cm a 10 cm
   debe decir `VISTO` con `area >= 2` y cuánto tardó. Si dice `no veo rojo`, imprime el color del
   píxel más rojo: con eso se ajustan `rojo_r_min` y `rojo_dif_min`. Con `repetir(10)` se mueve el
   punto y `cx`, `cy` deben cambiar.
2. **Geometría:** con el punto a 10 cm, `ver()` da su fila `cy`. Compare la distancia que calcula el
   robot con la real; si no cuadra, revise altura, inclinación y `fov_v`.
3. **Misión completa:** robot en el piso, punto a 10 cm y medidas llenas. En Flet, tarjeta 7,
   **ARRANCAR misión**. Después no se toca nada: mire la cruz verde y el estado. Si algo sale mal,
   **DETENER misión**.
4. **Sin Flet:** también se arranca publicando `{"action": "start"}` en `<PREFIX>mission/cmd`.

Por la Shell del Pico se ve cada vuelta: `Misión: buscando | detección 180 ms | {...}`.

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
