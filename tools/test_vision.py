"""
Outil de debug vision.
Affiche en temps réel l'état détecté de chaque portrait avec les scores de matching.
Appuie sur Q pour quitter.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import numpy as np
import time
from vision.capture import ScreenCapture
from vision.analyzer import VisionAnalyzer
from core.config import PORTRAIT_POSITIONS

STATE_COLORS = {
    "healthy":      (200, 255, 200),
    "injured":      (100, 100, 255),
    "deep_wounds":  (100, 255, 255),
    "downed":       (50,  50,  200),
    "carried":      (50,  150, 255),
    "hooked":       (50,  255, 150),
    "dead":         (80,  80,  80),
    "escaped":      (50,  255, 50),
    "disconnected": (60,  60,  60),
    "trapped":      (50,  200, 255),
}


def draw_debug_panel(frame: np.ndarray, debug_list: list) -> np.ndarray:
    roi_h, roi_w = frame.shape[:2]
    scale   = 3
    display = cv2.resize(frame, (roi_w * scale, roi_h * scale), interpolation=cv2.INTER_NEAREST)
    panel   = np.zeros((roi_h * scale, 320, 3), dtype=np.uint8)

    for i, info in enumerate(debug_list):
        if not info:
            continue
        y_base = i * (roi_h * scale // 4) + 10
        state  = info.get("state", "?")
        color  = STATE_COLORS.get(state, (200, 200, 200))

        clf_pred = info.get("clf_pred")
        clf_conf = info.get("clf_conf", 0.0)
        clf_str  = f"{clf_pred}({clf_conf:.2f})" if clf_pred else "no model"

        lines = [
            f"S{i+1}: {state.upper()}",
            f"  tmpl={info.get('icon_match','none')} ({info.get('icon_score',0):.3f})",
            f"  clf={clf_str}",
            f"  hooks={info.get('hook_bars',0)}",
        ]
        for j, line in enumerate(lines):
            cv2.putText(panel, line, (4, y_base + j * 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1)

    for i, pos in enumerate(PORTRAIT_POSITIONS):
        x1, y1 = pos["x"] * scale, pos["y"] * scale
        x2, y2 = x1 + pos["w"] * scale, y1 + pos["h"] * scale
        state  = debug_list[i].get("state", "") if debug_list[i] else ""
        cv2.rectangle(display, (x1, y1), (x2, y2), STATE_COLORS.get(state, (200, 200, 200)), 2)

    return np.hstack([display, panel])


def main():
    cap    = ScreenCapture()
    vision = VisionAnalyzer()
    print("Vision debug en temps réel. Q pour quitter.")
    fps_times = []

    while True:
        t0         = time.time()
        frame      = cap.capture_raw()
        debug_list = vision.get_debug_info(frame)

        fps_times.append(time.time() - t0)
        if len(fps_times) > 20:
            fps_times.pop(0)
        fps = 1.0 / (sum(fps_times) / len(fps_times)) if fps_times else 0

        combined = draw_debug_panel(frame, debug_list)
        cv2.putText(combined, f"FPS: {fps:.1f}", (4, combined.shape[0] - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)

        cv2.imshow("DBD Vision Debug — Q pour quitter", combined)
        if cv2.waitKey(50) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
