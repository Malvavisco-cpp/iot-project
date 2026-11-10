"""Cinemática del MeArm (09_Taller_Arm.ipynb, Partes 1-3). Lógica pura: corre en
CPython y MicroPython (sin ipywidgets, SVG ni la clase Vec del notebook).

Pivotes (nombres del notebook), en dm, con el hombro `a` en el origen:

    a: hombro (servo q1 y servo q2 en el mismo eje)
    d: codo           (a-d brazo,      q1 = ángulo de a->d)
    e: manivela       (a-e manivela,   q2 = ángulo de a->e)
    f: a-e-f-d es un paralelogramo -> el antebrazo d->i es paralelo a e->a
    i: muñeca         (d-i antebrazo)
    j: punta de la pinza
    b, c, g, h: segundo paralelogramo que mantiene la pinza siempre al mismo ángulo

Dos consecuencias que se usan en todo el taller (verificadas con el código del notebook):

  * ángulo absoluto del antebrazo = q2 + 180°  -> el servo q2 mueve el antebrazo DIRECTO
  * la pinza queda siempre a beta2 + beta1 - 180 = 15° respecto a la horizontal

Equivalencia con el gemelo (RoDifArm.js), que usa ángulos absolutos:
    alpha1 = q1          (brazo respecto a la horizontal)
    alpha2 = q2 + 180°   (antebrazo respecto a la horizontal)
"""

import math

# Longitudes del notebook (dm). Las del MeArm real son de este orden (8 cm el brazo).
LINKS = {
    "A": 0.4, "B": 0.8, "C": 0.4, "D": 0.8, "E": 0.35, "F": 0.8, "G": 0.35,
    "H": 0.45, "I": 0.2, "J": 0.8, "K": 0.2, "L": 0.8, "M": 0.25,
}
CONSTANTS = {"beta0_deg": 180.0, "beta1_deg": 90.0, "beta2_deg": 105.0}

# Pares de pivotes unidos por una barra (para dibujar).
BARS = (("a", "b"), ("a", "d"), ("d", "c"), ("c", "b"), ("d", "f"), ("f", "e"), ("a", "e"),
        ("c", "g"), ("d", "g"), ("d", "i"), ("i", "h"), ("g", "h"), ("i", "j"))


def wrap_deg(angle):
    """Ángulo a (-180, 180]."""
    a = (angle + 180.0) % 360.0 - 180.0
    return 180.0 if a == -180.0 else a


def _polar(length, angle_rad, origin=(0.0, 0.0)):
    return origin[0] + length * math.cos(angle_rad), origin[1] + length * math.sin(angle_rad)


def _angle(p, q):
    """Ángulo de la recta p->q (rad). Es `Vec.angle_line` del notebook."""
    return math.atan2(q[1] - p[1], q[0] - p[0])


def law_cos(bc, ac, ab):
    """Ángulo en `a` del triángulo, opuesto al lado bc (ley de cosenos, Parte 1)."""
    c = (ac * ac + ab * ab - bc * bc) / (2 * ac * ab)
    if c < -1.0 - 1e-9 or c > 1.0 + 1e-9:
        raise ValueError("los lados no forman un triángulo")
    return math.acos(max(-1.0, min(1.0, c)))


def solve_third_point(P, Q, d_PR, d_QR):
    """Problema del tercer punto (Parte 1): las dos posiciones de R a d_PR de P y d_QR de Q."""
    dx, dy = Q[0] - P[0], Q[1] - P[1]
    d = math.sqrt(dx * dx + dy * dy)
    if d == 0:
        raise ValueError("P y Q coinciden")
    ux, uy = dx / d, dy / d
    ps = (d_PR * d_PR + d * d - d_QR * d_QR) / (2 * d)
    sr2 = d_PR * d_PR - ps * ps
    if sr2 < -1e-9:
        raise ValueError("no existe el punto: las barras no alcanzan")
    sr = math.sqrt(max(sr2, 0.0))
    sx, sy = P[0] + ux * ps, P[1] + uy * ps
    return (sx - uy * sr, sy + ux * sr), (sx + uy * sr, sy - ux * sr)


def forward(q1_deg, q2_deg, links=LINKS, constants=CONSTANTS):
    """Cinemática directa (Parte 3): ángulos de los servos -> todos los pivotes."""
    L = links
    q1, q2 = math.radians(q1_deg), math.radians(q2_deg)
    a = (0.0, 0.0)
    b = _polar(L["A"], math.radians(constants["beta0_deg"]), a)
    d = _polar(L["B"], q1, a)
    c = solve_third_point(b, d, L["D"], L["C"])[0]
    e = _polar(L["G"], q2, a)
    f = solve_third_point(d, e, L["E"], L["F"])[1]
    g = _polar(L["I"], _angle(c, d) + math.radians(constants["beta1_deg"]), d)
    i = _polar(L["J"], _angle(f, d), d)
    h = solve_third_point(g, i, L["L"], L["K"])[0]
    j = _polar(L["M"], _angle(h, i) + math.radians(constants["beta2_deg"]), i)
    return {"a": a, "b": b, "c": c, "d": d, "e": e, "f": f, "g": g, "h": h, "i": i, "j": j}


def gripper_angle_deg(constants=CONSTANTS):
    """Ángulo fijo de la pinza respecto a la horizontal (15° con las constantes del notebook)."""
    return wrap_deg(constants["beta1_deg"] + constants["beta2_deg"] - 180.0)


def wrist_from_tip(x, y, links=LINKS, constants=CONSTANTS):
    """La pinza siempre apunta igual, así que la muñeca está a un vector fijo de la punta."""
    g = math.radians(gripper_angle_deg(constants))
    return x - links["M"] * math.cos(g), y - links["M"] * math.sin(g)


def inverse(x, y, links=LINKS, constants=CONSTANTS, target="tip"):
    """Cinemática inversa: punto (dm) -> (q1, q2) en grados.

    target="tip": (x, y) es la punta de la pinza (j). target="wrist": la muñeca (i).
    Usa la solución "codo arriba", la única que el MeArm puede hacer.
    Lanza ValueError si el punto está fuera del alcance.
    """
    if target == "tip":
        x, y = wrist_from_tip(x, y, links, constants)
    elif target != "wrist":
        raise ValueError("target debe ser 'tip' o 'wrist'")
    ad, di = links["B"], links["J"]
    ai = math.sqrt(x * x + y * y)
    if ai > ad + di or ai < abs(ad - di) or ai == 0:
        raise ValueError("(%.2f, %.2f) dm está fuera del alcance del brazo" % (x, y))
    q1 = math.atan2(y, x) + law_cos(di, ad, ai)
    d = _polar(ad, q1)
    q2 = _angle(d, (x, y)) + math.pi
    return wrap_deg(math.degrees(q1)), wrap_deg(math.degrees(q2))


# --------------------------------------------------- equivalencia con el gemelo

def twin_from_servos(q1_deg, q2_deg):
    """(q1, q2) del MeArm -> (alpha1, alpha2) del gemelo."""
    return wrap_deg(q1_deg), wrap_deg(q2_deg + 180.0)


def servos_from_twin(alpha1_deg, alpha2_deg):
    """(alpha1, alpha2) del gemelo -> (q1, q2) del MeArm."""
    return wrap_deg(alpha1_deg), wrap_deg(alpha2_deg - 180.0)


def elbow_relative_deg(alpha1_deg, alpha2_deg):
    """Ángulo del antebrazo respecto al brazo. El MeArm solo puede tenerlo negativo
    (codo doblado hacia abajo): en 0 el paralelogramo se aplana y en +x se invierte."""
    return wrap_deg(alpha2_deg - alpha1_deg)


def check_reachable(alpha1_deg, alpha2_deg, min_rel_deg, max_rel_deg):
    rel = elbow_relative_deg(alpha1_deg, alpha2_deg)
    return min_rel_deg <= rel <= max_rel_deg
