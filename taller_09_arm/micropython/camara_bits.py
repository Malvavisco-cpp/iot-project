"""Encuentra qué pin de DATOS de la cámara está flojo o con ruido (colores verdes/rosados que cambian).

Con las BARRAS DE COLOR de la cámara la imagen es siempre la misma, así que entre una captura y la
siguiente NINGÚN bit debería cambiar. Un pin de datos flojo hace que "su" bit cambie al azar.
Pin D0..D7 = GP(data_0 + 0..7); cada pin lleva el mismo bit en los dos bytes de cada píxel.

Uso (Thonny): abra este archivo y pulse F5, o en la Shell:
    import camara_bits
    camara_bits.medir()          # no toque la cámara ni los cables mientras mide
    camara_bits.medir()          # mueva un cable, repita y compare
"""

import camara_test
import config


def medir(n=4, paso=3):
    pins = config.CAMERA_PINS
    base = pins["data_0"]
    camara_test.iniciar()
    camara_test.barras(True)
    frames = []
    for _ in range(n):
        f = camara_test.capturar()
        if f is None:
            print("No llegó imagen: primero arregle PCLK/HREF/VSYNC (ver mensaje de arriba).")
            return
        frames.append(f)

    cambios = [0] * 8
    unos = [0] * 8
    total = 0
    for a in range(len(frames) - 1):
        x, y = frames[a], frames[a + 1]
        for j in range(0, len(x), paso):
            d = x[j] ^ y[j]
            if d:
                for k in range(8):
                    cambios[k] += (d >> k) & 1
    for f in frames:
        for j in range(0, len(f), paso):
            b = f[j]
            total += 1
            for k in range(8):
                unos[k] += (b >> k) & 1
    pares = (len(frames) - 1) * (len(frames[0]) // paso + 1)

    print("pin   GP   cambia entre capturas   unos      veredicto")
    malos = []
    for k in range(8):
        cam = 100.0 * cambios[k] / pares
        uno = 100.0 * unos[k] / total
        if cam > 1.0:
            v = "FLOJO / CON RUIDO"
            malos.append(k)
        elif uno < 2.0 or uno > 98.0:
            v = "PEGADO en %s (¿cable suelto o en corto?)" % ("0" if uno < 50 else "1")
            malos.append(k)
        else:
            v = "ok"
        print("D%d   GP%-3d %6.1f %%                %5.1f %%   %s" % (k, base + k, cam, uno, v))
    if malos:
        print("\nRevise esos cables/soldaduras: D%s (GP%s). Muévalos y vuelva a correr medir()." % (
            ", D".join(str(k) for k in malos), ", GP".join(str(base + k) for k in malos)))
    else:
        print("\nLos 8 pines de datos están bien. Si el color sigue raro, pruebe PCLK (GP%d), HREF (GP%d) y XCLK (GP%d)"
              " y el GND." % (pins["pclk"], pins["href"], pins["mclk"]))
    camara_test.barras(False)


if __name__ == "__main__":
    medir()
