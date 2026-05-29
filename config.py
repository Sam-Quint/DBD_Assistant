import json
import os

# Valeurs par défaut (1920x1080 fullscreen)
_DEFAULT_ROI = {"x": 60, "y": 330, "w": 220, "h": 280}

# Chargement depuis calibration.json si présent
_CALIB_PATH = os.path.join(os.path.dirname(__file__), "calibration.json")
if os.path.exists(_CALIB_PATH):
    with open(_CALIB_PATH) as _f:
        _calib = json.load(_f)
    PORTRAITS_ROI = _calib.get("portraits_roi", _DEFAULT_ROI)
else:
    PORTRAITS_ROI = _DEFAULT_ROI

RESOLUTION = (1920, 1080)

# Position de chaque portrait dans la ROI (relatif à la ROI)
PORTRAIT_POSITIONS = [
    {"x": 0, "y": 0,   "w": 55, "h": 55},
    {"x": 0, "y": 70,  "w": 55, "h": 55},
    {"x": 0, "y": 140, "w": 55, "h": 55},
    {"x": 0, "y": 210, "w": 55, "h": 55},
]

CAPTURE_FPS = 10

TEMPLATE_THRESHOLD = 0.80

# Durées des timers (secondes)
TIMER_DECISIVE_STRIKE = 60
TIMER_FARDEAU = 40
TIMER_WIGGLE = 16
TIMER_WIGGLE_BONUS = 4
TIMER_DEEP_WOUNDS_WINDOW = 15

UNHOOK_DETECTION_WINDOW = 1.0

# Touches clavier AZERTY
KEY_CANCEL = "²"
KEY_SELECT = ["&", "é", '"', "'"]
KEY_PERKS  = ["(", "-", "è", "_", "ç", "à"]

MANUAL_PERK_NAMES = [
    "Souplesse",
    "Finesse",
    "Dead Hard",
    "Mine Explosif",
    "Champion de la Lumière",
    "Pièges Chimiques",
]

ASSETS_DIR = "assets/icons"
