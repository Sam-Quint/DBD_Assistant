import os
import cv2
import numpy as np
from core.config import PORTRAIT_POSITIONS, TEMPLATE_THRESHOLD
from core.state import SurvivorState

# Taille à laquelle les templates sont stockés et comparés
TEMPLATE_SIZE = 32

# Chemin vers les templates (relatif à ce fichier : vision/../assets/icons/)
_ICONS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "icons")

# États gérés par le template matching
_ICON_STATES = ["healthy", "injured", "downed", "carried", "hooked", "dead", "escaped"]


class SurvivorSnapshot:
    """Résultat de l'analyse visuelle d'un portrait à un instant T."""
    def __init__(self):
        self.state: str   = SurvivorState.HEALTHY
        self.hook_bars: int = 0
        self.has_yellow_bar: bool = False


class VisionAnalyzer:
    """
    Analyse les 4 portraits de survivants dans une frame capturée.

    Pipeline de détection :
      1. Template matching (niveaux de gris) sur la zone centrale du portrait
         → match trouvé au-dessus du seuil → état icône (downed/carried/hooked/dead/escaped)
      2. Sinon → portrait vivant :
         → barre jaune (tiers bas)           → DEEP_WOUNDS
         → griffures rouges (HSV rouge)      → INJURED
         → sinon                             → HEALTHY

    Les templates sont chargés depuis assets/icons/{état}/*.png au démarrage.
    Plusieurs templates par état sont supportés (score max retenu).
    """

    def __init__(self):
        # Dictionnaire {état: [image_gris_32x32, ...]}
        self._templates = self._load_templates()
        loaded = {s: len(t) for s, t in self._templates.items()}
        print(f"[VisionAnalyzer] Templates chargés : {loaded}")

    # ── Chargement des templates ──────────────────────────────────────────────

    def _load_templates(self) -> dict[str, list[np.ndarray]]:
        """
        Charge tous les templates PNG depuis assets/icons/{état}/.
        Convertit en niveaux de gris et stocke tel quel (le redimensionnement
        se fait à la volée dans _match_icon pour s'adapter à la taille réelle).
        """
        templates = {}
        for state in _ICON_STATES:
            state_dir = os.path.join(_ICONS_DIR, state)
            if not os.path.isdir(state_dir):
                continue
            imgs = []
            for fname in sorted(os.listdir(state_dir)):
                if fname.lower().endswith(".png"):
                    img = cv2.imread(os.path.join(state_dir, fname), cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        imgs.append(img)
            if imgs:
                templates[state] = imgs
        return templates

    def reload_templates(self):
        """Recharge les templates depuis le disque (utile après une capture)."""
        self._templates = self._load_templates()

    # ── Pipeline principal ────────────────────────────────────────────────────

    def analyze_frame(self, frame: np.ndarray) -> list[SurvivorSnapshot]:
        """Analyse les 4 portraits et retourne 4 SurvivorSnapshot."""
        return [
            self._analyze_portrait(
                frame[pos["y"]:pos["y"]+pos["h"], pos["x"]:pos["x"]+pos["w"]]
            )
            for pos in PORTRAIT_POSITIONS
        ]

    def _analyze_portrait(self, roi: np.ndarray) -> SurvivorSnapshot:
        snap = SurvivorSnapshot()
        if roi.size == 0:
            return snap

        h, w = roi.shape[:2]

        # 80% du portrait (marge 10% pour exclure le bord de l'anneau)
        center_roi = roi[h//10 : 9*h//10, w//10 : 9*w//10]

        # ── Étape 1 : template matching sur la zone centrale ──────────────────
        icon_state, score = self._match_icon(center_roi)
        if icon_state:
            snap.state     = icon_state
            snap.hook_bars = self._count_white_bars(roi)
            return snap

        # ── Étape 2 : portrait vivant → signaux HSV ───────────────────────────
        circle_mask = self._make_circle_mask(h, w)
        roi_masked  = cv2.bitwise_and(roi, roi, mask=circle_mask)

        has_yellow = self._detect_yellow_bar(roi)
        snap.has_yellow_bar = has_yellow

        if has_yellow:
            snap.state = SurvivorState.DEEP_WOUNDS
        elif self._detect_red_scratches(roi_masked):
            snap.state = SurvivorState.INJURED
        else:
            snap.state = SurvivorState.HEALTHY

        snap.hook_bars = self._count_white_bars(roi)
        return snap

    # ── Template matching ─────────────────────────────────────────────────────

    def _match_icon(self, center_roi: np.ndarray) -> tuple[str | None, float]:
        """
        Template matching en niveaux de gris sur la zone centrale.

        Pour chaque état, on teste tous ses templates et on garde le score max.
        On retourne l'état avec le meilleur score global, si celui-ci dépasse
        TEMPLATE_THRESHOLD. Sinon retourne (None, 0.0).
        """
        if not self._templates or center_roi.size == 0:
            return None, 0.0

        gray = cv2.cvtColor(center_roi, cv2.COLOR_BGR2GRAY)
        c_h, c_w = gray.shape[:2]

        best_state, best_score = None, 0.0

        for state, tmpl_list in self._templates.items():
            for tmpl in tmpl_list:
                # Redimensionner le template à la taille exacte de la zone centrale
                t = cv2.resize(tmpl, (c_w, c_h)) if tmpl.shape != (c_h, c_w) else tmpl
                result = cv2.matchTemplate(gray, t, cv2.TM_CCOEFF_NORMED)
                score  = float(np.max(result))
                if score > best_score:
                    best_score = score
                    best_state = state

        if best_score >= TEMPLATE_THRESHOLD:
            return best_state, best_score
        return None, 0.0

    # ── Signaux HSV (portrait vivant) ─────────────────────────────────────────

    def _make_circle_mask(self, h: int, w: int) -> np.ndarray:
        """Masque circulaire pour exclure le fond variable derrière le portrait."""
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask, (w // 2, h // 2), min(w, h) // 2 - 2, 255, -1)
        return mask

    def _detect_red_scratches(self, roi_masked: np.ndarray) -> bool:
        """Griffures rouges (Blessé). Le rouge HSV occupe deux plages de teinte."""
        hsv = cv2.cvtColor(roi_masked, cv2.COLOR_BGR2HSV)
        m1  = cv2.inRange(hsv, np.array([0,   180, 120]), np.array([10,  255, 255]))
        m2  = cv2.inRange(hsv, np.array([170, 180, 120]), np.array([180, 255, 255]))
        return int(np.sum(cv2.bitwise_or(m1, m2) > 0)) > 30

    def _detect_yellow_bar(self, roi: np.ndarray) -> bool:
        """Barre jaune Deep Wounds : ligne horizontale continue dans le tiers bas."""
        h, w     = roi.shape[:2]
        bar_zone = roi[2*h//3:h, :]
        hsv      = cv2.cvtColor(bar_zone, cv2.COLOR_BGR2HSV)
        yellow   = cv2.inRange(hsv, np.array([20, 150, 150]), np.array([35, 255, 255]))
        return bool(np.any(np.sum(yellow > 0, axis=1) > w * 0.4))

    def _count_white_bars(self, roi: np.ndarray) -> int:
        """Barres blanches (hook count 0/1/2) à droite du cercle."""
        h, w      = roi.shape[:2]
        bars_zone = roi[:, w*3//4:]
        if bars_zone.size == 0:
            return 0
        hsv   = cv2.cvtColor(bars_zone, cv2.COLOR_BGR2HSV)
        white = cv2.inRange(hsv, np.array([0, 0, 200]), np.array([180, 30, 255]))
        half  = h // 2
        count = 0
        if np.sum(white[:half] > 0) > 10: count += 1
        if np.sum(white[half:] > 0) > 10: count += 1
        return count

    # ── Debug ─────────────────────────────────────────────────────────────────

    def get_debug_info(self, frame: np.ndarray) -> list[dict]:
        """Retourne les valeurs brutes de détection pour tools/test_vision.py."""
        debug_list = []
        for i, pos in enumerate(PORTRAIT_POSITIONS):
            roi = frame[pos["y"]:pos["y"]+pos["h"], pos["x"]:pos["x"]+pos["w"]]
            if roi.size == 0:
                debug_list.append({})
                continue

            h, w        = roi.shape[:2]
            center_roi  = roi[h//10:9*h//10, w//10:9*w//10]
            circle_mask = self._make_circle_mask(h, w)
            roi_masked  = cv2.bitwise_and(roi, roi, mask=circle_mask)

            icon_state, icon_score = self._match_icon(center_roi)
            snap = self._analyze_portrait(roi)

            debug_list.append({
                "survivor":       i + 1,
                "state":          snap.state,
                "icon_match":     icon_state,
                "icon_score":     round(icon_score, 3),
                "has_scratches":  self._detect_red_scratches(roi_masked),
                "has_yellow_bar": self._detect_yellow_bar(roi),
                "hook_bars":      snap.hook_bars,
            })

        return debug_list
