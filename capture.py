import mss
import numpy as np
from config import PORTRAITS_ROI, MONITOR_OVERRIDE

DELTA_THRESHOLD = 3.0


def _build_monitor() -> dict:
    """Construit le dict moniteur pour mss en tenant compte de la calibration."""
    if MONITOR_OVERRIDE:
        # Le ROI est relatif au coin supérieur gauche du moniteur sélectionné
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
        """Retourne la frame BGR si un changement est détecté, None sinon."""
        raw = self.sct.grab(self.monitor)
        frame = np.array(raw)[:, :, :3]

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
