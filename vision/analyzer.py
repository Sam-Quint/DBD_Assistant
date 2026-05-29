import cv2
import numpy as np
from core.config import PORTRAIT_POSITIONS
from core.state import SurvivorState


class SurvivorSnapshot:
    """Résultat de l'analyse visuelle d'un portrait à un instant T."""
    def __init__(self):
        self.state: str = SurvivorState.HEALTHY
        self.confidence: float = 0.0
        self.hook_bars: int = 0
        self.has_yellow_bar: bool = False


class VisionAnalyzer:
    """
    Analyse les 4 portraits de survivants dans une frame capturée.

    Détection par signaux combinés (sans template) dans cet ordre de priorité :
      1. Couleur de l'anneau  → mort / deep wounds
      2. Intérieur du cercle  → porté / accroché / à terre / sorti
      3. Barre jaune          → deep wounds
      4. Griffures rouges     → blessé vs bonne santé
    """

    def analyze_frame(self, frame: np.ndarray) -> list[SurvivorSnapshot]:
        """Analyse les 4 portraits et retourne 4 SurvivorSnapshot."""
        snapshots = []
        for pos in PORTRAIT_POSITIONS:
            roi = frame[pos["y"]:pos["y"]+pos["h"], pos["x"]:pos["x"]+pos["w"]]
            snapshots.append(self._analyze_portrait(roi))
        return snapshots

    def _analyze_portrait(self, roi: np.ndarray) -> SurvivorSnapshot:
        snap = SurvivorSnapshot()
        if roi.size == 0:
            return snap

        h, w = roi.shape[:2]

        # Masque circulaire : exclure le fond derrière le cercle (variable selon la map)
        circle_mask = self._make_circle_mask(h, w)
        roi_masked = cv2.bitwise_and(roi, roi, mask=circle_mask)

        # Signal 1 : intérieur du cercle (états icône) — PRIORITÉ ABSOLUE
        # Doit être testé AVANT ring=dark car carried/hooked/downed ont aussi un anneau sombre
        icon_state = self._detect_icon_state(roi_masked, circle_mask, h, w)
        if icon_state:
            snap.state = icon_state
            snap.hook_bars = self._count_white_bars(roi)
            return snap

        # Signal 2 : anneau — seulement si pas d'icône détectée
        ring_color = self._sample_ring_color(roi, h, w)
        if ring_color == "dark":
            snap.state = SurvivorState.DEAD
            snap.hook_bars = self._count_white_bars(roi)
            return snap

        # Signal 3 : cyan ou barre jaune → Deep Wounds
        has_yellow_bar = self._detect_yellow_bar(roi)
        snap.has_yellow_bar = has_yellow_bar
        if ring_color == "cyan" or has_yellow_bar:
            snap.state = SurvivorState.DEEP_WOUNDS
            snap.hook_bars = self._count_white_bars(roi)
            return snap

        # Signal 4 : griffures rouges → blessé vs bonne santé
        snap.state = SurvivorState.INJURED if self._detect_red_scratches(roi_masked) else SurvivorState.HEALTHY
        snap.hook_bars = self._count_white_bars(roi)
        return snap

    # ── Détection des états icône (sans template) ─────────────────────────────

    def _detect_icon_state(self, roi_masked: np.ndarray, circle_mask: np.ndarray, h: int, w: int) -> str | None:
        """
        Détecte Porté / Accroché / À terre / Sorti sans template.

        Principe : un portrait normal (visage) a beaucoup de pixels colorés et lumineux
        répartis partout. Une icône d'état a un fond quasi-noir avec une silhouette
        blanche/claire concentrée au centre.

        On détecte d'abord si c'est une icône (fond sombre dominant),
        puis on identifie laquelle par géométrie.
        """
        hsv = cv2.cvtColor(roi_masked, cv2.COLOR_BGR2HSV)
        circle_px = hsv[circle_mask == 255]
        if len(circle_px) == 0:
            return None

        mean_sat = float(np.mean(circle_px[:, 1]))
        mean_val = float(np.mean(circle_px[:, 2]))

        # Portrait normal : lumineux ET coloré (visage, cheveux, vêtements)
        # Seuils abaissés pour être robuste sur les maps sombres
        # mean_val > 80 : au moins modérément lumineux
        # mean_sat > 20 : présence de couleur (peau, vêtements)
        if mean_val > 80 and mean_sat > 20:
            return None

        # Sorti : teinte verte dominante (icône de porte)
        green_mask = cv2.inRange(hsv, np.array([35, 40, 140]), np.array([90, 255, 255]))
        green_ratio = np.sum((green_mask > 0) & (circle_mask == 255)) / max(np.sum(circle_mask == 255), 1)
        if green_ratio > 0.12:
            return SurvivorState.ESCAPED

        # Isoler les pixels de l'icône : clairs (V>100) et peu saturés (S<90)
        # = silhouette blanche/grise sur fond noir
        icon_mask = cv2.inRange(hsv, np.array([0, 0, 100]), np.array([180, 90, 255]))
        icon_mask = cv2.bitwise_and(icon_mask, circle_mask)
        icon_px = np.where(icon_mask > 0)
        n = len(icon_px[0])

        # Trop peu de pixels icône → probablement carried (silhouette quasi invisible)
        if n < 12:
            return SurvivorState.CARRIED

        rows, cols = icon_px
        row_spread = int(np.max(rows)) - int(np.min(rows))
        col_spread = int(np.max(cols)) - int(np.min(cols))
        aspect = col_spread / max(row_spread, 1)   # >1 = large, <1 = haut
        centroid_y = float(np.mean(rows)) / h      # 0 = haut, 1 = bas

        # À terre : silhouette horizontale (largeur >> hauteur)
        if aspect > 1.35:
            return SurvivorState.DOWNED

        # Accroché : silhouette verticale concentrée en haut du cercle
        if aspect < 0.85 and centroid_y < 0.55:
            return SurvivorState.HOOKED

        return SurvivorState.CARRIED

    # ── Signaux HSV ───────────────────────────────────────────────────────────

    def _make_circle_mask(self, h: int, w: int) -> np.ndarray:
        """Masque binaire circulaire inscrit dans le rectangle h×w."""
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask, (w // 2, h // 2), min(w, h) // 2 - 2, 255, -1)
        return mask

    def _sample_ring_color(self, roi: np.ndarray, h: int, w: int) -> str:
        """
        Analyse la couleur de l'anneau (bordure du cercle).
        Retourne "dark" (mort), "cyan" (Deep Wounds) ou "white" (vivant normal).
        """
        ring_width = max(3, min(h, w) // 10)
        center = (w // 2, h // 2)
        r_out = min(w, h) // 2 - 1
        mo = np.zeros((h, w), dtype=np.uint8)
        mi = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mo, center, r_out, 255, -1)
        cv2.circle(mi, center, r_out - ring_width, 255, -1)
        ring_mask = cv2.bitwise_xor(mo, mi)

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        px = hsv[ring_mask == 255]
        if len(px) == 0:
            return "white"

        mean_h = float(np.mean(px[:, 0]))
        mean_s = float(np.mean(px[:, 1]))
        mean_v = float(np.mean(px[:, 2]))

        # Seuil dark plus strict : V très bas ET peu saturé
        # Évite les faux positifs sur maps sombres avec des survivants vivants
        if mean_v < 35 and mean_s < 60:
            return "dark"

        # Seuil cyan plus strict : plage H resserrée + saturation élevée
        # Évite les faux positifs sur fonds orangés/chauds
        if 88 <= mean_h <= 105 and mean_s > 130 and mean_v > 60:
            return "cyan"

        return "white"

    def _detect_red_scratches(self, roi_masked: np.ndarray) -> bool:
        """Détecte les griffures rouges (état Blessé). Le rouge HSV est en deux plages."""
        hsv = cv2.cvtColor(roi_masked, cv2.COLOR_BGR2HSV)
        m1 = cv2.inRange(hsv, np.array([0,   180, 120]), np.array([10,  255, 255]))
        m2 = cv2.inRange(hsv, np.array([170, 180, 120]), np.array([180, 255, 255]))
        return int(np.sum(cv2.bitwise_or(m1, m2) > 0)) > 30

    def _detect_yellow_bar(self, roi: np.ndarray) -> bool:
        """Détecte la barre jaune de Deep Wounds dans le tiers inférieur du portrait."""
        h, w = roi.shape[:2]
        bar_zone = roi[2*h//3:h, :]
        hsv = cv2.cvtColor(bar_zone, cv2.COLOR_BGR2HSV)
        yellow = cv2.inRange(hsv, np.array([20, 150, 150]), np.array([35, 255, 255]))
        return bool(np.any(np.sum(yellow > 0, axis=1) > w * 0.4))

    def _count_white_bars(self, roi: np.ndarray) -> int:
        """Compte les barres blanches (hook count : 0, 1 ou 2) à droite du cercle."""
        h, w = roi.shape[:2]
        bars_zone = roi[:, w*3//4:]
        if bars_zone.size == 0:
            return 0
        hsv = cv2.cvtColor(bars_zone, cv2.COLOR_BGR2HSV)
        white = cv2.inRange(hsv, np.array([0, 0, 200]), np.array([180, 30, 255]))
        half = h // 2
        count = 0
        if np.sum(white[:half] > 0) > 10:
            count += 1
        if np.sum(white[half:] > 0) > 10:
            count += 1
        return count

    # ── Debug ─────────────────────────────────────────────────────────────────

    def get_debug_info(self, frame: np.ndarray) -> list[dict]:
        """Retourne les infos brutes de détection pour tools/test_vision.py."""
        debug_list = []
        for i, pos in enumerate(PORTRAIT_POSITIONS):
            roi = frame[pos["y"]:pos["y"]+pos["h"], pos["x"]:pos["x"]+pos["w"]]
            if roi.size == 0:
                debug_list.append({})
                continue
            h, w = roi.shape[:2]
            circle_mask = self._make_circle_mask(h, w)
            roi_masked = cv2.bitwise_and(roi, roi, mask=circle_mask)
            hsv = cv2.cvtColor(roi_masked, cv2.COLOR_BGR2HSV)
            px = hsv[circle_mask == 255]
            snap = self._analyze_portrait(roi)
            debug_list.append({
                "survivor":       i + 1,
                "state":          snap.state,
                "ring_color":     self._sample_ring_color(roi, h, w),
                "mean_sat":       round(float(np.mean(px[:, 1])) if len(px) else 0, 1),
                "mean_val":       round(float(np.mean(px[:, 2])) if len(px) else 0, 1),
                "has_scratches":  self._detect_red_scratches(roi_masked),
                "has_yellow_bar": self._detect_yellow_bar(roi),
                "icon_state":     self._detect_icon_state(roi_masked, circle_mask, h, w),
                "hook_bars":      snap.hook_bars,
            })
        return debug_list