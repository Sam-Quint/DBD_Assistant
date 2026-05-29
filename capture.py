import mss
import numpy as np
from config import PORTRAITS_ROI

DELTA_THRESHOLD = 3.0


class ScreenCapture:
    def __init__(self):
        self.sct = mss.mss()
        self.last_frame = None
        self.monitor = {
            "top":    PORTRAITS_ROI["y"],
            "left":   PORTRAITS_ROI["x"],
            "width":  PORTRAITS_ROI["w"],
            "height": PORTRAITS_ROI["h"],
        }

    def capture(self) -> np.ndarray | None:
        """Retourne la frame BGR si un changement est détecté, None sinon."""
        raw = self.sct.grab(self.monitor)
        frame = np.array(raw)[:, :, :3]  # BGR, sans canal alpha

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
