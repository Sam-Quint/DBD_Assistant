import mss
import numpy as np
from core.config import PORTRAITS_ROI, MONITOR_OVERRIDE

# Si la différence pixel moyenne entre deux frames est inférieure à ce seuil,
# la frame est considérée identique → on skip l'analyse (économie CPU)
DELTA_THRESHOLD = 3.0


def _build_monitor() -> dict:
    """
    Construit la région à capturer pour mss.
    Si un moniteur spécifique a été calibré, on décale les coordonnées
    par rapport à son coin haut-gauche (gestion multi-écrans).
    """
    if MONITOR_OVERRIDE:
        return {
            "top":    MONITOR_OVERRIDE["top"]  + PORTRAITS_ROI["y"],
            "left":   MONITOR_OVERRIDE["left"] + PORTRAITS_ROI["x"],
            "width":  PORTRAITS_ROI["w"],
            "height": PORTRAITS_ROI["h"],
        }
    return {
        "top":    PORTRAITS_ROI["y"],
        "left":   PORTRAITS_ROI["x"],
        "width":  PORTRAITS_ROI["w"],
        "height": PORTRAITS_ROI["h"],
    }


class ScreenCapture:
    def __init__(self):
        self.sct = mss.mss()
        self.last_frame = None
        self.monitor = _build_monitor()

    def capture(self) -> np.ndarray | None:
        """
        Capture la zone des portraits.
        Retourne la frame BGR si un changement est détecté, None sinon.
        """
        raw = self.sct.grab(self.monitor)
        frame = np.array(raw)[:, :, :3]  # BGRA → BGR

        if self.last_frame is not None:
            diff = np.mean(np.abs(frame.astype(float) - self.last_frame.astype(float)))
            if diff < DELTA_THRESHOLD:
                return None

        self.last_frame = frame.copy()
        return frame

    def capture_raw(self) -> np.ndarray:
        """Retourne toujours la frame courante (pour les outils de calibration)."""
        raw = self.sct.grab(self.monitor)
        return np.array(raw)[:, :, :3]
