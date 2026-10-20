"""Brazo MeArm con los ángulos del gemelo (RoDifArm.js):

    alpha0: giro de la base
    alpha1: brazo respecto a la horizontal          -> servo del hombro (q1)
    alpha2: antebrazo respecto a la horizontal      -> servo del codo  (q2 = alpha2 - 180°)

Por el paralelogramo del MeArm, el servo del codo fija el ángulo ABSOLUTO del
antebrazo (ver common/mearm.py). Por eso aquí el codo recibe alpha2 y no
alpha2 - alpha1 (eso sería un brazo en serie, como el que supone el proyecto de
coreografía).

El MeArm no puede poner el antebrazo por encima de la línea del brazo: si el
estado pide un ángulo relativo fuera de [min_rel, max_rel], el servo del codo se
detiene en el límite (y se avisa una vez). `angles` guarda lo PEDIDO, igual que
el gemelo, para que la interpolación del reproductor siga sincronizada.
"""

from common.mearm import elbow_relative_deg, wrap_deg


class MeArm:

    def __init__(self, base, shoulder, elbow, shoulder_center_deg=90.0, crank_center_deg=-180.0,
                 min_rel_deg=-160.0, max_rel_deg=-20.0, initial=(0.0, 0.0, 0.0)):
        """
        shoulder_center_deg: alpha1 con el servo del hombro centrado (90 = brazo vertical).
        crank_center_deg:    q2 con el servo del codo centrado (-180 = manivela hacia atrás,
                             o sea antebrazo horizontal; así el servo recibe alpha2 directo).
        """
        self.base = base
        self.shoulder = shoulder
        self.elbow = elbow
        self.shoulder_center_deg = shoulder_center_deg
        self.crank_center_deg = crank_center_deg
        self.min_rel_deg = min_rel_deg
        self.max_rel_deg = max_rel_deg
        self.angles = (0.0, 0.0, 0.0)
        self.limited = False
        self.set(*initial)

    def physical_alpha2(self, alpha1, alpha2):
        """alpha2 dentro de lo que el mecanismo permite para ese alpha1."""
        rel = elbow_relative_deg(alpha1, alpha2)
        if rel > self.max_rel_deg:
            return alpha1 + self.max_rel_deg
        if rel < self.min_rel_deg:
            return alpha1 + self.min_rel_deg
        return alpha2

    def set(self, alpha0, alpha1, alpha2):
        real_alpha2 = self.physical_alpha2(alpha1, alpha2)
        limited = real_alpha2 != alpha2
        if limited and not self.limited:
            print("MeArm: el codo no llega a %.0f° con el brazo en %.0f°; se queda en %.0f°"
                  % (alpha2, alpha1, real_alpha2))
        self.limited = limited

        q2 = real_alpha2 - 180.0
        self.base.set_angle(alpha0)
        self.shoulder.set_angle(alpha1 - self.shoulder_center_deg)
        self.elbow.set_angle(wrap_deg(q2 - self.crank_center_deg))
        self.angles = (alpha0, alpha1, alpha2)
