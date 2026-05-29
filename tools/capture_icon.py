"""
Outil de capture des icônes centrales (templates).
Affiche la zone centrale de chaque portrait en temps réel.

Touches :
  1-4 : sélectionner le survivant à capturer
  d   : sauvegarder icon_downed.png     (à terre)
  c   : sauvegarder icon_carried.png    (porté)
  h   : sauvegarder icon_hooked.png     (accroché)
  x   : sauvegarder icon_dead.png       (mort)
  e   : sauvegarder icon_escaped.png    (sorti)
  z   : sauvegarder icon_disconnected.png
  q   : quitter
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import numpy as np
from capture import ScreenCapture
from config import PORTRAIT_POSITIONS, ASSETS_DIR

ICON_KEYS = {
    ord("d"): "icon_downed.png",
    ord("c"): "icon_carried.png",
    ord("h"): "icon_hooked.png",
    ord("x"): "icon_dead.png",
    ord("e"): "icon_escaped.png",
    ord("z"): "icon_disconnected.png",
}

ASSETS_PATH = os.path.join(os.path.dirname(__file__), "..", ASSETS_DIR)


def get_center_roi(portrait_roi: np.ndarray) -> np.ndarray:
    h, w = portrait_roi.shape[:2]
    cy1, cy2 = h // 4, 3 * h // 4
    cx1, cx2 = w // 4, 3 * w // 4
    return portrait_roi[cy1:cy2, cx1:cx2]


def main():
    cap = ScreenCapture()
    selected = 0

    print(__doc__)
    print(f"Assets dir : {ASSETS_PATH}")

    while True:
        frame = cap.capture_raw()
        pos = PORTRAIT_POSITIONS[selected]
        portrait = frame[pos["y"]:pos["y"]+pos["h"], pos["x"]:pos["x"]+pos["w"]]
        center = get_center_roi(portrait)

        scale = 8
        display_portrait = cv2.resize(portrait, (pos["w"]*scale, pos["h"]*scale),
                                       interpolation=cv2.INTER_NEAREST)
        ch, cw = center.shape[:2]
        display_center = cv2.resize(center, (cw*scale, ch*scale),
                                     interpolation=cv2.INTER_NEAREST)

        x1 = pos["w"]//4 * scale
        y1 = pos["h"]//4 * scale
        x2 = 3*pos["w"]//4 * scale
        y2 = 3*pos["h"]//4 * scale
        cv2.rectangle(display_portrait, (x1, y1), (x2, y2), (0, 255, 255), 2)
        cv2.putText(display_portrait, f"S{selected+1}", (4, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        combined = np.hstack([display_portrait, display_center])
        cv2.imshow("Capture Icon — voir instructions dans la console", combined)

        key = cv2.waitKey(50) & 0xFF

        if key == ord("q"):
            break

        for i, k in enumerate([ord("1"), ord("2"), ord("3"), ord("4")]):
            if key == k:
                selected = i
                print(f"Survivant {selected+1} sélectionné")

        if key in ICON_KEYS:
            filename = ICON_KEYS[key]
            out_path = os.path.join(ASSETS_PATH, filename)
            cv2.imwrite(out_path, center)
            print(f"Sauvegardé : {out_path}")

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
