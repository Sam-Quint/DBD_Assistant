import json
import os

from core.layout import compute_layout

from core.paths import app_dir

# calibration.json est à côté de l'application (racine du projet, ou dossier de l'.exe)
_CALIB_PATH = os.path.join(app_dir(), "calibration.json")

RESOLUTION = (1920, 1080)


def _primary_height() -> int:
    """Hauteur de l'écran principal (1080 si mss est indisponible)."""
    try:
        import mss
        with mss.mss() as sct:
            return sct.monitors[1]["height"]
    except Exception:
        return RESOLUTION[1]


_calib = {}
if os.path.exists(_CALIB_PATH):
    with open(_CALIB_PATH) as _f:
        _calib = json.load(_f)

MONITOR_OVERRIDE = _calib.get("monitor")

if "layout" in _calib:
    # Réglage automatique : positions calculées depuis la résolution (tools/auto_calibrer.py)
    _l = _calib["layout"]
    _layout = compute_layout(_l["height"], _l.get("ui_scale", 1.0), _l.get("dx", 0), _l.get("dy", 0))
    PORTRAITS_ROI      = _layout["roi"]
    PORTRAIT_POSITIONS = _layout["positions"]
elif "portraits_roi" in _calib:
    # Ancien réglage manuel : zone dessinée à la main, positions fixes à l'intérieur
    PORTRAITS_ROI = _calib["portraits_roi"]
    PORTRAIT_POSITIONS = [{"x": 24, "y": y, "w": 60, "h": 60} for y in (24, 110, 200, 290)]
else:
    # Aucun réglage : on suppose le jeu en plein écran sur l'écran principal
    _layout = compute_layout(_primary_height())
    PORTRAITS_ROI      = _layout["roi"]
    PORTRAIT_POSITIONS = _layout["positions"]

# Score minimum pour qu'un template match soit retenu
TEMPLATE_THRESHOLD = 0.80

# Nombre de captures analysées par seconde
CAPTURE_FPS = 10

# Durées des timers (secondes)
TIMER_DECISIVE_STRIKE    = 60
TIMER_FARDEAU            = 40
TIMER_WIGGLE             = 16
TIMER_WIGGLE_BONUS       = 4
TIMER_DEEP_WOUNDS_WINDOW = 15

# Si Accroché → Blessé en moins de 1s → décrochage rapide → Coup Décisif potentiel
UNHOOK_DETECTION_WINDOW = 1.0

# Touches clavier AZERTY
KEY_CANCEL = "²"
KEY_SELECT = ["&", "é", '"', "'"]
KEY_PERKS  = ["(", "-", "è", "_", "ç", "à"]

# Perks assignables manuellement (ordre = ordre des touches KEY_PERKS)
MANUAL_PERK_NAMES = [
    "Souplesse",
    "Finesse",
    "Dead Hard",
    "Mine Explosif",
    "Champion de la Lumière",
    "Pièges Chimiques",
]

