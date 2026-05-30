import json
import os

# calibration.json est à la racine du projet (un niveau au-dessus de core/)
_CALIB_PATH = os.path.join(os.path.dirname(__file__), "..", "calibration.json")

_DEFAULT_ROI     = {"x": 60, "y": 330, "w": 220, "h": 280}
_DEFAULT_MONITOR = None  # None = premier moniteur détecté par mss

if os.path.exists(_CALIB_PATH):
    with open(_CALIB_PATH) as _f:
        _calib = json.load(_f)
    PORTRAITS_ROI    = _calib.get("portraits_roi", _DEFAULT_ROI)
    MONITOR_OVERRIDE = _calib.get("monitor", _DEFAULT_MONITOR)
else:
    PORTRAITS_ROI    = _DEFAULT_ROI
    MONITOR_OVERRIDE = _DEFAULT_MONITOR

RESOLUTION = (1920, 1080)

# Coordonnées des 4 portraits dans la ROI (relatif au coin haut-gauche de PORTRAITS_ROI)
PORTRAIT_POSITIONS = [
    {"x": 24, "y": 24,  "w": 60, "h": 60},   # Survivant 1
    {"x": 24, "y": 110, "w": 60, "h": 60},   # Survivant 2
    {"x": 24, "y": 200, "w": 60, "h": 60},   # Survivant 3
    {"x": 24, "y": 290, "w": 60, "h": 60},   # Survivant 4
]

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

