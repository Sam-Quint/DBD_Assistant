"""
Réglage automatique de la zone des portraits.

1. Lance la partie (les 4 portraits doivent être visibles), puis lance ce script
2. Choisis l'écran, confirme la résolution (détectée automatiquement)
3. Les 4 cadres sont calculés ; vérifie-les sur l'aperçu et ajuste si besoin :
      flèches / ZQSD ou WASD : décaler        + / - : agrandir / réduire l'interface
      R : remettre à zéro     ENTREE : sauvegarder     Q : quitter sans sauvegarder
   L'état reconnu s'affiche sous chaque cadre : c'est le meilleur test que le réglage est bon.
"""
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import cv2
import numpy as np

from core.layout import PRESETS, compute_layout
from core.paths import app_dir
try:
    from calibrer_roi import capture_monitor, choose_monitor, list_monitors
except ImportError:   # exécutable packagé : le module est dans le paquet tools
    from tools.calibrer_roi import capture_monitor, choose_monitor, list_monitors

CALIB_PATH = os.path.join(app_dir(), "calibration.json")

STATE_COLORS = {   # BGR
    "healthy": (80, 200, 80), "injured": (60, 60, 255), "downed": (0, 140, 255),
    "carried": (255, 120, 200), "hooked": (255, 160, 60), "dead": (180, 180, 180),
    "escaped": (255, 255, 0),
}


def ratio_label(width: int, height: int) -> str:
    g = math.gcd(width, height)
    w, h = width // g, height // g
    known = {(16, 9): "16:9", (8, 5): "16:10", (64, 27): "21:9", (43, 18): "21:9", (4, 3): "4:3"}
    return known.get((w, h), f"{w}:{h}")


def ask_resolution(monitor: dict) -> tuple[int, int]:
    """Résolution du jeu : celle de l'écran par défaut, sinon un préréglage ou une saisie 'LxH'."""
    detected = (monitor["width"], monitor["height"])
    print(f"\nRésolution détectée : {detected[0]}x{detected[1]} ({ratio_label(*detected)})")
    print("  ENTREE = garder cette résolution, ou choisis :")
    presets = list(PRESETS.items())
    for i, (label, _) in enumerate(presets, 1):
        print(f"  [{i}] {label}")
    print("  ou tape une résolution, par ex. 1600x900")
    while True:
        answer = input("Choix : ").strip().lower().replace(" ", "")
        if not answer:
            return detected
        if answer.isdigit() and 1 <= int(answer) <= len(presets):
            return presets[int(answer) - 1][1]
        if "x" in answer:
            try:
                w, h = (int(v) for v in answer.split("x"))
                if w >= 640 and h >= 360:
                    return w, h
            except ValueError:
                pass
        print("  Réponse non reconnue.")


def build_preview(screenshot: np.ndarray, height: int, ui_scale: float, dx: int, dy: int,
                  recognizer=None) -> np.ndarray:
    """Aperçu de la zone des portraits avec les 4 cadres et l'état reconnu."""
    layout = compute_layout(height, ui_scale, dx, dy)
    roi = layout["roi"]
    screen_h, screen_w = screenshot.shape[:2]

    view = screenshot.copy()
    cv2.rectangle(view, (roi["x"], roi["y"]), (roi["x"] + roi["w"], roi["y"] + roi["h"]), (0, 255, 255), 1)
    for i, pos in enumerate(layout["positions"]):
        x, y = roi["x"] + pos["x"], roi["y"] + pos["y"]
        state, color = "", (0, 0, 255)
        crop = screenshot[max(y, 0):y + pos["h"], max(x, 0):x + pos["w"]]
        if recognizer is not None and crop.size:
            state, _ = recognizer.classify_bgr(crop)
            color = STATE_COLORS.get(state, color)
        cv2.rectangle(view, (x, y), (x + pos["w"], y + pos["h"]), color, 2)
        label, origin, scale = f"S{i+1} {state}", (x + pos["w"] + 6, y + 14), max(0.4, height / 1800)
        cv2.putText(view, label, origin, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(view, label, origin, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)

    # zone affichée : bande gauche autour des portraits
    x0, x1 = 0, min(screen_w, int(height * 0.45))
    y0, y1 = max(0, roi["y"] - int(height * 0.04)), min(screen_h, roi["y"] + roi["h"] + int(height * 0.04))
    crop = view[y0:y1, x0:x1]
    zoom = min(1000 / crop.shape[0], 1.6 if height <= 1080 else 1.0)
    crop = cv2.resize(crop, None, fx=zoom, fy=zoom, interpolation=cv2.INTER_AREA if zoom < 1 else cv2.INTER_LINEAR)

    lines = [f"{screen_w}x{screen_h}  interface x{ui_scale:.2f}  decalage {dx:+d},{dy:+d}",
             "fleches/WASD: decaler   +/-: echelle   R: reset",
             "ENTREE: sauvegarder   Q: quitter"]
    banner = np.zeros((18 * len(lines) + 8, max(crop.shape[1], 430), 3), np.uint8)
    for i, t in enumerate(lines):
        cv2.putText(banner, t, (6, 18 + 18 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    canvas = np.zeros((crop.shape[0] + banner.shape[0], banner.shape[1], 3), np.uint8)
    canvas[:crop.shape[0], :crop.shape[1]] = crop
    canvas[crop.shape[0]:] = banner
    return canvas


KEYS = {  # waitKeyEx (Windows) : flèches
    2424832: (-1, 0), 2555904: (1, 0), 2490368: (0, -1), 2621440: (0, 1),
    ord("a"): (-1, 0), ord("d"): (1, 0), ord("w"): (0, -1), ord("s"): (0, 1),
    ord("q"): None,
}


def main():
    monitor = choose_monitor(list_monitors())
    width, height = ask_resolution(monitor)
    print(f"\nRésolution du jeu : {width}x{height} ({ratio_label(width, height)})")
    print("Affiche la partie avec les 4 portraits visibles. Capture dans 3 secondes...")
    time.sleep(3)
    screenshot = capture_monitor(monitor)

    try:
        from vision.status_recognizer import StatusRecognizer
        recognizer = StatusRecognizer()
    except Exception as e:  # l'aperçu reste utilisable sans la reconnaissance
        print(f"(reconnaissance indisponible : {e})")
        recognizer = None

    ui_scale, dx, dy = 1.0, 0, 0
    if os.path.exists(CALIB_PATH):
        try:
            old = json.load(open(CALIB_PATH)).get("layout", {})
            if old.get("height") == height:
                ui_scale, dx, dy = old.get("ui_scale", 1.0), old.get("dx", 0), old.get("dy", 0)
                print("Réglage précédent rechargé.")
        except (OSError, ValueError):
            pass

    win = "Reglage automatique - ENTREE pour sauvegarder"
    cv2.namedWindow(win)
    while True:
        cv2.imshow(win, build_preview(screenshot, height, ui_scale, dx, dy, recognizer))
        key = cv2.waitKeyEx(50)
        if key == -1:
            continue
        if key in (ord("q"), 27):
            print("Annulé.")
            break
        if key in (13, 10):
            data = {
                "monitor": {k: monitor[k] for k in ("left", "top", "width", "height")},
                "layout": {"width": width, "height": height,
                           "ui_scale": round(ui_scale, 3), "dx": dx, "dy": dy},
            }
            with open(CALIB_PATH, "w") as f:
                json.dump(data, f, indent=2)
            roi = compute_layout(height, ui_scale, dx, dy)["roi"]
            print(f"Réglage sauvegardé : {width}x{height}, interface x{ui_scale:.2f}, décalage {dx:+d},{dy:+d}")
            print(f"  Zone capturée : x={roi['x']} y={roi['y']} w={roi['w']} h={roi['h']}")
            break
        if key in (ord("+"), ord("=")):
            ui_scale = min(2.0, round(ui_scale + 0.01, 3))
        elif key in (ord("-"), ord("_")):
            ui_scale = max(0.5, round(ui_scale - 0.01, 3))
        elif key in (ord("r"), ord("R")):
            ui_scale, dx, dy = 1.0, 0, 0
        elif key in KEYS and KEYS[key]:
            step = KEYS[key]
            dx, dy = dx + step[0], dy + step[1]

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
