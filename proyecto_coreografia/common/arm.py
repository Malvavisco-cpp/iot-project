"""Brazo de 3 articulaciones con la misma geometría del gemelo (RoDifArm.js):

    alpha0: giro de la base (horizontal)
    alpha1: hombro
    alpha2: ángulo ABSOLUTO del antebrazo. El gemelo dibuja el codo con
            `elbow.rotation.z = alpha2 - alpha1`, así que el servo del codo
            (montado sobre el brazo) recibe alpha2 - alpha1.
"""


class Arm:

    def __init__(self, base, shoulder, elbow, initial=(0.0, 0.0, 0.0)):
        self.base = base
        self.shoulder = shoulder
        self.elbow = elbow
        self.angles = (0.0, 0.0, 0.0)
        self.set(*initial)

    def set(self, alpha0, alpha1, alpha2):
        self.base.set_angle(alpha0)
        self.shoulder.set_angle(alpha1)
        self.elbow.set_angle(alpha2 - alpha1)
        self.angles = (alpha0, alpha1, alpha2)
