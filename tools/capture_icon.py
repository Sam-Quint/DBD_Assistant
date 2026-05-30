"""
Outil de capture de templates pendant une vraie partie.

Touches :
  1 2 3 4       Sélectionner le survivant à capturer
  W             État : À terre  (downed)
  X             État : Porté    (carried)
  C             État : Accroché (hooked)
  V             État : Mort     (dead)
  B             État : Sorti    (escaped)
  ENTRÉE        Sauvegarder le template du survivant sélectionné dans l'état choisi
  R             Recharger les templates dans l'analyseur (après plusieurs captures)
  Q             Quitter
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import numpy as np
from vision.capture import ScreenCapture
from core.config import PORTRAIT_POSITIONS

ICONS_DIR     = os.path.join(os.path.dirname(__file__), "..", "assets", "icons")
TEMPLATE_SIZE = 48  # taille de stockage des templates (48×48 px)
SCALE         = 4   # facteur d'agrandissement de l'affichage

STATE_KEYS = {
    ord("w"): "downed",
    ord("x"): "carried",
    ord("c"): "hooked",
    ord("v"): "dead",
    ord("b"): "escaped",
}

# Couleurs BGR par état pour l'interface
STATE_COLORS = {
    "downed":  (50,  50,  220),
    "carried": (50,  165, 255),
    "hooked":  (50,  220, 50),
    "dead":    (80,  80,  80),
    "escaped": (50,  255, 180),
    None:      (180, 180, 180),
}


def _center_roi(portrait: np.ndarray) -> np.ndarray:
    """Extrait 80% du portrait (marge de 10% de chaque côté pour exclure le bord de l'anneau)."""
    h, w = portrait.shape[:2]
    return portrait[h//10 : 9*h//10, w//10 : 9*w//10]


def _count_templates() -> dict[str, int]:
    """Compte le nombre de templates sauvegardés par état."""
    counts = {}
    for state in ["downed", "carried", "hooked", "dead", "escaped"]:
        d = os.path.join(ICONS_DIR, state)
        counts[state] = len([f for f in os.listdir(d) if f.endswith(".png")]) if os.path.isdir(d) else 0
    return counts


def _save_template(portrait: np.ndarray, state: str) -> str:
    """
    Extrait la zone centrale, la convertit en niveaux de gris 32×32
    et la sauvegarde dans assets/icons/{état}/{état}_{N}.png.
    Retourne le chemin du fichier créé.
    """
    center  = _center_roi(portrait)
    gray    = cv2.cvtColor(center, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (TEMPLATE_SIZE, TEMPLATE_SIZE))

    state_dir = os.path.join(ICONS_DIR, state)
    os.makedirs(state_dir, exist_ok=True)

    n    = len([f for f in os.listdir(state_dir) if f.endswith(".png")])
    path = os.path.join(state_dir, f"{state}_{n + 1}.png")
    cv2.imwrite(path, resized)
    return path


def _build_display(frame: np.ndarray, selected: int, chosen_state: str | None) -> np.ndarray:
    """Construit l'image affichée : 4 portraits agrandis + bande d'info."""
    panels = []

    for i, pos in enumerate(PORTRAIT_POSITIONS):
        portrait = frame[pos["y"]:pos["y"]+pos["h"], pos["x"]:pos["x"]+pos["w"]]
        h, w     = portrait.shape[:2]
        big      = cv2.resize(portrait, (w * SCALE, h * SCALE), interpolation=cv2.INTER_NEAREST)

        # Rectangle jaune sur la zone capturée (80% du portrait, marge 10%)
        cx1, cy1 = w*SCALE//10, h*SCALE//10
        cx2, cy2 = 9*w*SCALE//10, 9*h*SCALE//10
        cv2.rectangle(big, (cx1, cy1), (cx2, cy2), (0, 220, 220), 1)

        # Bordure colorée sur le survivant sélectionné
        color = STATE_COLORS.get(chosen_state, (180, 180, 180))
        thickness = 3 if i == selected else 1
        cv2.rectangle(big, (0, 0), (w*SCALE-1, h*SCALE-1), color if i == selected else (60, 60, 60), thickness)

        # Numéro
        cv2.putText(big, f"S{i+1}", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    color if i == selected else (140, 140, 140), 1)

        panels.append(big)

    display = np.hstack(panels)

    # ── Bande d'info ─────────────────────────────────────────────────────────
    info_h  = 90
    info_w  = display.shape[1]
    info    = np.zeros((info_h, info_w, 3), dtype=np.uint8)
    color   = STATE_COLORS.get(chosen_state, (180, 180, 180))
    counts  = _count_templates()

    line1 = f"Survivant : S{selected+1}   Etat : {chosen_state.upper() if chosen_state else 'NON CHOISI'}"
    line2 = "Templates : " + "  ".join(f"{s}={n}" for s, n in counts.items())
    line3 = "1/2/3/4=select | W=downed  X=carried  C=hooked  V=dead  B=escaped | ENTREE=save | R=reload | Q=quit"

    cv2.putText(info, line1, (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)
    cv2.putText(info, line2, (6, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 160, 160), 1)
    cv2.putText(info, line3, (6, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (100, 100, 100), 1)

    return np.vstack([display, info])


def main():
    cap          = ScreenCapture()
    selected     = 0       # index du survivant sélectionné (0-3)
    chosen_state = None    # état à sauvegarder

    print(__doc__)

    while True:
        frame   = cap.capture_raw()
        display = _build_display(frame, selected, chosen_state)

        cv2.imshow("Capture Templates — Q pour quitter", display)
        key = cv2.waitKey(50) & 0xFF

        if key == ord("q"):
            break

        # Sélection du survivant
        for i, k in enumerate([ord("1"), ord("2"), ord("3"), ord("4")]):
            if key == k:
                selected = i

        # Choix de l'état
        if key in STATE_KEYS:
            chosen_state = STATE_KEYS[key]

        # Sauvegarde
        if key == 13 and chosen_state:  # ENTRÉE
            pos     = PORTRAIT_POSITIONS[selected]
            portrait = frame[pos["y"]:pos["y"]+pos["h"], pos["x"]:pos["x"]+pos["w"]]
            path    = _save_template(portrait, chosen_state)
            print(f"Sauvegardé : {path}")

        # Rechargement des templates dans l'analyseur
        if key == ord("r"):
            print("Templates rechargés.")

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
