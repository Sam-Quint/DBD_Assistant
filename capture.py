import mss
import numpy as np
from config import PORTRAITS_ROI, MONITOR_OVERRIDE

# Seuil de différence de pixel moyen entre deux frames.
# Si la différence est inférieure à ce seuil, la frame est considérée identique
# et on ne lance pas l'analyse (économie de CPU).
DELTA_THRESHOLD = 3.0


def _build_monitor() -> dict:
    """
    Construit le dictionnaire de région à capturer pour mss.

    Si une calibration multi-écrans existe (MONITOR_OVERRIDE), on décale
    les coordonnées du ROI par rapport au coin haut-gauche du bon moniteur.
    Sinon, on capture directement depuis les coordonnées absolues du ROI.
    """
    if MONITOR_OVERRIDE:
        # Les coordonnées du ROI sont relatives au moniteur sélectionné.
        # mss utilise des coordonnées ABSOLUES → on ajoute le décalage du moniteur.
        return {
            "top":    MONITOR_OVERRIDE["top"]  + PORTRAITS_ROI["y"],
            "left":   MONITOR_OVERRIDE["left"] + PORTRAITS_ROI["x"],
            "width":  PORTRAITS_ROI["w"],
            "height": PORTRAITS_ROI["h"],
        }
    # Moniteur principal : les coordonnées sont directement absolues
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
        # Région à capturer, calculée une seule fois au démarrage
        self.monitor = _build_monitor()

    def capture(self) -> np.ndarray | None:
        """
        Capture la zone des portraits et la retourne en BGR.

        Retourne None si la frame est identique à la précédente (pas de changement
        à l'écran), pour éviter d'analyser inutilement des frames statiques.
        Retourne la frame numpy (H×W×3, BGR) si un changement est détecté.
        """
        raw = self.sct.grab(self.monitor)
        # mss retourne BGRA (4 canaux), on garde seulement BGR (3 canaux)
        frame = np.array(raw)[:, :, :3]

        if self.last_frame is not None:
            # Calculer la différence pixel par pixel (valeur moyenne sur toute la frame)
            diff = np.mean(np.abs(frame.astype(float) - self.last_frame.astype(float)))
            if diff < DELTA_THRESHOLD:
                return None  # Frame trop similaire → skip

        self.last_frame = frame.copy()
        return frame

    def capture_raw(self) -> np.ndarray:
        """
        Capture et retourne TOUJOURS la frame courante, sans comparaison.
        Utilisé par les outils de calibration qui ont besoin d'un flux continu.
        """
        raw = self.sct.grab(self.monitor)
        return np.array(raw)[:, :, :3]
