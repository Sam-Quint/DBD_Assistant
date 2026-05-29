"""
Outil de calibration interactive de la ROI.

1. Lance le jeu en arrière-plan
2. Lance ce script
3. Clique-glisse pour encadrer la zone des 4 portraits
4. Appuie sur ENTREE pour sauvegarder, Q pour quitter sans sauvegarder

Le résultat est sauvegardé dans calibration.json et chargé automatiquement au démarrage.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import numpy as np
import mss
import json

CALIB_PATH = os.path.join(os.path.dirname(__file__), "..", "calibration.json")
drawing = False
start_x = start_y = end_x = end_y = 0
rect_done = False


def capture_fullscreen() -> np.ndarray:
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # écran principal
        raw = sct.grab(monitor)
        return np.array(raw)[:, :, :3]


def mouse_callback(event, x, y, flags, param):
    global drawing, start_x, start_y, end_x, end_y, rect_done

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        rect_done = False
        start_x, start_y = x, y
        end_x, end_y = x, y

    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        end_x, end_y = x, y

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        end_x, end_y = x, y
        rect_done = True


def main():
    global start_x, start_y, end_x, end_y, rect_done

    print("Capture de l'écran en cours...")
    screenshot = capture_fullscreen()
    screen_h, screen_w = screenshot.shape[:2]

    # Réduire pour afficher sur l'écran (max 1280px de large)
    scale = min(1.0, 1280 / screen_w)
    display_w = int(screen_w * scale)
    display_h = int(screen_h * scale)

    # Charger calibration existante pour pré-remplir
    roi_exists = False
    if os.path.exists(CALIB_PATH):
        with open(CALIB_PATH) as f:
            data = json.load(f)
        roi = data.get("portraits_roi", {})
        if roi:
            start_x = int(roi["x"] * scale)
            start_y = int(roi["y"] * scale)
            end_x = int((roi["x"] + roi["w"]) * scale)
            end_y = int((roi["y"] + roi["h"]) * scale)
            rect_done = True
            roi_exists = True
            print(f"Calibration existante chargée : {roi}")

    cv2.namedWindow("Calibration ROI — ENTREE pour sauvegarder, Q pour quitter")
    cv2.setMouseCallback("Calibration ROI — ENTREE pour sauvegarder, Q pour quitter", mouse_callback)

    base = cv2.resize(screenshot, (display_w, display_h))

    print("\nClique et glisse pour encadrer la zone des 4 portraits des survivants.")
    print("Appuie sur ENTREE pour sauvegarder, Q pour quitter.\n")

    while True:
        display = base.copy()

        # Overlay sombre sur tout l'écran
        overlay = display.copy()
        cv2.rectangle(overlay, (0, 0), (display_w, display_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.35, display, 0.65, 0, display)

        x1, y1 = min(start_x, end_x), min(start_y, end_y)
        x2, y2 = max(start_x, end_x), max(start_y, end_y)

        if x2 > x1 and y2 > y1:
            # Zone sélectionnée en clair
            display[y1:y2, x1:x2] = base[y1:y2, x1:x2]
            color = (0, 255, 0) if rect_done else (0, 200, 255)
            cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)

            # Infos de la sélection en coordonnées réelles
            real_x = int(x1 / scale)
            real_y = int(y1 / scale)
            real_w = int((x2 - x1) / scale)
            real_h = int((y2 - y1) / scale)
            info = f"x={real_x}  y={real_y}  w={real_w}  h={real_h}"
            cv2.putText(display, info, (x1, max(y1 - 8, 16)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)

        # Instructions
        instructions = [
            "Encadre la zone des 4 portraits (haut gauche du jeu)",
            "ENTREE = sauvegarder   Q = quitter sans sauvegarder",
        ]
        for i, txt in enumerate(instructions):
            cv2.putText(display, txt, (10, display_h - 30 + i * 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.imshow("Calibration ROI — ENTREE pour sauvegarder, Q pour quitter", display)
        key = cv2.waitKey(30) & 0xFF

        if key == ord("q"):
            print("Annulé.")
            break

        if key == 13 and rect_done and x2 > x1 and y2 > y1:  # ENTREE
            real_x = int(x1 / scale)
            real_y = int(y1 / scale)
            real_w = int((x2 - x1) / scale)
            real_h = int((y2 - y1) / scale)

            data = {
                "portraits_roi": {
                    "x": real_x,
                    "y": real_y,
                    "w": real_w,
                    "h": real_h,
                }
            }
            with open(CALIB_PATH, "w") as f:
                json.dump(data, f, indent=2)

            print(f"Calibration sauvegardée dans calibration.json :")
            print(f"  x={real_x}, y={real_y}, w={real_w}, h={real_h}")
            print("\nRelance test_capture.py pour vérifier.")
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
