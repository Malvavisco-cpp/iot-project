"""Dibuja el MeArm (como las figuras del notebook 09) en un archivo SVG.

    python -m tools.mearm_svg --alpha1 67.5 --alpha2 -67.5        # ángulos del gemelo
    python -m tools.mearm_svg --q1 90 --q2 -180                   # ángulos de los servos
    python -m tools.mearm_svg --x 1.2 --y 0.8                     # punta de la pinza (IK)

Abra el .svg en el navegador.
"""

import argparse

from common import config, mearm

WIDTH, HEIGHT = 600, 500
X_MIN, X_MAX, Y_MIN, Y_MAX = -0.8, 2.0, -0.8, 1.6


def to_px(p):
    sx = (p[0] - X_MIN) * WIDTH / (X_MAX - X_MIN)
    sy = HEIGHT - (p[1] - Y_MIN) * HEIGHT / (Y_MAX - Y_MIN)
    return sx, sy


def render(points, title):
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d">' % (WIDTH, HEIGHT),
           '<rect width="100%" height="100%" fill="white"/>']
    ox, oy = to_px((0, 0))
    out.append('<line x1="0" y1="%.1f" x2="%d" y2="%.1f" stroke="green"/>' % (oy, WIDTH, oy))
    out.append('<line x1="%.1f" y1="0" x2="%.1f" y2="%d" stroke="red"/>' % (ox, ox, HEIGHT))
    for p, q in mearm.BARS:
        (x1, y1), (x2, y2) = to_px(points[p]), to_px(points[q])
        color = "steelblue" if (p, q) in (("a", "d"), ("d", "i"), ("i", "j")) else "gray"
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="3"/>'
                   % (x1, y1, x2, y2, color))
    for name, p in points.items():
        x, y = to_px(p)
        out.append('<circle cx="%.1f" cy="%.1f" r="5" fill="black"/>' % (x, y))
        out.append('<text x="%.1f" y="%.1f" font-size="14">%s</text>' % (x + 6, y - 6, name))
    out.append('<text x="10" y="20" font-size="14">%s</text>' % title)
    out.append("</svg>")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="Dibuja el MeArm en SVG")
    parser.add_argument("--q1", type=float)
    parser.add_argument("--q2", type=float)
    parser.add_argument("--alpha1", type=float)
    parser.add_argument("--alpha2", type=float)
    parser.add_argument("--x", type=float, help="punta de la pinza (dm)")
    parser.add_argument("--y", type=float, help="punta de la pinza (dm)")
    parser.add_argument("-o", "--output", default="mearm.svg")
    args = parser.parse_args()

    if args.x is not None and args.y is not None:
        q1, q2 = mearm.inverse(args.x, args.y)
    elif args.alpha1 is not None and args.alpha2 is not None:
        q1, q2 = mearm.servos_from_twin(args.alpha1, args.alpha2)
    elif args.q1 is not None and args.q2 is not None:
        q1, q2 = args.q1, args.q2
    else:
        parser.error("use --q1/--q2, --alpha1/--alpha2 o --x/--y")

    a1, a2 = mearm.twin_from_servos(q1, q2)
    ok = mearm.check_reachable(a1, a2, config.MEARM_MIN_REL_DEG, config.MEARM_MAX_REL_DEG)
    points = mearm.forward(q1, q2)
    tip = points["j"]
    title = "q1=%.1f q2=%.1f | alpha1=%.1f alpha2=%.1f | punta (%.2f, %.2f) dm%s" % (
        q1, q2, a1, a2, tip[0], tip[1], "" if ok else " | FUERA DE RANGO")
    with open(args.output, "w") as f:
        f.write(render(points, title))
    print(title)
    print("->", args.output)


if __name__ == "__main__":
    main()
