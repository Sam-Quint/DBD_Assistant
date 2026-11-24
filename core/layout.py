"""
Position des 4 portraits de survivants calculée à partir de la résolution du jeu.

L'interface de Dead by Daylight est dimensionnée selon la HAUTEUR de l'écran et ancrée
au bord gauche : le ratio (16:9, 16:10, 21:9...) ne change donc rien, seule la hauteur
compte. La géométrie de référence est mesurée en 1920x1080 (interface à l'échelle 100 %).

    x_px = x_1080 * hauteur / 1080

Deux réglages fins restent disponibles pour absorber un écart avec la référence
(échelle d'interface différente dans les options du jeu, jeu en fenêtre...) :
    ui_scale : agrandit/réduit taille et espacement autour du 1er portrait
    dx, dy   : décalage en pixels écran
"""

REF_HEIGHT = 1080
REF_CENTER_X = 128      # centre horizontal des portraits (px, en 1080p)
REF_FIRST_Y = 457       # centre vertical du 1er portrait
REF_STEP_Y = 88         # écart vertical entre deux portraits
REF_SIZE = 60           # côté du portrait
MARGIN = 4              # marge de capture autour des portraits (px, en 1080p)

# Résolutions courantes proposées dans l'outil de réglage : libellé -> (largeur, hauteur)
PRESETS = {
    "1920x1080 (16:9)":  (1920, 1080),
    "2560x1440 (16:9)":  (2560, 1440),
    "3840x2160 (16:9)":  (3840, 2160),
    "1920x1200 (16:10)": (1920, 1200),
    "2560x1600 (16:10)": (2560, 1600),
    "2560x1080 (21:9)":  (2560, 1080),
    "3440x1440 (21:9)":  (3440, 1440),
    "1280x720 (16:9)":   (1280, 720),
}


def compute_layout(height: int, ui_scale: float = 1.0, dx: int = 0, dy: int = 0) -> dict:
    """
    Retourne {"roi": {x, y, w, h}, "positions": [{x, y, w, h} * 4]}.
    roi        : zone à capturer (coordonnées écran)
    positions  : portraits, relatifs au coin haut-gauche de la zone
    """
    k = height / REF_HEIGHT
    size = REF_SIZE * k * ui_scale
    step = REF_STEP_Y * k * ui_scale
    cx = REF_CENTER_X * k + dx
    cy0 = REF_FIRST_Y * k + dy

    boxes = []
    for i in range(4):
        boxes.append((round(cx - size / 2), round(cy0 + i * step - size / 2), round(size), round(size)))

    margin = round(MARGIN * k)
    left = max(0, min(b[0] for b in boxes) - margin)
    top = max(0, min(b[1] for b in boxes) - margin)
    right = max(b[0] + b[2] for b in boxes) + margin
    bottom = max(b[1] + b[3] for b in boxes) + margin

    return {
        "roi": {"x": left, "y": top, "w": right - left, "h": bottom - top},
        "positions": [{"x": x - left, "y": y - top, "w": w, "h": h} for x, y, w, h in boxes],
    }
