"""
Reconnaissance de l'état d'un portrait de survivant par règles (aucun apprentissage).

Ordre de décision :
  1. Griffures (corrélation sur le canal vert avec une référence)  -> "injured"
  2. Pictogramme blanc (à terre, porté, accroché, mort, sorti) : masque blanc recadré,
     comparé à une forme moyenne par état (assets/statuts/templates.npz)
  3. Sinon -> "healthy"

Les formes moyennes sont de simples images moyennes, pas un modèle entraîné.
"""
import os

import cv2
import numpy as np
from PIL import Image, ImageFilter

from core.paths import resource_dir

_ASSETS = os.path.join(resource_dir(), "assets", "statuts")

N = 48                  # taille de travail (px)
SHIFT = 2               # tolérance de décalage de la forme (px)
SCRATCH_FIRST = 0.50    # score de griffures : blessés >= 0.58, tout le reste <= 0.40
# corrélation de forme exigée selon la quantité de blanc pur : (blanc_min, corrélation_min)
SHAPE_RULES = [(195, 0.60), (182, 0.75), (170, 0.90)]

# ── Griffures ────────────────────────────────────────────────────────────────
_S = 40
_THRESHOLD_NORM = 90


def _contrast(image: Image.Image) -> np.ndarray:
    # Le canal vert oppose les traits clairs aux griffures rouges en arrière-plan.
    green = np.asarray(image.convert("RGB").resize((_S, _S), Image.Resampling.BILINEAR),
                       dtype=np.float32)[:, :, 1]
    padded = np.pad(green, ((3, 3), (0, 0)), mode="edge")
    return green - (padded[:-6] + padded[6:]) / 2


class ScratchDetector:
    def __init__(self):
        with Image.open(os.path.join(_ASSETS, "reference.png")) as reference:
            pattern = _contrast(reference)
        y, x = np.mgrid[0:_S, 0:_S]
        strip = (x >= 7) & (x <= 29) & (abs(y + 0.72 * x - 30) < 6)
        self.y, self.x = np.where(strip)
        self.reference = pattern[strip]
        self.reference /= max(np.linalg.norm(self.reference), 1)

    def score(self, image: Image.Image) -> float:
        values = _contrast(image)
        best = 0.0
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                sample = values[self.y + dy, self.x + dx]
                norm = np.linalg.norm(sample)
                if norm > _THRESHOLD_NORM:
                    best = max(best, float(sample @ self.reference / norm))
        return best


# ── Pictogrammes ─────────────────────────────────────────────────────────────

def _white_mask(rgb: np.ndarray) -> np.ndarray:
    """Pixels blancs : canaux tous hauts ET peu saturés (un fond beige/bleu clair n'est pas blanc)."""
    low, high = rgb.min(axis=2), rgb.max(axis=2)
    threshold = max(110.0, 0.75 * np.percentile(low, 99))
    return ((low >= threshold) & (high - low <= 0.30 * high)).astype(np.float32)


def _main_blob(mask: np.ndarray) -> np.ndarray:
    """Garde la plus grosse composante, en écartant le cercle de fil barbelé qui entoure certains pictogrammes."""
    m8 = cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(m8, connectivity=8)
    if count <= 1:
        return mask
    best, best_area = 0, 0
    for i in range(1, count):
        _, _, w, h, area = stats[i]
        if w >= 0.85 * N and h >= 0.85 * N and area / (w * h) < 0.35:
            continue
        if area > best_area:
            best, best_area = i, area
    return mask * (labels == best) if best else mask


def _normalized_shape(mask: np.ndarray) -> np.ndarray:
    """Recadre le masque sur sa boîte englobante (indépendant de l'échelle/position) puis le floute."""
    mask = _main_blob(mask)
    ys, xs = np.nonzero(mask)
    if len(xs) < 8:
        return np.zeros((N, N), dtype=np.float32)
    y0, y1 = np.percentile(ys, [1, 99])
    x0, x1 = np.percentile(xs, [1, 99])
    crop = Image.fromarray((mask * 255).astype(np.uint8)).crop(
        (int(x0) - 1, int(y0) - 1, int(x1) + 2, int(y1) + 2))
    scale = (N - 8) / max(crop.size)
    crop = crop.resize((max(1, round(crop.width * scale)), max(1, round(crop.height * scale))),
                       Image.Resampling.BILINEAR)
    canvas = Image.new("L", (N, N), 0)
    canvas.paste(crop, ((N - crop.width) // 2, (N - crop.height) // 2))
    return np.asarray(canvas.filter(ImageFilter.GaussianBlur(1.5)), dtype=np.float32) / 255


def _shape_score(shape: np.ndarray, template: np.ndarray) -> float:
    """Corrélation centrée entre la forme et le gabarit, maximum sur de petits décalages."""
    m = SHIFT
    core = shape[m:-m, m:-m]
    core = core - core.mean()
    nc = np.linalg.norm(core)
    if nc == 0:
        return 0.0
    best = -1.0
    for dy in range(-m, m + 1):
        for dx in range(-m, m + 1):
            t = template[m + dy:N - m + dy, m + dx:N - m + dx]
            t = t - t.mean()
            denom = nc * np.linalg.norm(t)
            if denom > 0:
                best = max(best, float((core * t).sum() / denom))
    return best


# ── API ──────────────────────────────────────────────────────────────────────

class StatusRecognizer:
    def __init__(self):
        self._scratch = ScratchDetector()
        data = np.load(os.path.join(_ASSETS, "templates.npz"))
        self._shapes = {k[2:]: data[k] for k in data.files if k.startswith("t_")}
        self._status = {k[2:]: str(data[k]) for k in data.files if k.startswith("s_")}

    def classify_bgr(self, roi_bgr: np.ndarray) -> tuple[str, float]:
        """roi_bgr : portrait recadré (BGR, comme renvoyé par mss/OpenCV). Retourne (état, score)."""
        image = Image.fromarray(cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB))
        return self.classify(image)

    def classify(self, image: Image.Image) -> tuple[str, float]:
        scratch = self._scratch.score(image)
        if scratch >= SCRATCH_FIRST:
            return "injured", scratch

        rgb = np.asarray(image.convert("RGB").resize((N, N), Image.Resampling.BILINEAR), dtype=np.float32)
        white = float(np.percentile(rgb.min(axis=2), 99))
        need = next((r for w, r in SHAPE_RULES if white >= w), None)
        if need is not None:
            shape = _normalized_shape(_white_mask(rgb))
            name, best = max(((k, _shape_score(shape, t)) for k, t in self._shapes.items()),
                             key=lambda kv: kv[1])
            if best >= need:
                return self._status[name], best
        return "healthy", scratch
