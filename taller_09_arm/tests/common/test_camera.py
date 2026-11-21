import struct
import zlib

import pytest

from common import camera


def test_topic_round_trip():
    assert camera.frame_topic(160, 120) == "camera/frame/rgb565_160x120"
    assert camera.parse_frame_topic("camera/frame/rgb565_160x120") == (160, 120)


def test_the_topic_can_carry_the_robot_prefix():
    assert camera.parse_frame_topic("UDFJC/iot_ws/robot14/camera/frame/rgb565_80x60") == (80, 60)


@pytest.mark.parametrize("bad", [
    "camera/frame/rgb565", "camera/frame/jpeg_160x120", "motion/state", "x/rgb565_160x120", "camera/frame/rgb565_0x120",
])
def test_other_topics_are_rejected(bad):
    with pytest.raises(ValueError):
        camera.parse_frame_topic(bad)


def test_frame_size_matches_the_workshop_numbers():
    assert camera.frame_size(160, 120) == 38400
    assert camera.frame_size(640, 480) == 614400


def test_rgb565_primary_colors():
    # rojo 0xF800, verde 0x07E0, azul 0x001F, blanco 0xFFFF, negro 0
    data = bytes([0xF8, 0x00, 0x07, 0xE0, 0x00, 0x1F, 0xFF, 0xFF, 0x00, 0x00])
    assert camera.rgb565_to_rgb(data) == bytes([
        248, 0, 0,
        0, 252, 0,
        0, 0, 248,
        248, 252, 248,
        0, 0, 0,
    ])


def test_rgb565_needs_whole_pixels():
    with pytest.raises(ValueError):
        camera.rgb565_to_rgb(b"\x00")


def _decode_png(png):
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, size = 8, b"", None
    while pos < len(png):
        (length,) = struct.unpack(">I", png[pos:pos + 4])
        kind, body = png[pos + 4:pos + 8], png[pos + 8:pos + 8 + length]
        (crc,) = struct.unpack(">I", png[pos + 8 + length:pos + 12 + length])
        assert crc == zlib.crc32(kind + body) & 0xFFFFFFFF
        if kind == b"IHDR":
            size = struct.unpack(">II", body[:8])
        elif kind == b"IDAT":
            idat += body
        pos += 12 + length
    return size, zlib.decompress(idat)


def test_png_is_valid_and_keeps_the_pixels():
    rgb = bytes([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])   # 2x2
    size, raw = _decode_png(camera.rgb_to_png(2, 2, rgb))
    assert size == (2, 2)
    assert raw == b"\x00" + rgb[:6] + b"\x00" + rgb[6:]


def test_png_rejects_a_wrong_buffer():
    with pytest.raises(ValueError):
        camera.rgb_to_png(2, 2, b"\x00" * 5)


def test_frame_to_png_checks_the_size_against_the_topic():
    payload = bytes(160 * 120 * 2)
    w, h, png = camera.frame_to_png("camera/frame/rgb565_160x120", payload)
    assert (w, h) == (160, 120)
    assert png.startswith(b"\x89PNG")
    with pytest.raises(ValueError):
        camera.frame_to_png("camera/frame/rgb565_160x120", payload[:-2])
