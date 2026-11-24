import cv2
import numpy as np
from core.config import PORTRAIT_POSITIONS
from core.state import SurvivorState
from vision.status_recognizer import StatusRecognizer


class SurvivorSnapshot:
    def __init__(self):
        self.state: str     = SurvivorState.HEALTHY
        self.hook_bars: int = 0


class VisionAnalyzer:
    """
    Analyse les 4 portraits par règles (aucun modèle appris).

    Pipeline (voir vision/status_recognizer.py) :
      1. Griffures                      → injured
      2. Pictogramme blanc (forme)      → downed / carried / hooked / dead / escaped
      3. Sinon                          → healthy
    """

    def __init__(self):
        self._recognizer = StatusRecognizer()
        print("[VisionAnalyzer] Reconnaissance par règles chargée")

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

        snap.state, _ = self._recognizer.classify_bgr(roi)
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

            state, score = self._recognizer.classify_bgr(roi)
            debug_list.append({
                "survivor":  i + 1,
                "state":     state,
                "score":     round(float(score), 3),
                "hook_bars": self._count_white_bars(roi),
            })

        return debug_list
