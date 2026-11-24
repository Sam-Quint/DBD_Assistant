"""
Outil de calibration interactive de la ROI.

1. Lance le jeu en arrière-plan
2. Lance ce script
3. Sélectionne l'écran où tourne le jeu
4. Clique-glisse pour encadrer la zone des 4 portraits
5. Appuie sur ENTREE pour sauvegarder, Q pour quitter sans sauvegarder
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import numpy as np
import mss
import json

from core.paths import app_dir

CALIB_PATH = os.path.join(app_dir(), "calibration.json")

drawing = False
start_x = start_y = end_x = end_y = 0
rect_done = False


def list_monitors():
    with mss.mss() as sct:
        # monitors[0] = écran virtuel (tous), monitors[1..n] = écrans individuels
        return sct.monitors[1:]


def capture_monitor(monitor_info: dict) -> np.ndarray:
    with mss.mss() as sct:
        raw = sct.grab(monitor_info)
        return np.array(raw)[:, :, :3]


def choose_monitor(monitors: list) -> dict:
    """Affiche une fenêtre avec un aperçu de chaque écran pour sélection."""
    print(f"\n{len(monitors)} écran(s) détecté(s) :")
    for i, m in enumerate(monitors):
        print(f"  [{i+1}] {m['width']}x{m['height']} à ({m['left']}, {m['top']})")

    if len(monitors) == 1:
        print("Un seul écran, sélection automatique.")
        return monitors[0]

    # Aperçus réduits côte à côte
    previews = []
    thumb_w, thumb_h = 400, 225
    for i, m in enumerate(monitors):
        img = capture_monitor(m)
        thumb = cv2.resize(img, (thumb_w, thumb_h))
        label = f"  Ecran {i+1} : {m['width']}x{m['height']}"
        cv2.putText(thumb, label, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
        cv2.putText(thumb, f"  Appuie sur {i+1}", (8, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
        previews.append(thumb)

    combined = np.hstack(previews)
    cv2.imshow("Quel ecran contient le jeu ? Appuie sur 1, 2, 3...", combined)

    selected = None
    while selected is None:
        key = cv2.waitKey(0) & 0xFF
        for i in range(len(monitors)):
            if key == ord(str(i + 1)):
                selected = i
                break
        if key == ord("q"):
            cv2.destroyAllWindows()
            sys.exit(0)

    cv2.destroyAllWindows()
    print(f"Écran {selected + 1} sélectionné.")
    return monitors[selected]


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

    monitors = list_monitors()
    monitor = choose_monitor(monitors)

    print("\nCapture de l'écran en cours...")
    screenshot = capture_monitor(monitor)
    screen_h, screen_w = screenshot.shape[:2]

    scale = min(1.0, 1280 / screen_w)
    display_w = int(screen_w * scale)
    display_h = int(screen_h * scale)

    # Pré-remplir depuis calibration existante
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
            print(f"Calibration existante chargée : {roi}")

    win = "Calibration ROI — ENTREE pour sauvegarder, Q pour quitter"
    cv2.namedWindow(win)
    cv2.setMouseCallback(win, mouse_callback)

    base = cv2.resize(screenshot, (display_w, display_h))

    print("\nClique et glisse pour encadrer la zone des 4 portraits des survivants.")
    print("Appuie sur ENTREE pour sauvegarder, Q pour quitter.\n")

    while True:
        display = base.copy()

        overlay = display.copy()
        cv2.rectangle(overlay, (0, 0), (display_w, display_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.35, display, 0.65, 0, display)

        x1, y1 = min(start_x, end_x), min(start_y, end_y)
        x2, y2 = max(start_x, end_x), max(start_y, end_y)

        if x2 > x1 and y2 > y1:
            display[y1:y2, x1:x2] = base[y1:y2, x1:x2]
            color = (0, 255, 0) if rect_done else (0, 200, 255)
            cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)

            real_x = int(x1 / scale)
            real_y = int(y1 / scale)
            real_w = int((x2 - x1) / scale)
            real_h = int((y2 - y1) / scale)
            info = f"x={real_x}  y={real_y}  w={real_w}  h={real_h}"
            cv2.putText(display, info, (x1, max(y1 - 8, 16)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)

        instructions = [
            "Encadre la zone des 4 portraits (haut gauche du jeu)",
            "ENTREE = sauvegarder   Q = quitter sans sauvegarder",
        ]
        for i, txt in enumerate(instructions):
            cv2.putText(display, txt, (10, display_h - 30 + i * 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.imshow(win, display)
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
                "monitor": {
                    "left":   monitor["left"],
                    "top":    monitor["top"],
                    "width":  monitor["width"],
                    "height": monitor["height"],
                },
                "portraits_roi": {
                    "x": real_x,
                    "y": real_y,
                    "w": real_w,
                    "h": real_h,
                }
            }
            with open(CALIB_PATH, "w") as f:
                json.dump(data, f, indent=2)

            print(f"Calibration sauvegardée :")
            print(f"  Écran : {monitor['width']}x{monitor['height']} à ({monitor['left']}, {monitor['top']})")
            print(f"  ROI   : x={real_x}, y={real_y}, w={real_w}, h={real_h}")
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
