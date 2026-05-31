import os
import cv2
import numpy as np
import joblib
from core.config import PORTRAIT_POSITIONS, TEMPLATE_THRESHOLD
from core.state import SurvivorState
from vision.features import extract_hog

_ICONS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "icons")

_ICON_STATES = ["downed", "carried", "hooked", "dead", "escaped"]

_CLASSIFIER_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "living_clf.joblib")


class SurvivorSnapshot:
    def __init__(self):
        self.state: str     = SurvivorState.HEALTHY
        self.hook_bars: int = 0


class VisionAnalyzer:
    """
    Analyse les 4 portraits de survivants dans une frame capturée.

    Pipeline :
      1. Template matching (niveaux de gris, zone centrale 80%) → états icônes
         (downed / carried / hooked / dead / escaped)
      2. Classifieur SVM HOG (assets/living_clf.joblib) → healthy / injured
      3. Sinon → HEALTHY par défaut
    """

    def __init__(self):
        self._icon_templates = self._load_templates(_ICON_STATES)
        self._living_clf     = self._load_classifier()
        print(f"[VisionAnalyzer] Icon templates : { {s: len(t) for s, t in self._icon_templates.items()} }")
        print(f"[VisionAnalyzer] Living clf     : {'OK' if self._living_clf else 'absent (HEALTHY par défaut)'}")

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

    def _load_classifier(self):
        if os.path.exists(_CLASSIFIER_PATH):
            try:
                return joblib.load(_CLASSIFIER_PATH)
            except Exception as e:
                print(f"[VisionAnalyzer] Erreur chargement classifieur : {e}")
        return None

    def reload_templates(self):
        self._icon_templates = self._load_templates(_ICON_STATES)
        self._living_clf     = self._load_classifier()

    # ── Pipeline ──────────────────────────────────────────────────────────────

    def analyze_frame(self, frame: np.ndarray) -> list[SurvivorSnapshot]:
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

        h, w       = roi.shape[:2]
        center_roi = roi[h//10 : 9*h//10, w//10 : 9*w//10]

        icon_state, _ = self._match_templates(center_roi, self._icon_templates, TEMPLATE_THRESHOLD)
        if icon_state:
            snap.state     = icon_state
            snap.hook_bars = self._count_white_bars(roi)
            return snap

        if self._living_clf:
            features   = extract_hog(center_roi)
            pred       = self._living_clf["model"].predict([features])[0]
            snap.state = self._living_clf["states"][pred]

        snap.hook_bars = self._count_white_bars(roi)
        return snap

    # ── Template matching ─────────────────────────────────────────────────────

    def _match_templates(self, roi: np.ndarray, templates: dict, threshold: float) -> tuple[str | None, float]:
        if not templates or roi.size == 0:
            return None, 0.0

        gray     = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
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

    # ── Barres blanches (hook count) ──────────────────────────────────────────

    def _count_white_bars(self, roi: np.ndarray) -> int:
        h, w      = roi.shape[:2]
        bars_zone = roi[:, w*3//4:]
        if bars_zone.size == 0:
            return 0
        hsv   = cv2.cvtColor(bars_zone, cv2.COLOR_BGR2HSV)
        white = cv2.inRange(hsv, np.array([0, 0, 200]), np.array([180, 30, 255]))
        half  = h // 2
        count = 0
        if np.sum(white[:half] > 0) > 10: count += 1
        if np.sum(white[half:]  > 0) > 10: count += 1
        return count

    # ── Debug ─────────────────────────────────────────────────────────────────

    def get_debug_info(self, frame: np.ndarray) -> list[dict]:
        debug_list = []
        for i, pos in enumerate(PORTRAIT_POSITIONS):
            roi = frame[pos["y"]:pos["y"]+pos["h"], pos["x"]:pos["x"]+pos["w"]]
            if roi.size == 0:
                debug_list.append({})
                continue

            h, w       = roi.shape[:2]
            center_roi = roi[h//10:9*h//10, w//10:9*w//10]

            icon_state, icon_score = self._match_templates(center_roi, self._icon_templates, TEMPLATE_THRESHOLD)

            clf_pred, clf_conf = None, 0.0
            if self._living_clf:
                features  = extract_hog(center_roi)
                pred      = self._living_clf["model"].predict([features])[0]
                proba     = self._living_clf["model"].predict_proba([features])[0]
                clf_pred  = self._living_clf["states"][pred]
                clf_conf  = round(float(max(proba)), 3)

            snap = self._analyze_portrait(roi)

            debug_list.append({
                "survivor":   i + 1,
                "state":      snap.state,
                "icon_match": icon_state,
                "icon_score": round(icon_score, 3),
                "clf_pred":   clf_pred,
                "clf_conf":   clf_conf,
                "hook_bars":  snap.hook_bars,
            })

        return debug_list
