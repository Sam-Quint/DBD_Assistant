RESOLUTION = (1920, 1080)

PORTRAITS_ROI = {
    "x": 60,
    "y": 330,
    "w": 220,
    "h": 280
}

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
TIMER_DEEP_WOUNDS_WINDOW = 15  # fenêtre post-décrochage

# Coup Décisif : fenêtre de détection décrochage rapide
UNHOOK_DETECTION_WINDOW = 1.0

# Touches clavier AZERTY
KEY_CANCEL = "²"
KEY_SELECT = ["&", "é", '"', "'"]
KEY_PERKS  = ["(", "-", "è", "_", "ç", "à"]

# Noms des perks manuelles (V.2.0)
MANUAL_PERK_NAMES = [
    "Souplesse",
    "Finesse",
    "Dead Hard",
    "Mine Explosif",
    "Champion de la Lumière",
    "Pièges Chimiques",
]

ASSETS_DIR = "assets/icons"
