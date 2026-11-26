"""Cámara OV7670 (taller 12): nombres de tópico y conversión de las imágenes. Lógica pura.

El Pico publica cada imagen en bruto (RGB565, 2 bytes por píxel, byte alto primero) en

    camera/frame/rgb565_<ancho>x<alto>          p. ej. camera/frame/rgb565_160x120

y el tamaño va en el nombre del tópico: quien recibe necesita saberlo para armar la
imagen. Aquí vive todo lo que no toca hardware, para probarlo en el PC.
"""

TOPIC_FRAME_PREFIX = "camera/frame/"
TOPIC_FRAME_FILTER = "camera/frame/+"   # se escucha este: sirve para cualquier resolución
FORMAT = "rgb565"

# `re`, `struct` y `zlib` se importan dentro de las funciones que los usan: el Pico solo
# necesita frame_topic() y frame_size(), y en MicroPython zlib puede no estar disponible.


def frame_topic(width, height):
    return "%s%s_%dx%d" % (TOPIC_FRAME_PREFIX, FORMAT, width, height)


def frame_size(width, height):
    """Bytes de una imagen RGB565."""
    return width * height * 2


def parse_frame_topic(topic):
    """'.../camera/frame/rgb565_160x120' -> (160, 120). ValueError si no es un tópico de imagen."""
    import re

    match = re.search(r"rgb565_(\d+)x(\d+)$", topic)
    if match is None or TOPIC_FRAME_PREFIX not in topic:
        raise ValueError("no es un tópico de imagen: %s" % topic)
    width, height = int(match.group(1)), int(match.group(2))
    if width <= 0 or height <= 0:
        raise ValueError("tamaño inválido en el tópico: %s" % topic)
    return width, height


def rgb565_to_rgb(data):
    """RGB565 (byte alto primero) -> RGB de 3 bytes por píxel.

    Misma conversión que PubSub_client_web.html: r = 5 bits << 3, g = 6 bits << 2, b = 5 bits << 3.
    """
    if len(data) % 2:
        raise ValueError("RGB565 necesita un número par de bytes")
    out = bytearray(len(data) // 2 * 3)
    j = 0
    for i in range(0, len(data), 2):
        value = (data[i] << 8) | data[i + 1]
        out[j] = ((value >> 11) & 0x1F) << 3
        out[j + 1] = ((value >> 5) & 0x3F) << 2
        out[j + 2] = (value & 0x1F) << 3
        j += 3
    return bytes(out)


def _chunk(kind, body):
    import struct
    import zlib

    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)


def rgb_to_png(width, height, rgb):
    """RGB (3 bytes por píxel) -> archivo PNG en bytes, sin librerías externas."""
    import struct
    import zlib

    if len(rgb) != width * height * 3:
        raise ValueError("se esperaban %d bytes de RGB y llegaron %d" % (width * height * 3, len(rgb)))
    row = width * 3
    raw = b"".join(b"\x00" + rgb[y * row:(y + 1) * row] for y in range(height))  # filtro 0 en cada fila
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(raw))
        + _chunk(b"IEND", b"")
    )


def draw_cross(rgb, width, height, cx, cy, size=5, color=(0, 255, 0)):
    """Dibuja una cruz de brazos `size` centrada en (cx, cy) sobre una imagen RGB (bytearray)."""
    cx, cy = int(round(cx)), int(round(cy))
    for d in range(-size, size + 1):
        for x, y in ((cx + d, cy), (cx, cy + d)):
            if 0 <= x < width and 0 <= y < height:
                i = (y * width + x) * 3
                rgb[i:i + 3] = bytes(color)


def frame_to_png(topic, payload, marca=None):
    """Mensaje MQTT de imagen -> (ancho, alto, PNG). ValueError si el tamaño no cuadra.
    `marca` = (cx, cy) dibuja una cruz verde en el punto que el robot detectó."""
    width, height = parse_frame_topic(topic)
    if len(payload) != frame_size(width, height):
        raise ValueError("la imagen trae %d bytes y el tópico dice %dx%d (%d)"
                         % (len(payload), width, height, frame_size(width, height)))
    rgb = rgb565_to_rgb(payload)
    if marca is not None:
        draw_cross(rgb, width, height, marca[0], marca[1])
    return width, height, rgb_to_png(width, height, rgb)
