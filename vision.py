import cv2
import numpy as np
from config import PORTRAIT_POSITIONS
from state import SurvivorState


class SurvivorSnapshot:
    def __init__(self):
        self.state: str = SurvivorState.HEALTHY
        self.confidence: float = 0.0
        self.hook_bars: int = 0
        self.has_yellow_bar: bool = False


class VisionAnalyzer:
    def analyze_frame(self, frame: np.ndarray) -> list[SurvivorSnapshot]:
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
        circle_mask = self._make_circle_mask(h, w)
        roi_masked = cv2.bitwise_and(roi, roi, mask=circle_mask)

        # ── Signal 1 : anneau ────────────────────────────────────────────────
        ring_color = self._sample_ring_color(roi, h, w)

        if ring_color == "dark":
            snap.state = SurvivorState.DEAD
            snap.hook_bars = self._count_white_bars(roi)
            return snap

        # ── Signal 2 : intérieur du cercle ───────────────────────────────────
        icon_state = self._detect_icon_state(roi_masked, circle_mask, h, w)
        if icon_state:
            snap.state = icon_state
            snap.hook_bars = self._count_white_bars(roi)
            return snap

        # ── Signal 3 : barre jaune (Deep Wounds) ─────────────────────────────
        has_yellow_bar = self._detect_yellow_bar(roi)
        snap.has_yellow_bar = has_yellow_bar

        if ring_color == "cyan" or has_yellow_bar:
            snap.state = SurvivorState.DEEP_WOUNDS
            snap.hook_bars = self._count_white_bars(roi)
            return snap

        # ── Signal 4 : griffures rouges (blessé) ─────────────────────────────
        if self._detect_red_scratches(roi_masked):
            snap.state = SurvivorState.INJURED
        else:
            snap.state = SurvivorState.HEALTHY

        snap.hook_bars = self._count_white_bars(roi)
        return snap

    # ── Détection des états icône (sans template) ────────────────────────────

    def _detect_icon_state(self, roi_masked: np.ndarray, circle_mask: np.ndarray, h: int, w: int) -> str | None:
        """
        Détecte les états Porté / Accroché / À terre / Sorti / Déconnecté
        sans aucun template, uniquement par analyse HSV de l'intérieur du cercle.

        Un portrait normal (visage) a une saturation et luminosité moyennes élevées.
        Un état icône a un intérieur sombre avec une forme claire dessus.
        """
        hsv = cv2.cvtColor(roi_masked, cv2.COLOR_BGR2HSV)
        circle_px = hsv[circle_mask == 255]

        if len(circle_px) == 0:
            return None

        mean_sat = float(np.mean(circle_px[:, 1]))
        mean_val = float(np.mean(circle_px[:, 2]))

        # Portrait normal : saturation et luminosité élevées (teintes de peau, cheveux)
        if mean_val > 95 and mean_sat > 28:
            return None

        # ── Sorti (Escaped) : portrait très lumineux avec teinte verte ───────
        green_mask = cv2.inRange(
            hsv,
            np.array([35, 40, 140]),
            np.array([90, 255, 255])
        )
        green_ratio = np.sum((green_mask > 0) & (circle_mask == 255)) / max(np.sum(circle_mask == 255), 1)
        if green_ratio > 0.12:
            return SurvivorState.ESCAPED

        # ── Icône sombre : isoler les pixels clairs (l'icône sur fond noir) ──
        icon_mask = cv2.inRange(hsv, np.array([0, 0, 100]), np.array([180, 80, 255]))
        icon_mask = cv2.bitwise_and(icon_mask, circle_mask)

        icon_px = np.where(icon_mask > 0)
        n = len(icon_px[0])

        if n < 12:
            # Presque aucun pixel clair → silhouette à peine visible → Porté
            return SurvivorState.CARRIED

        rows, cols = icon_px
        row_spread = int(np.max(rows)) - int(np.min(rows))
        col_spread = int(np.max(cols)) - int(np.min(cols))
        aspect = col_spread / max(row_spread, 1)  # >1 = large, <1 = haut

        centroid_y = float(np.mean(rows)) / h   # position verticale de l'icône

        # À terre : silhouette allongée horizontalement
        if aspect > 1.35:
            return SurvivorState.DOWNED

        # Accroché : forme de crochet — majoritairement verticale, concentrée en haut
        if aspect < 0.85 and centroid_y < 0.55:
            return SurvivorState.HOOKED

        # Sinon : Porté (silhouette verticale, centroïde plus bas)
        return SurvivorState.CARRIED

    # ── Méthodes de détection HSV ────────────────────────────────────────────

    def _make_circle_mask(self, h: int, w: int) -> np.ndarray:
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask, (w // 2, h // 2), min(w, h) // 2 - 2, 255, -1)
        return mask

    def _sample_ring_color(self, roi: np.ndarray, h: int, w: int) -> str:
        """Retourne "cyan", "dark" ou "white"."""
        ring_width = max(3, min(h, w) // 10)
        center = (w // 2, h // 2)
        r_out = min(w, h) // 2 - 1
        r_in = r_out - ring_width

        mo = np.zeros((h, w), dtype=np.uint8)
        mi = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mo, center, r_out, 255, -1)
        cv2.circle(mi, center, r_in, 255, -1)
        ring_mask = cv2.bitwise_xor(mo, mi)

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        px = hsv[ring_mask == 255]

        if len(px) == 0:
            return "white"

        mean_h = float(np.mean(px[:, 0]))
        mean_s = float(np.mean(px[:, 1]))
        mean_v = float(np.mean(px[:, 2]))

        if mean_v < 50:
            return "dark"
        if 85 <= mean_h <= 100 and mean_s > 100:
            return "cyan"
        return "white"

    def _detect_red_scratches(self, roi_masked: np.ndarray) -> bool:
        hsv = cv2.cvtColor(roi_masked, cv2.COLOR_BGR2HSV)
        m1 = cv2.inRange(hsv, np.array([0,   180, 120]), np.array([10,  255, 255]))
        m2 = cv2.inRange(hsv, np.array([170, 180, 120]), np.array([180, 255, 255]))
        return int(np.sum(cv2.bitwise_or(m1, m2) > 0)) > 30

    def _detect_yellow_bar(self, roi: np.ndarray) -> bool:
        h, w = roi.shape[:2]
        bar_zone = roi[2*h//3:h, :]
        hsv = cv2.cvtColor(bar_zone, cv2.COLOR_BGR2HSV)
        yellow = cv2.inRange(hsv, np.array([20, 150, 150]), np.array([35, 255, 255]))
        return bool(np.any(np.sum(yellow > 0, axis=1) > w * 0.4))

    def _count_white_bars(self, roi: np.ndarray) -> int:
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

    # ── Debug ────────────────────────────────────────────────────────────────

    def get_debug_info(self, frame: np.ndarray) -> list[dict]:
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
            mean_sat = float(np.mean(px[:, 1])) if len(px) else 0
            mean_val = float(np.mean(px[:, 2])) if len(px) else 0

            ring_color = self._sample_ring_color(roi, h, w)
            has_scratches = self._detect_red_scratches(roi_masked)
            has_yellow = self._detect_yellow_bar(roi)
            icon_state = self._detect_icon_state(roi_masked, circle_mask, h, w)
            snap = self._analyze_portrait(roi)

            debug_list.append({
                "survivor":      i + 1,
                "state":         snap.state,
                "ring_color":    ring_color,
                "mean_sat":      round(mean_sat, 1),
                "mean_val":      round(mean_val, 1),
                "has_scratches": has_scratches,
                "has_yellow_bar":has_yellow,
                "icon_state":    icon_state,
                "hook_bars":     snap.hook_bars,
            })

        return debug_list
