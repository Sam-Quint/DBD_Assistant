import os
import cv2
import numpy as np
import joblib
from core.config import PORTRAIT_POSITIONS, TEMPLATE_THRESHOLD
from core.state import SurvivorState
from vision.features import extract_hog

# Taille à laquelle les templates sont stockés et comparés
TEMPLATE_SIZE = 32

# Chemin vers les templates (relatif à ce fichier : vision/../assets/icons/)
_ICONS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "icons")

# États avec symboles distinctifs (template matching)
_ICON_STATES = ["downed", "carried", "hooked", "dead", "escaped"]

# Chemin du modèle SVM entraîné pour healthy/injured
_CLASSIFIER_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "living_clf.joblib")


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
      1. Template matching (niveaux de gris, zone centrale 80%) → états icônes
      2. Classifieur SVM HOG (assets/living_clf.joblib)         → healthy / injured
      3. Sinon → HEALTHY par défaut

    Templates chargés depuis assets/icons/{état}/*.png.
    Modèle SVM entraîné via Entrainement/train_classifier.ipynb.
    """

    def __init__(self):
        self._icon_templates = self._load_templates(_ICON_STATES)
        self._living_clf     = self._load_classifier()
        print(f"[VisionAnalyzer] Icon templates : { {s: len(t) for s, t in self._icon_templates.items()} }")
        print(f"[VisionAnalyzer] Living clf     : {'OK' if self._living_clf else 'absent (HEALTHY par défaut)'}")

    # ── Chargement des templates ──────────────────────────────────────────────

    def _load_templates(self, states: list[str]) -> dict[str, list[np.ndarray]]:
        templates = {}
        for state in states:
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
        """Recharge les templates et le classifieur depuis le disque."""
        self._icon_templates = self._load_templates(_ICON_STATES)
        self._living_clf     = self._load_classifier()

    def _load_classifier(self):
        """Charge le modèle SVM depuis assets/living_clf.joblib, ou None si absent."""
        if os.path.exists(_CLASSIFIER_PATH):
            try:
                return joblib.load(_CLASSIFIER_PATH)
            except Exception as e:
                print(f"[VisionAnalyzer] Erreur chargement classifieur : {e}")
        return None

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
        center_roi = roi[h//10 : 9*h//10, w//10 : 9*w//10]

        # États icônes (symboles distinctifs, template matching)
        icon_state, _ = self._match_templates(center_roi, self._icon_templates, TEMPLATE_THRESHOLD)
        if icon_state:
            snap.state = icon_state
            snap.hook_bars = self._count_white_bars(roi)
            return snap

        # États vivants (SVM sur features HOG)
        if self._living_clf:
            features = extract_hog(center_roi)
            pred     = self._living_clf["model"].predict([features])[0]
            snap.state = self._living_clf["states"][pred]

        snap.hook_bars = self._count_white_bars(roi)
        return snap

    # ── Template matching ─────────────────────────────────────────────────────

    def _match_templates(self, roi: np.ndarray, templates: dict, threshold: float) -> tuple[str | None, float]:
        """Retourne l'état avec le meilleur score parmi les templates donnés, ou (None, 0.0)."""
        if not templates or roi.size == 0:
            return None, 0.0

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        r_h, r_w = gray.shape[:2]

        best_state, best_score = None, 0.0

        for state, tmpl_list in templates.items():
            for tmpl in tmpl_list:
                t      = cv2.resize(tmpl, (r_w, r_h)) if tmpl.shape != (r_h, r_w) else tmpl
                result = cv2.matchTemplate(gray, t, cv2.TM_CCOEFF_NORMED)
                score  = float(np.max(result))
                if score > best_score:
                    best_score = score
                    best_state = state

        if best_score >= threshold:
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

            icon_state, icon_score = self._match_templates(center_roi, self._icon_templates, TEMPLATE_THRESHOLD)
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
