# Driver del OLED SH1106 por I2C para MicroPython (128x64, típico de las de 1.3").
#
# Misma interfaz que ssd1306.SSD1306_I2C (es un FrameBuffer: fill, text, rect, ...,
# más show, poweron, poweroff, contrast, invert, rotate). La diferencia con el
# SSD1306 está en cómo se manda la imagen: el SH1106 solo tiene modo de página y su
# memoria es de 132 columnas, con la pantalla visible desplazada 2 columnas. Por eso
# el driver del SSD1306 (modo horizontal) lo deja en negro.

from micropython import const
import framebuf

_SET_CONTRAST = const(0x81)
_SET_NORM_INV = const(0xA6)
_SET_DISP = const(0xAE)
_SET_DISP_START_LINE = const(0x40)
_SET_SEG_REMAP = const(0xA0)
_SET_MUX_RATIO = const(0xA8)
_SET_COM_OUT_DIR = const(0xC0)
_SET_DISP_OFFSET = const(0xD3)
_SET_COM_PIN_CFG = const(0xDA)
_SET_DISP_CLK_DIV = const(0xD5)
_SET_PRECHARGE = const(0xD9)
_SET_VCOM_DESEL = const(0xDB)
_SET_DC_DC = const(0xAD)
_SET_PAGE = const(0xB0)
_COL_OFFSET = const(2)  # la ventana de 128 columnas empieza en la columna 2 de 132


class SH1106_I2C(framebuf.FrameBuffer):
    def __init__(self, width, height, i2c, addr=0x3C, rotate=False):
        self.width = width
        self.height = height
        self.i2c = i2c
        self.addr = addr
        self.pages = height // 8
        self.buffer = bytearray(self.pages * width)
        super().__init__(self.buffer, width, height, framebuf.MONO_VLSB)
        self._init_display()
        self.rotate(rotate)
        self.fill(0)
        self.show()

    def _cmd(self, *cmds):
        for c in cmds:
            self.i2c.writeto(self.addr, bytes((0x00, c)))

    def _init_display(self):
        self._cmd(
            _SET_DISP,
            _SET_DISP_CLK_DIV, 0x80,
            _SET_MUX_RATIO, self.height - 1,
            _SET_DISP_OFFSET, 0x00,
            _SET_DISP_START_LINE | 0x00,
            _SET_DC_DC, 0x8B,  # convertidor interno encendido
            _SET_COM_PIN_CFG, 0x12 if self.height > 32 else 0x02,
            _SET_CONTRAST, 0xCF,
            _SET_PRECHARGE, 0xF1,
            _SET_VCOM_DESEL, 0x40,
            0xA4,  # muestra la memoria
            _SET_NORM_INV,
            _SET_DISP | 0x01,
        )

    def poweroff(self):
        self._cmd(_SET_DISP)

    def poweron(self):
        self._cmd(_SET_DISP | 0x01)

    def contrast(self, contrast):
        self._cmd(_SET_CONTRAST, contrast)

    def invert(self, invert):
        self._cmd(_SET_NORM_INV | (invert & 1))

    def rotate(self, flag=True):
        self._cmd(_SET_SEG_REMAP | (0 if flag else 1), _SET_COM_OUT_DIR | (0 if flag else 8))

    def show(self):
        w = self.width
        for page in range(self.pages):
            self._cmd(_SET_PAGE | page, _COL_OFFSET & 0x0F, 0x10 | (_COL_OFFSET >> 4))
            self.i2c.writeto(self.addr, b"\x40" + self.buffer[page * w:(page + 1) * w])
