import cv2
import numpy as np
from config import PORTRAIT_POSITIONS
from state import SurvivorState

# ── Snapshot ──────────────────────────────────────────────────────────────────
# Résultat de l'analyse visuelle d'UN portrait à UN instant T.
# Produit par VisionAnalyzer et consommé par StateLogic.
class SurvivorSnapshot:
    def __init__(self):
        self.state: str = SurvivorState.HEALTHY
        self.confidence: float = 0.0   # score de confiance (futur usage)
        self.hook_bars: int = 0        # nombre de barres blanches (0, 1 ou 2)
        self.has_yellow_bar: bool = False


# ── Analyseur visuel ──────────────────────────────────────────────────────────
class VisionAnalyzer:

    def analyze_frame(self, frame: np.ndarray) -> list[SurvivorSnapshot]:
        """
        Analyse les 4 portraits dans la frame capturée.
        Retourne une liste de 4 SurvivorSnapshot (un par survivant).
        """
        snapshots = []
        for pos in PORTRAIT_POSITIONS:
            # Découper le portrait depuis la ROI globale
            roi = frame[pos["y"]:pos["y"]+pos["h"], pos["x"]:pos["x"]+pos["w"]]
            snapshots.append(self._analyze_portrait(roi))
        return snapshots

    def _analyze_portrait(self, roi: np.ndarray) -> SurvivorSnapshot:
        """
        Pipeline de détection d'état pour UN portrait.

        On analyse 4 signaux dans cet ordre de priorité :
          1. Couleur de l'anneau  → mort détecté ici
          2. Intérieur du cercle  → porté / accroché / à terre / sorti
          3. Barre jaune          → Deep Wounds
          4. Griffures rouges     → Blessé vs Bonne santé
        """
        snap = SurvivorSnapshot()
        if roi.size == 0:
            return snap

        h, w = roi.shape[:2]

        # Masque circulaire : on ignore les pixels EN DEHORS du cercle du portrait.
        # Le fond derrière le cercle change selon la map (forêt, feu, etc.),
        # donc on l'exclut de toutes les analyses pour éviter les faux positifs.
        circle_mask = self._make_circle_mask(h, w)
        roi_masked = cv2.bitwise_and(roi, roi, mask=circle_mask)

        # ── Signal 1 : couleur de l'anneau ───────────────────────────────────
        # L'anneau est la bordure colorée du cercle du portrait.
        # Sa couleur change selon l'état : blanc/gris (vivant), cyan (Deep Wounds),
        # très sombre (mort ou déconnecté).
        ring_color = self._sample_ring_color(roi, h, w)

        if ring_color == "dark":
            snap.state = SurvivorState.DEAD
            snap.hook_bars = self._count_white_bars(roi)
            return snap

        # ── Signal 2 : intérieur du cercle ───────────────────────────────────
        # Quand un survivant est dans un état "icône" (porté, accroché, à terre,
        # sorti), son portrait est remplacé par une silhouette/icône sur fond noir.
        # On détecte cela en analysant la luminosité et la forme des pixels.
        icon_state = self._detect_icon_state(roi_masked, circle_mask, h, w)
        if icon_state:
            snap.state = icon_state
            snap.hook_bars = self._count_white_bars(roi)
            return snap

        # ── Signal 3 : barre jaune (Deep Wounds) ─────────────────────────────
        # La barre jaune est visible en bas du portrait quand le survivant est
        # en état "Blessé + Deep Wounds". On la détecte par sa couleur HSV jaune
        # et sa continuité horizontale (au moins 40% de la largeur du portrait).
        has_yellow_bar = self._detect_yellow_bar(roi)
        snap.has_yellow_bar = has_yellow_bar

        if ring_color == "cyan" or has_yellow_bar:
            snap.state = SurvivorState.DEEP_WOUNDS
            snap.hook_bars = self._count_white_bars(roi)
            return snap

        # ── Signal 4 : griffures rouges ──────────────────────────────────────
        # Les griffures apparaissent sur le portrait quand le survivant est blessé.
        # Ce sont des pixels rouge très saturé (S>180 en HSV), distincts du fond
        # de la map qui peut aussi être rouge/orange mais moins saturé.
        if self._detect_red_scratches(roi_masked):
            snap.state = SurvivorState.INJURED
        else:
            snap.state = SurvivorState.HEALTHY

        snap.hook_bars = self._count_white_bars(roi)
        return snap

    # ── Détection des états "icône" ───────────────────────────────────────────

    def _detect_icon_state(self, roi_masked: np.ndarray, circle_mask: np.ndarray, h: int, w: int) -> str | None:
        """
        Détecte les états Porté / Accroché / À terre / Sorti sans template.

        Principe :
        - Un portrait normal (visage du personnage) a une saturation et une
          luminosité moyennes assez élevées (teintes de peau variées, couleurs des vêtements).
        - Un état icône a un FOND NOIR avec une silhouette/icône CLAIRE dessus.
          → Saturation faible + luminosité globale faible.

        Une fois qu'on sait qu'on est dans un état icône, on analyse la FORME
        des pixels clairs pour distinguer les états :
        - Pixels étalés horizontalement → À terre (silhouette allongée)
        - Pixels étalés verticalement + concentrés en haut → Accroché (forme en crochet)
        - Peu ou pas de pixels clairs → Porté (silhouette sombre)
        - Teinte verte détectée → Sorti (icône de porte verte)

        Retourne None si le portrait semble être un visage normal.
        """
        hsv = cv2.cvtColor(roi_masked, cv2.COLOR_BGR2HSV)
        # Récupérer uniquement les pixels à l'intérieur du cercle
        circle_px = hsv[circle_mask == 255]

        if len(circle_px) == 0:
            return None

        mean_sat = float(np.mean(circle_px[:, 1]))  # saturation moyenne
        mean_val = float(np.mean(circle_px[:, 2]))  # luminosité moyenne

        # Un visage normal a saturation > 28 ET luminosité > 95
        # → ce n'est pas un état icône
        if mean_val > 95 and mean_sat > 28:
            return None

        # ── Sorti : teinte verte dominante (icône de porte) ──────────────────
        # La porte de sortie affiche une icône verte/cyan distincte
        green_mask = cv2.inRange(
            hsv,
            np.array([35, 40, 140]),   # teinte : vert-jaune (H=35) à cyan (H=90)
            np.array([90, 255, 255])
        )
        green_ratio = np.sum((green_mask > 0) & (circle_mask == 255)) / max(np.sum(circle_mask == 255), 1)
        if green_ratio > 0.12:  # plus de 12% de pixels verts dans le cercle
            return SurvivorState.ESCAPED

        # ── Isoler les pixels de l'icône (clairs sur fond sombre) ────────────
        # L'icône elle-même (silhouette blanche/grise) est plus lumineuse que le fond noir.
        # On cherche les pixels avec luminosité > 100 et saturation < 80 (gris/blanc).
        icon_mask = cv2.inRange(hsv, np.array([0, 0, 100]), np.array([180, 80, 255]))
        icon_mask = cv2.bitwise_and(icon_mask, circle_mask)

        icon_px = np.where(icon_mask > 0)
        n = len(icon_px[0])

        if n < 12:
            # Très peu de pixels clairs = silhouette à peine visible
            # → Le survivant est porté (la silhouette du carrier est très sombre)
            return SurvivorState.CARRIED

        rows, cols = icon_px

        # Calculer l'étendue horizontale et verticale des pixels de l'icône
        row_spread = int(np.max(rows)) - int(np.min(rows))  # hauteur de l'icône
        col_spread = int(np.max(cols)) - int(np.min(cols))  # largeur de l'icône

        # Rapport largeur/hauteur de l'icône :
        # > 1 = icône plus large que haute (horizontale)
        # < 1 = icône plus haute que large (verticale)
        aspect = col_spread / max(row_spread, 1)

        # Position verticale du centre de masse de l'icône (0 = haut, 1 = bas)
        centroid_y = float(np.mean(rows)) / h

        # À terre : la silhouette allongée est clairement plus large que haute
        if aspect > 1.35:
            return SurvivorState.DOWNED

        # Accroché : le symbole crochet est majoritairement vertical
        # et concentré dans la moitié supérieure du cercle
        if aspect < 0.85 and centroid_y < 0.55:
            return SurvivorState.HOOKED

        # Sinon : Porté (silhouette verticale, position variable)
        return SurvivorState.CARRIED

    # ── Méthodes de détection HSV ─────────────────────────────────────────────

    def _make_circle_mask(self, h: int, w: int) -> np.ndarray:
        """
        Crée un masque binaire en forme de cercle inscrit dans le rectangle h×w.
        Pixels DANS le cercle = 255 (analysés), pixels HORS du cercle = 0 (ignorés).
        Le rayon est légèrement réduit (-2px) pour éviter d'inclure la bordure de l'anneau.
        """
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask, (w // 2, h // 2), min(w, h) // 2 - 2, 255, -1)
        return mask

    def _sample_ring_color(self, roi: np.ndarray, h: int, w: int) -> str:
        """
        Analyse la couleur de l'anneau (bordure du cercle du portrait).

        Méthode : on crée deux cercles (grand et petit), leur XOR donne l'anneau.
        On calcule la teinte (H), saturation (S) et luminosité (V) moyennes.

        Retourne :
        - "dark"  → V < 50 : portrait très sombre = mort ou déconnecté
        - "cyan"  → H ≈ 85-100 et S > 100 : anneau cyan = Deep Wounds actif
        - "white" → tout le reste : état vivant normal
        """
        ring_width = max(3, min(h, w) // 10)  # épaisseur de l'anneau en pixels
        center = (w // 2, h // 2)
        r_out = min(w, h) // 2 - 1
        r_in  = r_out - ring_width

        mo = np.zeros((h, w), dtype=np.uint8)
        mi = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mo, center, r_out, 255, -1)
        cv2.circle(mi, center, r_in,  255, -1)
        # XOR : pixels dans le grand cercle mais PAS dans le petit = l'anneau
        ring_mask = cv2.bitwise_xor(mo, mi)

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        px = hsv[ring_mask == 255]

        if len(px) == 0:
            return "white"

        mean_h = float(np.mean(px[:, 0]))  # teinte (0-180 en OpenCV)
        mean_s = float(np.mean(px[:, 1]))  # saturation (0-255)
        mean_v = float(np.mean(px[:, 2]))  # valeur/luminosité (0-255)

        if mean_v < 50:
            return "dark"
        if 85 <= mean_h <= 100 and mean_s > 100:
            return "cyan"
        return "white"

    def _detect_red_scratches(self, roi_masked: np.ndarray) -> bool:
        """
        Détecte les griffures rouges caractéristiques de l'état Blessé.

        En HSV, le rouge occupe DEUX plages de teinte (H=0-10 et H=170-180)
        à cause de la nature circulaire de la roue des couleurs.
        On applique un OR sur les deux masques pour couvrir tout le rouge.

        Critère : au moins 30 pixels rouge très saturé (S>180) et lumineux (V>120)
        dans le cercle masqué. Ce seuil évite les faux positifs avec des fonds
        légèrement rougeâtres.
        """
        hsv = cv2.cvtColor(roi_masked, cv2.COLOR_BGR2HSV)
        m1 = cv2.inRange(hsv, np.array([0,   180, 120]), np.array([10,  255, 255]))
        m2 = cv2.inRange(hsv, np.array([170, 180, 120]), np.array([180, 255, 255]))
        return int(np.sum(cv2.bitwise_or(m1, m2) > 0)) > 30

    def _detect_yellow_bar(self, roi: np.ndarray) -> bool:
        """
        Détecte la barre jaune de Deep Wounds en bas du portrait.

        La barre est située dans le TIERS INFÉRIEUR du portrait.
        Pour éviter les faux positifs avec des fonds jaunes (champ de maïs, etc.),
        on vérifie qu'au moins une ligne horizontale contient > 40% de pixels jaunes
        consécutifs (= une vraie barre, pas des pixels isolés).
        """
        h, w = roi.shape[:2]
        # On analyse uniquement le tiers inférieur où se trouve la barre
        bar_zone = roi[2*h//3:h, :]
        hsv = cv2.cvtColor(bar_zone, cv2.COLOR_BGR2HSV)
        # Plage jaune DBD : teinte 20-35, saturation et luminosité élevées
        yellow = cv2.inRange(hsv, np.array([20, 150, 150]), np.array([35, 255, 255]))
        # Compter les pixels jaunes par ligne horizontale
        row_sums = np.sum(yellow > 0, axis=1)
        return bool(np.any(row_sums > w * 0.4))

    def _count_white_bars(self, roi: np.ndarray) -> int:
        """
        Compte les barres blanches à droite du portrait (0, 1 ou 2).

        Ces barres représentent le nombre de fois qu'un survivant a été accroché.
        Elles sont situées à droite du cercle, dans le quart droit du ROI.
        On divise la zone en deux moitiés verticales : haut = 1er hook, bas = 2ème.
        Critère : au moins 10 pixels blancs (V>200, S<30) dans chaque moitié.
        """
        h, w = roi.shape[:2]
        # Zone à droite du cercle : quart droit du ROI
        bars_zone = roi[:, w*3//4:]
        if bars_zone.size == 0:
            return 0

        hsv = cv2.cvtColor(bars_zone, cv2.COLOR_BGR2HSV)
        # Blanc = très lumineux (V>200) et très peu saturé (S<30)
        white = cv2.inRange(hsv, np.array([0, 0, 200]), np.array([180, 30, 255]))

        half = h // 2
        count = 0
        if np.sum(white[:half] > 0) > 10:
            count += 1
        if np.sum(white[half:] > 0) > 10:
            count += 1
        return count

    # ── Debug (utilisé par tools/test_vision.py) ──────────────────────────────

    def get_debug_info(self, frame: np.ndarray) -> list[dict]:
        """
        Retourne les infos de debug détaillées pour les 4 portraits.
        Affiche les valeurs brutes (saturation, luminosité, couleur anneau, etc.)
        pour aider à calibrer les seuils si la détection est incorrecte.
        """
        debug_list = []
        for i, pos in enumerate(PORTRAIT_POSITIONS):
            roi = frame[pos["y"]:pos["y"]+pos["h"], pos["x"]:pos["x"]+pos["w"]]
            if roi.size == 0:
                debug_list.append({})
                continue

            h, w = roi.shape[:2]
            circle_mask = self._make_circle_mask(h, w)
            roi_masked = cv2.bitwise_and(roi, roi, mask=circle_mask)

            hsv = cv2.cvtColor(roi_masked, cv2.COLOR_BGR2HSV)
            px = hsv[circle_mask == 255]
            mean_sat = float(np.mean(px[:, 1])) if len(px) else 0
            mean_val = float(np.mean(px[:, 2])) if len(px) else 0

            ring_color  = self._sample_ring_color(roi, h, w)
            has_scratches = self._detect_red_scratches(roi_masked)
            has_yellow  = self._detect_yellow_bar(roi)
            icon_state  = self._detect_icon_state(roi_masked, circle_mask, h, w)
            snap        = self._analyze_portrait(roi)

            debug_list.append({
                "survivor":       i + 1,
                "state":          snap.state,       # état final détecté
                "ring_color":     ring_color,        # couleur de l'anneau
                "mean_sat":       round(mean_sat, 1),# saturation moyenne du cercle
                "mean_val":       round(mean_val, 1),# luminosité moyenne du cercle
                "has_scratches":  has_scratches,     # griffures rouges détectées ?
                "has_yellow_bar": has_yellow,         # barre jaune détectée ?
                "icon_state":     icon_state,         # état icône brut (avant fusion)
                "hook_bars":      snap.hook_bars,     # nombre de barres blanches
            })

        return debug_list
