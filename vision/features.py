import cv2
import numpy as np

FEATURE_SIZE = 48   # portraits redimensionnés à 48x48 avant extraction
HOG_CELL     = 6    # pixels par cellule HOG
HOG_BINS     = 9    # bins d'orientation (0-180°)


def extract_hog(img: np.ndarray) -> np.ndarray:
    """
    Extrait un vecteur HOG depuis un portrait BGR ou niveaux de gris.
    Utilisé à la fois dans le notebook d'entraînement et dans analyzer.py.
    Les griffures diagonales créent des gradients orientés distinctifs.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    gray = cv2.resize(gray, (FEATURE_SIZE, FEATURE_SIZE)).astype(np.float32)

    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = np.sqrt(gx ** 2 + gy ** 2)
    angle     = np.arctan2(gy, gx) * 180.0 / np.pi % 180.0

    n_cells = FEATURE_SIZE // HOG_CELL
    hists   = []
    for cy in range(n_cells):
        for cx in range(n_cells):
            y1, y2 = cy * HOG_CELL, (cy + 1) * HOG_CELL
            x1, x2 = cx * HOG_CELL, (cx + 1) * HOG_CELL
            hist, _ = np.histogram(
                angle[y1:y2, x1:x2],
                bins=HOG_BINS, range=(0, 180),
                weights=magnitude[y1:y2, x1:x2]
            )
            hists.append(hist)

    features = np.concatenate(hists)
    norm     = np.linalg.norm(features)
    return features / (norm + 1e-6)
