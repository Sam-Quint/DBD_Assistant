"""
Outil de calibration ROI.
Affiche en temps réel la zone capturée avec les rectangles des portraits.
Appuie sur Q pour quitter.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
from capture import ScreenCapture
from config import PORTRAIT_POSITIONS


def main():
    cap = ScreenCapture()
    print("Affichage de la ROI en temps réel. Appuie sur Q pour quitter.")

    while True:
        frame = cap.capture_raw()
        display = frame.copy()

        for i, pos in enumerate(PORTRAIT_POSITIONS):
            x, y, w, h = pos["x"], pos["y"], pos["w"], pos["h"]
            cv2.rectangle(display, (x, y), (x+w, y+h), (0, 255, 0), 1)
            cv2.putText(display, f"S{i+1}", (x+2, y+12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        h_roi, w_roi = display.shape[:2]
        display = cv2.resize(display, (w_roi * 2, h_roi * 2), interpolation=cv2.INTER_NEAREST)

        cv2.imshow("DBD Capture ROI — Q pour quitter", display)
        if cv2.waitKey(100) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
