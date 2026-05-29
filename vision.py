import os
import cv2
import numpy as np
from config import PORTRAIT_POSITIONS, TEMPLATE_THRESHOLD, ASSETS_DIR
from state import SurvivorState


class SurvivorSnapshot:
    """État visuel brut d'un survivant à un instant T."""
    def __init__(self):
        self.state: str = SurvivorState.HEALTHY
        self.confidence: float = 0.0
        self.hook_bars: int = 0
        self.has_yellow_bar: bool = False


class VisionAnalyzer:
    def __init__(self):
        self.icon_templates = self._load_icon_templates()

    def _load_icon_templates(self) -> dict:
        """Charge les templates des icônes centrales depuis assets/icons/."""
        templates = {}
        icon_map = {
            SurvivorState.DOWNED:       "icon_downed.png",
            SurvivorState.CARRIED:      "icon_carried.png",
            SurvivorState.HOOKED:       "icon_hooked.png",
            SurvivorState.DEAD:         "icon_dead.png",
            SurvivorState.ESCAPED:      "icon_escaped.png",
            SurvivorState.DISCONNECTED: "icon_disconnected.png",
        }
        for state, filename in icon_map.items():
            path = os.path.join(os.path.dirname(__file__), ASSETS_DIR, filename)
            if os.path.exists(path):
                img = cv2.imread(path)
                if img is not None:
                    templates[state] = img
        return templates

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
        circle_mask = self._make_circle_mask(h, w)
        roi_masked = cv2.bitwise_and(roi, roi, mask=circle_mask)

        # Signal 1 : icône centrale (états non-vivants)
        cy1, cy2 = h // 4, 3 * h // 4
        cx1, cx2 = w // 4, 3 * w // 4
        center_roi = roi[cy1:cy2, cx1:cx2]
        icon_state, icon_score = self._match_icon(center_roi)

        if icon_state and icon_score >= TEMPLATE_THRESHOLD:
            snap.state = icon_state
            snap.confidence = icon_score
            snap.hook_bars = self._count_white_bars(roi)
            return snap

        # Signal 2 : couleur de l'anneau
        ring_color = self._sample_ring_color(roi, h, w)

        if ring_color == "dark":
            snap.state = SurvivorState.DEAD
            snap.hook_bars = self._count_white_bars(roi)
            return snap

        # Signal 3 : griffures rouges (blessé)
        has_scratches = self._detect_red_scratches(roi_masked)

        # Signal 4 : barre jaune (Deep Wounds)
        has_yellow_bar = self._detect_yellow_bar(roi)
        snap.has_yellow_bar = has_yellow_bar

        if ring_color == "cyan" or has_yellow_bar:
            snap.state = SurvivorState.DEEP_WOUNDS
        elif has_scratches:
            snap.state = SurvivorState.INJURED
        else:
            snap.state = SurvivorState.HEALTHY

        snap.hook_bars = self._count_white_bars(roi)
        return snap

    # ----------------------------------------------------------------
    # Méthodes de détection
    # ----------------------------------------------------------------

    def _make_circle_mask(self, h: int, w: int) -> np.ndarray:
        mask = np.zeros((h, w), dtype=np.uint8)
        center = (w // 2, h // 2)
        radius = min(w, h) // 2 - 2
        cv2.circle(mask, center, radius, 255, -1)
        return mask

    def _sample_ring_color(self, roi: np.ndarray, h: int, w: int) -> str:
        """Retourne "cyan", "dark", ou "white"."""
        ring_width = max(3, min(h, w) // 10)
        center = (w // 2, h // 2)
        radius_outer = min(w, h) // 2 - 1
        radius_inner = radius_outer - ring_width

        mask_outer = np.zeros((h, w), dtype=np.uint8)
        mask_inner = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask_outer, center, radius_outer, 255, -1)
        cv2.circle(mask_inner, center, radius_inner, 255, -1)
        ring_mask = cv2.bitwise_xor(mask_outer, mask_inner)

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        ring_pixels = hsv[ring_mask == 255]

        if len(ring_pixels) == 0:
            return "white"

        mean_h = float(np.mean(ring_pixels[:, 0]))
        mean_s = float(np.mean(ring_pixels[:, 1]))
        mean_v = float(np.mean(ring_pixels[:, 2]))

        if mean_v < 50:
            return "dark"
        if 85 <= mean_h <= 100 and mean_s > 100:
            return "cyan"
        return "white"

    def _detect_red_scratches(self, roi_masked: np.ndarray) -> bool:
        """Détecte les griffures rouges (état Blessé)."""
        hsv = cv2.cvtColor(roi_masked, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, np.array([0,   180, 120]), np.array([10,  255, 255]))
        mask2 = cv2.inRange(hsv, np.array([170, 180, 120]), np.array([180, 255, 255]))
        red_mask = cv2.bitwise_or(mask1, mask2)
        return int(np.sum(red_mask > 0)) > 30

    def _detect_yellow_bar(self, roi: np.ndarray) -> bool:
        """Détecte la barre jaune de Deep Wounds en bas du portrait."""
        h, w = roi.shape[:2]
        bar_zone = roi[2*h//3:h, :]
        hsv = cv2.cvtColor(bar_zone, cv2.COLOR_BGR2HSV)
        yellow_mask = cv2.inRange(
            hsv,
            np.array([20, 150, 150]),
            np.array([35, 255, 255])
        )
        row_sums = np.sum(yellow_mask > 0, axis=1)
        return bool(np.any(row_sums > w * 0.4))

    def _match_icon(self, center_roi: np.ndarray) -> tuple[str | None, float]:
        """Template matching sur la zone centrale uniquement."""
        if not self.icon_templates or center_roi.size == 0:
            return None, 0.0

        best_state, best_score = None, 0.0
        c_h, c_w = center_roi.shape[:2]

        for state_name, template in self.icon_templates.items():
            t = template
            t_h, t_w = t.shape[:2]
            if t_h != c_h or t_w != c_w:
                t = cv2.resize(t, (c_w, c_h))

            result = cv2.matchTemplate(center_roi, t, cv2.TM_CCOEFF_NORMED)
            score = float(np.max(result))
            if score > best_score:
                best_score = score
                best_state = state_name

        return best_state, best_score

    def _count_white_bars(self, roi: np.ndarray) -> int:
        """Compte les barres blanches (0, 1 ou 2) à droite du cercle."""
        h, w = roi.shape[:2]
        bars_zone = roi[:, w*3//4:]

        if bars_zone.size == 0:
            return 0

        hsv = cv2.cvtColor(bars_zone, cv2.COLOR_BGR2HSV)
        white_mask = cv2.inRange(hsv, np.array([0, 0, 200]), np.array([180, 30, 255]))

        count = 0
        half = h // 2
        if np.sum(white_mask[:half] > 0) > 10:
            count += 1
        if np.sum(white_mask[half:] > 0) > 10:
            count += 1

        return count

    def get_debug_info(self, frame: np.ndarray) -> list[dict]:
        """Retourne les infos de debug pour chaque portrait (pour tools/test_vision.py)."""
        debug_list = []
        for i, pos in enumerate(PORTRAIT_POSITIONS):
            roi = frame[pos["y"]:pos["y"]+pos["h"], pos["x"]:pos["x"]+pos["w"]]
            if roi.size == 0:
                debug_list.append({})
                continue

            h, w = roi.shape[:2]
            circle_mask = self._make_circle_mask(h, w)
            roi_masked = cv2.bitwise_and(roi, roi, mask=circle_mask)

            ring_color = self._sample_ring_color(roi, h, w)
            has_scratches = self._detect_red_scratches(roi_masked)
            has_yellow = self._detect_yellow_bar(roi)

            cy1, cy2 = h // 4, 3 * h // 4
            cx1, cx2 = w // 4, 3 * w // 4
            center_roi = roi[cy1:cy2, cx1:cx2]
            icon_state, icon_score = self._match_icon(center_roi)

            snap = self._analyze_portrait(roi)

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
            ring_px = hsv[ring_mask == 255]
            mean_hsv = tuple(float(np.mean(ring_px[:, c])) for c in range(3)) if len(ring_px) else (0, 0, 0)

            debug_list.append({
                "survivor": i + 1,
                "state": snap.state,
                "confidence": snap.confidence,
                "hook_bars": snap.hook_bars,
                "ring_color": ring_color,
                "ring_hsv": mean_hsv,
                "has_scratches": has_scratches,
                "has_yellow_bar": has_yellow,
                "icon_state": icon_state,
                "icon_score": icon_score,
            })

        return debug_list
