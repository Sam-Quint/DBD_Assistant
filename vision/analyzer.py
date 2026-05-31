import os
import cv2
import numpy as np
import joblib
from core.config import PORTRAIT_POSITIONS
from core.state import SurvivorState
from vision.features import extract_hog

_CLASSIFIER_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "state_clf.joblib")


class SurvivorSnapshot:
    def __init__(self):
        self.state: str     = SurvivorState.HEALTHY
        self.hook_bars: int = 0


class VisionAnalyzer:
    """
    Analyse les 4 portraits via un classifieur SVM HOG unique.

    Pipeline :
      1. Classifieur SVM (assets/state_clf.joblib) → état détecté
      2. Sinon → HEALTHY par défaut

    Entraîner le modèle via Entrainement/train_classifier.ipynb.
    """

    def __init__(self):
        self._clf = self._load_classifier()
        if self._clf:
            print(f"[VisionAnalyzer] Classifieur chargé — états : {self._clf['states']}")
        else:
            print("[VisionAnalyzer] Pas de classifieur — tout affiché HEALTHY")

    def _load_classifier(self):
        if os.path.exists(_CLASSIFIER_PATH):
            try:
                return joblib.load(_CLASSIFIER_PATH)
            except Exception as e:
                print(f"[VisionAnalyzer] Erreur chargement : {e}")
        return None

    def reload(self):
        self._clf = self._load_classifier()

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

        if self._clf:
            features   = extract_hog(center_roi)
            pred       = self._clf["model"].predict([features])[0]
            snap.state = self._clf["states"][pred]

        snap.hook_bars = self._count_white_bars(roi)
        return snap

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

            clf_pred, clf_conf = SurvivorState.HEALTHY, 0.0
            if self._clf:
                features  = extract_hog(center_roi)
                pred      = self._clf["model"].predict([features])[0]
                proba     = self._clf["model"].predict_proba([features])[0]
                clf_pred  = self._clf["states"][pred]
                clf_conf  = round(float(max(proba)), 3)

            snap = self._analyze_portrait(roi)

            debug_list.append({
                "survivor":  i + 1,
                "state":     snap.state,
                "clf_pred":  clf_pred,
                "clf_conf":  clf_conf,
                "hook_bars": snap.hook_bars,
            })

        return debug_list
