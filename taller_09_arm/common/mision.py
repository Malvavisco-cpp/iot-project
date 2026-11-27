"""Misión autónoma: ir al punto rojo y bajar el brazo sobre él. Lógica pura (sin hardware).

El robot repite: mirar -> (girar | avanzar | bajar el brazo). Cada paso es una lista de
estados de MotionPlayer (los mismos de motion/state), así el carro se mueve exactamente
como en las coreografías. Quien la use llama a `decidir()` solo cuando el robot está
quieto y la imagen es nueva.

Fases: IDLE -> BUSCANDO -> BRAZO -> LISTO   (o FALLO con un motivo)
"""

import math

TOPIC_CMD = "mission/cmd"          # Flet -> robot: {"action": "start" | "stop"}
TOPIC_STATUS = "mission/status"    # robot -> Flet: fase y lo que ve

IDLE = "idle"
BUSCANDO = "buscando"
BRAZO = "brazo"
LISTO = "listo"
FALLO = "fallo"

_OBLIGATORIAS = ("cam_altura_m", "cam_inclinacion_deg", "fov_v_deg", "fov_h_deg", "punta_dist_m")


# Rangos razonables: atrapan unidades equivocadas (cm en vez de m, radianes en vez de grados).
_RANGOS = {
    "cam_altura_m": (0.01, 1.0, "m"),
    "cam_inclinacion_deg": (-20.0, 90.0, "grados"),
    "fov_v_deg": (15.0, 140.0, "grados"),
    "fov_h_deg": (15.0, 140.0, "grados"),
    "punta_dist_m": (0.01, 0.5, "m"),
}


def medidas_raras(p):
    """Medidas llenas pero con pinta de unidad equivocada. -> lista de textos."""
    raras = []
    for k, (lo, hi, unidad) in _RANGOS.items():
        v = p.get(k)
        if v is not None and not lo <= v <= hi:
            raras.append("%s=%s (esperaba entre %s y %s %s)" % (k, v, lo, hi, unidad))
    return raras


def bajada_deg(cy, alto, inclinacion_deg, fov_v_deg):
    """Cuántos grados BAJO la horizontal apunta el rayo de la fila `cy` (negativo = hacia arriba)."""
    f = (alto / 2) / math.tan(math.radians(fov_v_deg) / 2)
    return inclinacion_deg + math.degrees(math.atan((cy - alto / 2) / f))


def build_cmd(action):
    return {"action": action}


def faltan_medidas(p):
    """Nombres de las medidas que siguen sin llenar (None o <= 0)."""
    return [k for k in _OBLIGATORIAS if p.get(k) is None or p[k] <= 0 and k != "cam_inclinacion_deg"]


def distancia_al_piso(cy, alto, altura_m, inclinacion_deg, fov_v_deg):
    """Distancia horizontal (m) de la cámara al punto del piso visto en la fila `cy`.

    La cámara está a `altura_m` mirando `inclinacion_deg` hacia abajo; el rayo del píxel
    baja inclinación + atan((cy - alto/2) / f), con f la distancia focal en píxeles.
    None si el rayo no baja (mira por encima del piso).
    """
    f = (alto / 2) / math.tan(math.radians(fov_v_deg) / 2)
    bajada = math.radians(inclinacion_deg) + math.atan((cy - alto / 2) / f)
    if bajada <= 0:
        return None
    return altura_m / math.tan(bajada)


def angulo_horizontal(err_x, fov_h_deg):
    """Ángulo (grados) al que está el punto: + = a la derecha del eje de la cámara."""
    return math.degrees(math.atan(err_x * math.tan(math.radians(fov_h_deg) / 2)))


class Mision:

    def __init__(self, params):
        self.p = params
        self.fase = IDLE
        self.motivo = ""
        self.iter = 0
        self.barridos = 0
        self.resto_m = None      # lo que quedaba por avanzar tras el último avance
        self.ultima = {}         # lo último que se vio (para el estado que se publica)

    # ---------------------------------------------------------------- control

    def start(self):
        """-> None si arranca, o el texto de por qué no."""
        falta = faltan_medidas(self.p)
        if falta:
            self.fase, self.motivo = FALLO, "faltan medidas: " + ", ".join(falta)
            return self.motivo
        raras = medidas_raras(self.p)
        if raras:
            self.fase, self.motivo = FALLO, "medidas con unidad rara: " + "; ".join(raras)
            return self.motivo
        self.fase, self.motivo = BUSCANDO, ""
        self.iter = self.barridos = 0
        self.sobre_horizonte = ""
        self.resto_m = None
        self.ultima = {}
        return None

    def stop(self):
        self.fase, self.motivo = IDLE, ""

    @property
    def corriendo(self):
        return self.fase in (BUSCANDO, BRAZO)

    def estado(self):
        e = {"fase": self.fase, "iter": self.iter, "motivo": self.motivo}
        e.update(self.ultima)
        return e

    # ---------------------------------------------------------------- decisión

    def decidir(self, det, ancho, alto):
        """Con la detección de una imagen nueva, devuelve la lista de estados a ejecutar
        (o None si no hay que mover nada). `det` es el dict de detectar_rojo() o None."""
        if self.fase == BRAZO:      # el brazo ya terminó de bajar
            self.fase = LISTO
            return None
        if self.fase != BUSCANDO:
            return None

        if det is None:
            self.ultima = {"visto": False}
            if self.resto_m is not None and self.resto_m <= self.p["ciego_m"]:
                return self._bajar_brazo()      # lo perdió de vista justo al llegar
            self.barridos += 1
            if self.barridos > self.p["barrido_max"]:
                return self._fallo("no encuentro el punto rojo")
            return [self._giro(-self.p["barrido_deg"])]     # + grados = derecha -> se gira a la izquierda

        p = self.p
        ang = angulo_horizontal(det["err_x"], p["fov_h_deg"])
        dist = distancia_al_piso(det["cy"], alto, p["cam_altura_m"], p["cam_inclinacion_deg"], p["fov_v_deg"])
        if dist is None:
            # Por encima del horizonte no hay piso: es otra cosa roja (fondo, reflejo) o la inclinación
            # está mal medida. No se rinde: la ignora y sigue buscando; si nunca ve otra cosa, lo dice.
            b = bajada_deg(det["cy"], alto, p["cam_inclinacion_deg"], p["fov_v_deg"])
            self.sobre_horizonte = "fila %d queda %.1f grados por encima del horizonte" % (det["cy"], -b)
            self.ultima = {"visto": False, "ignorado": "sobre el horizonte", "cy": round(det["cy"], 1),
                           "cx": round(det["cx"], 1)}
            self.barridos += 1
            if self.barridos > p["barrido_max"]:
                return self._fallo(
                    "solo veo rojo por encima del horizonte (%s; inclinación %.1f, fov_v %.1f): o es algo del "
                    "fondo, o cam_inclinacion_deg/fov_v_deg están mal (¿hacia abajo y en grados?)"
                    % (self.sobre_horizonte, p["cam_inclinacion_deg"], p["fov_v_deg"]))
            return [self._giro(-p["barrido_deg"])]

        self.iter += 1      # los intentos son las veces que lo VE en el piso y corrige; el barrido va aparte
        if self.iter > p["max_iter"]:
            return self._fallo("no logré llegar en %d intentos" % p["max_iter"])
        self.ultima = {"visto": True, "cx": round(det["cx"], 1), "cy": round(det["cy"], 1),
                       "err_x": round(det["err_x"], 3), "ang_deg": round(ang, 1),
                       "dist_m": round(dist, 3)}
        self.barridos = 0

        if abs(det["err_x"]) > p["tol_err_x"]:
            self.resto_m = None
            return [self._giro(ang)]
        falta = dist - p["punta_dist_m"]       # > 0: falta avanzar; < 0: la punta del lápiz ya se pasó
        if abs(falta) <= p["tol_dist_m"] or (falta < 0 and not p.get("reversa", True)):
            return self._bajar_brazo()
        paso = min(abs(falta), p["avance_max_m"])
        self.resto_m = abs(falta) - paso
        return [self._avance(paso if falta > 0 else -paso)]

    # ---------------------------------------------------------------- pasos

    def _giro(self, ang_deg):
        """Giro en el sitio. ang_deg > 0 = el punto está a la derecha -> el carro gira a la derecha (w < 0)."""
        w = self.p["w_giro_deg_s"]
        return {"v_dm/s": 0, "w_deg/s": -w if ang_deg > 0 else w, "duration_s": max(0.05, abs(ang_deg) / w)}

    def _avance(self, metros):
        """metros > 0 avanza, metros < 0 retrocede."""
        v = self.p["v_dm_s"]
        return {"v_dm/s": v if metros >= 0 else -v, "w_deg/s": 0, "duration_s": max(0.05, abs(metros) * 10.0 / v)}

    def _bajar_brazo(self):
        a0, a1, a2 = self.p["brazo_abajo"]
        self.fase = BRAZO
        return [{"v_dm/s": 0, "w_deg/s": 0, "alpha0_deg": a0, "alpha1_deg": a1, "alpha2_deg": a2,
                 "duration_s": self.p["brazo_t_s"]}]

    def _fallo(self, motivo):
        self.fase, self.motivo = FALLO, motivo
        return None
