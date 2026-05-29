import json
import os

# ── Calibration ───────────────────────────────────────────────────────────────
# calibration.json est généré par tools/calibrer_roi.py.
# Il contient les coordonnées exactes de la zone des portraits SUR TON ÉCRAN.
# S'il n'existe pas, on utilise les valeurs par défaut (1920x1080 plein écran).
_CALIB_PATH = os.path.join(os.path.dirname(__file__), "calibration.json")

_DEFAULT_ROI     = {"x": 60, "y": 330, "w": 220, "h": 280}
_DEFAULT_MONITOR = None  # None = premier moniteur détecté par mss

if os.path.exists(_CALIB_PATH):
    with open(_CALIB_PATH) as _f:
        _calib = json.load(_f)
    # Coordonnées de la zone à capturer (coin haut-gauche + dimensions en pixels)
    PORTRAITS_ROI    = _calib.get("portraits_roi", _DEFAULT_ROI)
    # Infos du moniteur sélectionné lors de la calibration (multi-écrans)
    MONITOR_OVERRIDE = _calib.get("monitor", _DEFAULT_MONITOR)
else:
    PORTRAITS_ROI    = _DEFAULT_ROI
    MONITOR_OVERRIDE = _DEFAULT_MONITOR

RESOLUTION = (1920, 1080)

# ── Positions des 4 portraits dans la ROI ────────────────────────────────────
# Coordonnées RELATIVES au coin haut-gauche de PORTRAITS_ROI.
# Chaque portrait est un carré de w×h pixels qui contient le cercle du survivant.
# Ces valeurs ont été calibrées manuellement via test_capture.py.
PORTRAIT_POSITIONS = [
    {"x": 24, "y": 24,  "w": 60, "h": 60},   # Survivant 1 (le plus haut)
    {"x": 24, "y": 110, "w": 60, "h": 60},   # Survivant 2
    {"x": 24, "y": 200, "w": 60, "h": 60},   # Survivant 3
    {"x": 24, "y": 290, "w": 60, "h": 60},   # Survivant 4 (le plus bas)
]

# ── Capture ───────────────────────────────────────────────────────────────────
# Nombre de captures d'écran analysées par seconde.
# 10 FPS est suffisant pour détecter les transitions d'état du jeu.
CAPTURE_FPS = 10

# Score minimum pour valider un match de template (0.0 à 1.0).
# Non utilisé en V1.1 (plus de template matching), gardé pour les versions futures.
TEMPLATE_THRESHOLD = 0.80

# ── Durées des timers (en secondes) ──────────────────────────────────────────
TIMER_DECISIVE_STRIKE  = 60  # Coup Décisif : actif 60s après décrochage
TIMER_FARDEAU          = 40  # Fardeau : vulnérabilité de 40s après avoir pris une barre
TIMER_WIGGLE           = 16  # Wiggle : 16s pour se libérer quand porté
TIMER_WIGGLE_BONUS     = 4   # Bonus wiggle si le tueur lâche le survivant (+4s)
TIMER_DEEP_WOUNDS_WINDOW = 15  # Fenêtre post-décrochage : si le tueur frappe dans les 15s → Deep Wounds

# ── Détection Coup Décisif ────────────────────────────────────────────────────
# Si un survivant passe de ACCROCHÉ → BLESSÉ en moins de 1 seconde,
# c'est un décrochage par un coéquipier → Coup Décisif potentiellement actif.
UNHOOK_DETECTION_WINDOW = 1.0

# ── Touches clavier (layout AZERTY français) ─────────────────────────────────
KEY_CANCEL = "²"                        # Annuler la sélection de survivant
KEY_SELECT = ["&", "é", '"', "'"]       # Sélectionner survivant 1 / 2 / 3 / 4
KEY_PERKS  = ["(", "-", "è", "_", "ç", "à"]  # Assigner les 6 perks manuelles

# ── Perks manuelles (V.2.0) ───────────────────────────────────────────────────
# Liste des perks qu'on ne peut pas encore détecter automatiquement.
# L'utilisateur les attribue manuellement via les touches KEY_PERKS.
# L'ordre correspond aux touches : ( = Souplesse, - = Finesse, etc.
MANUAL_PERK_NAMES = [
    "Souplesse",
    "Finesse",
    "Dead Hard",
    "Mine Explosif",
    "Champion de la Lumière",
    "Pièges Chimiques",
]

ASSETS_DIR = "assets/icons"
