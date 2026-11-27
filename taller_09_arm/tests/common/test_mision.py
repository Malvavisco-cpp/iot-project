import math

from common import mision, vision_rojo
from common.mision import BRAZO, BUSCANDO, FALLO, LISTO, Mision

W, H = 160, 120

GEOM = {
    "cam_altura_m": 0.10, "cam_inclinacion_deg": 40.0, "fov_v_deg": 40.0, "fov_h_deg": 50.0,
    "punta_dist_m": 0.12,
    "w_giro_deg_s": 30.0, "v_dm_s": 1.0, "avance_max_m": 0.15,
    "tol_err_x": 0.08, "tol_dist_m": 0.01, "ciego_m": 0.03,
    "barrido_deg": 25.0, "barrido_max": 14, "max_iter": 12, "settle_ms": 600,
    "brazo_abajo": (0.0, 0.0, -90.0), "brazo_t_s": 2.0,
    "rojo_r_min": 110, "rojo_dif_min": 60, "area_min": 2,
}


def rgb565(r, g, b):
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


def imagen(cx=None, cy=None, lado=3, color=(255, 0, 0), fondo=(200, 200, 200)):
    px = [rgb565(*fondo)] * (W * H)
    if cx is not None:
        for y in range(int(cy), int(cy) + lado):
            for x in range(int(cx), int(cx) + lado):
                px[y * W + x] = rgb565(*color)
    out = bytearray()
    for v in px:
        out += bytes((v >> 8, v & 0xFF))
    return out


# --------------------------------------------------------------------- detección

def test_detecta_punto_rojo():
    det = vision_rojo.detectar_rojo(imagen(100, 40), W, H)
    assert abs(det["cx"] - 101) < 0.6 and abs(det["cy"] - 41) < 0.6
    assert det["area"] == 9
    assert det["err_x"] > 0.2 and det["err_y"] < 0


def test_sin_rojo():
    assert vision_rojo.detectar_rojo(imagen(), W, H) is None
    assert vision_rojo.detectar_rojo(imagen(20, 20, color=(0, 0, 255)), W, H) is None


def test_ruido_suelto_no_corre_el_centro():
    img = imagen(100, 40, lado=4)
    # un píxel rojo suelto lejos: sin el filtro por radio movería el centro hacia él
    v = rgb565(255, 0, 0)
    i = (110 * W + 5) * 2
    img[i], img[i + 1] = v >> 8, v & 0xFF
    det = vision_rojo.detectar_rojo(img, W, H)
    assert abs(det["cx"] - 101.5) < 1.0


def test_naranja_y_rosa_no_cuentan():
    assert vision_rojo.detectar_rojo(imagen(50, 50, color=(255, 160, 0)), W, H) is None   # naranja
    assert vision_rojo.detectar_rojo(imagen(50, 50, color=(255, 150, 160)), W, H) is None  # rosa claro


# --------------------------------------------------------------------- geometría

def test_distancia_en_el_eje():
    # Cámara a 0,2 m mirando 45° abajo: el centro de la imagen cae a 0,2 m.
    assert abs(mision.distancia_al_piso(60, 120, 0.2, 45.0, 40.0) - 0.2) < 1e-9
    assert mision.distancia_al_piso(0, 120, 0.2, 0.0, 40.0) is None   # mira por encima del piso


def test_mas_abajo_en_la_imagen_es_mas_cerca():
    lejos = mision.distancia_al_piso(30, H, 0.1, 40.0, 40.0)
    cerca = mision.distancia_al_piso(90, H, 0.1, 40.0, 40.0)
    assert cerca < lejos


def test_angulo_horizontal():
    assert mision.angulo_horizontal(0.0, 50.0) == 0.0
    assert abs(mision.angulo_horizontal(1.0, 50.0) - 25.0) < 1e-9   # borde derecho = FOV/2
    assert mision.angulo_horizontal(-0.5, 50.0) < 0


# --------------------------------------------------------------------- máquina de estados

def test_no_arranca_sin_medidas():
    p = dict(GEOM, cam_altura_m=None, fov_h_deg=None)
    m = Mision(p)
    motivo = m.start()
    assert "cam_altura_m" in motivo and "fov_h_deg" in motivo
    assert m.fase == FALLO and not m.corriendo
    assert m.decidir(None, W, H) is None


def test_punto_a_la_derecha_gira_a_la_derecha():
    m = Mision(GEOM)
    assert m.start() is None
    det = vision_rojo.detectar_rojo(imagen(130, 50), W, H)
    estados = m.decidir(det, W, H)
    assert len(estados) == 1 and estados[0]["v_dm/s"] == 0
    assert estados[0]["w_deg/s"] < 0                      # w > 0 es izquierda: derecha es negativo
    assert estados[0]["duration_s"] > 0.1


def test_punto_a_la_izquierda_gira_a_la_izquierda():
    m = Mision(GEOM)
    m.start()
    estados = m.decidir(vision_rojo.detectar_rojo(imagen(10, 50), W, H), W, H)
    assert estados[0]["w_deg/s"] > 0


def test_centrado_y_lejos_avanza_sin_pasarse():
    m = Mision(GEOM)
    m.start()
    det = {"cx": 80.0, "cy": 30.0, "area": 9, "err_x": 0.0, "err_y": 0.0}
    estados = m.decidir(det, W, H)
    dist = mision.distancia_al_piso(30, H, 0.10, 40.0, 40.0)
    falta = dist - GEOM["punta_dist_m"]
    esperado = min(falta, GEOM["avance_max_m"], max(0.03, falta * 0.6))
    assert estados[0]["w_deg/s"] == 0 and estados[0]["v_dm/s"] == 1.0
    assert abs(estados[0]["duration_s"] - esperado * 10.0) < 1e-6


def test_ya_en_posicion_baja_el_brazo_y_termina():
    dist = mision.distancia_al_piso(60, H, 0.10, 40.0, 40.0)
    p = dict(GEOM, punta_dist_m=dist - 0.005)      # falta 5 mm: dentro de la tolerancia (1 cm)
    m = Mision(p)
    m.start()
    det = {"cx": 80.0, "cy": 60.0, "area": 9, "err_x": 0.0, "err_y": 0.0}
    estados = m.decidir(det, W, H)
    assert m.fase == BRAZO
    assert (estados[0]["alpha1_deg"], estados[0]["alpha2_deg"]) == (0.0, -90.0)
    assert estados[0]["v_dm/s"] == 0 and estados[0]["duration_s"] == 2.0
    assert m.decidir(det, W, H) is None      # al terminar el brazo
    assert m.fase == LISTO


def test_sin_ver_el_punto_hace_barrido_y_se_rinde():
    m = Mision(GEOM)
    m.start()
    for _ in range(GEOM["barrido_max"]):
        estados = m.decidir(None, W, H)
        assert estados[0]["v_dm/s"] == 0 and estados[0]["w_deg/s"] != 0
    assert m.decidir(None, W, H) is None
    assert m.fase == FALLO and "no encuentro" in m.motivo


def test_pierde_el_punto_justo_al_llegar_baja_el_brazo():
    m = Mision(GEOM)
    m.start()
    m.resto_m = 0.0          # el último avance cerró toda la distancia
    estados = m.decidir(None, W, H)
    assert m.fase == BRAZO and estados[0]["alpha2_deg"] == -90.0


def test_tope_de_intentos():
    m = Mision(dict(GEOM, max_iter=3))
    m.start()
    lejos = {"cx": 80.0, "cy": 30.0, "area": 9, "err_x": 0.0, "err_y": 0.0}
    for _ in range(3):
        assert m.decidir(lejos, W, H) is not None
    m.decidir(lejos, W, H)
    assert m.fase == FALLO and "intentos" in m.motivo


def test_rojo_sobre_el_horizonte_se_ignora_y_sigue_buscando():
    m = Mision(dict(GEOM, cam_inclinacion_deg=0.0))
    m.start()
    det = {"cx": 80.0, "cy": 5.0, "area": 9, "err_x": 0.0, "err_y": -0.9}
    est = m.decidir(det, W, H)
    assert m.fase == BUSCANDO and est[0]["v_dm/s"] == 0 and m.iter == 0
    assert m.ultima["ignorado"] == "sobre el horizonte"


def test_simulacion_completa_llega_y_baja_el_brazo():
    """Punto a 0,10 m delante y 3 cm a un lado; el carro obedece los estados al pie de la letra."""
    m = Mision(GEOM)
    m.start()
    x, y, rumbo = 0.0, 0.0, 0.0          # carro en el origen, mirando +x (rumbo en grados, + = izquierda)
    objetivo = (0.18, -0.03)
    cam = (0.0, 0.0)

    def ve():
        dx, dy = objetivo[0] - x, objetivo[1] - y
        r = math.radians(-rumbo)
        fx, fy = dx * math.cos(r) - dy * math.sin(r), dx * math.sin(r) + dy * math.cos(r)  # x adelante, y a la izq
        if fx <= 0.01:
            return None
        ang = math.degrees(math.atan2(-fy, fx))         # + = derecha
        if abs(ang) > GEOM["fov_h_deg"] / 2 - 1:
            return None
        err_x = math.tan(math.radians(ang)) / math.tan(math.radians(GEOM["fov_h_deg"] / 2))
        # fila del punto: inversa de distancia_al_piso
        f = (H / 2) / math.tan(math.radians(GEOM["fov_v_deg"] / 2))
        bajada = math.atan2(GEOM["cam_altura_m"], fx)
        cy = H / 2 + f * math.tan(bajada - math.radians(GEOM["cam_inclinacion_deg"]))
        if not 0 <= cy < H:
            return None
        return {"cx": W / 2 + err_x * W / 2, "cy": cy, "area": 9, "err_x": err_x, "err_y": 0.0}

    for _ in range(40):
        estados = m.decidir(ve(), W, H)
        if estados is None:
            if m.fase in (LISTO, FALLO):
                break
            continue
        for s in estados:
            t = s["duration_s"]
            rumbo += s["w_deg/s"] * t
            avance = s["v_dm/s"] / 10.0 * t
            x += avance * math.cos(math.radians(rumbo))
            y += avance * math.sin(math.radians(rumbo))
    assert m.fase in (LISTO, BRAZO), m.estado()
    llegada = math.hypot(objetivo[0] - x, objetivo[1] - y)
    assert abs(llegada - GEOM["punta_dist_m"]) < 0.03, llegada


def test_unidades_raras_no_arrancan():
    m = Mision(dict(GEOM, fov_h_deg=0.9, cam_altura_m=8.0))     # radianes en vez de grados, cm en vez de m
    motivo = m.start()
    assert m.fase == FALLO and "fov_h_deg" in motivo and "cam_altura_m" in motivo


def test_fallo_por_horizonte_dice_los_grados():
    m = Mision(dict(GEOM, cam_inclinacion_deg=2.0))
    m.start()
    det = {"cx": 119.6, "cy": 33.2, "area": 9, "err_x": 0.495, "err_y": -0.45}
    for _ in range(GEOM["barrido_max"]):
        assert m.decidir(det, W, H) is not None
    assert m.decidir(det, W, H) is None
    assert m.fase == FALLO and "por encima del horizonte" in m.motivo and "cam_inclinacion_deg" in m.motivo


def test_si_el_punto_esta_mas_cerca_que_la_punta_retrocede():
    dist = mision.distancia_al_piso(60, H, 0.10, 40.0, 40.0)
    m = Mision(dict(GEOM, punta_dist_m=dist + 0.05))     # la punta llega 5 cm más lejos que el punto
    m.start()
    det = {"cx": 80.0, "cy": 60.0, "area": 9, "err_x": 0.0, "err_y": 0.0}
    estados = m.decidir(det, W, H)
    assert estados[0]["v_dm/s"] < 0 and abs(estados[0]["duration_s"] - 0.5) < 1e-6   # 5 cm a 1 dm/s
    assert m.fase == BUSCANDO


def test_sin_reversa_baja_el_brazo_aunque_se_pase():
    dist = mision.distancia_al_piso(60, H, 0.10, 40.0, 40.0)
    m = Mision(dict(GEOM, punta_dist_m=dist + 0.05, reversa=False))
    m.start()
    det = {"cx": 80.0, "cy": 60.0, "area": 9, "err_x": 0.0, "err_y": 0.0}
    m.decidir(det, W, H)
    assert m.fase == BRAZO


def test_giro_pivote_deja_una_rueda_quieta():
    m = Mision(dict(GEOM, giro_pivote=True, semiancho_m=0.065, w_giro_deg_s=90.0))
    g = m._giro(20.0)                        # punto a la derecha -> w < 0
    assert g["w_deg/s"] == -90.0
    v = g["v_dm/s"] / 10.0
    w = math.radians(g["w_deg/s"])
    assert abs((v + w * 0.065)) < 1e-3       # rueda derecha quieta
    assert abs((v - w * 0.065) - 0.2) < 1e-2  # rueda izquierda a 0,2 m/s
    assert abs(g["duration_s"] - 20.0 / 90.0) < 1e-6
    assert Mision(GEOM)._giro(20.0)["v_dm/s"] == 0      # sin el parámetro, gira en el sitio


def test_giro_gain_alarga_el_giro():
    m = Mision(dict(GEOM, w_giro_deg_s=90.0, giro_gain=1.6))
    assert abs(m._giro(9.0)["duration_s"] - 9.0 * 1.6 / 90.0) < 1e-6


def test_si_lo_pierde_justo_despues_de_avanzar_retrocede():
    m = Mision(dict(GEOM, ciego_m=0.0))      # sin zona ciega: aísla el caso
    m.start()
    det = {"cx": 80.0, "cy": 30.0, "area": 9, "err_x": 0.0, "err_y": 0.0}
    avance = m.decidir(det, W, H)[0]
    assert avance["v_dm/s"] > 0
    vuelta = m.decidir(None, W, H)
    assert vuelta[0]["v_dm/s"] < 0 and m.barridos == 0           # retrocede, no barre
    assert abs(vuelta[0]["duration_s"] - avance["duration_s"] * 0.5) < 1e-6
    assert m.decidir(None, W, H)[0]["v_dm/s"] == 0               # si sigue sin verlo, ahí sí barre
