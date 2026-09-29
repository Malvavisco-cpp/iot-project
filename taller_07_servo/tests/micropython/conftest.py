"""micropython/pwm_out.py no importa `machine` ni `rp2` (recibe el pin PWM ya
construido), así que no hace falta doblar hardware: solo agregar micropython/
al sys.path para poder hacer `import pwm_out` como lo hace main.py en el Pico.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "micropython"))
