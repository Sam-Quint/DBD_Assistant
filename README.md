# DBD Assistant

Overlay pour Dead by Daylight (côté Tueur). Détecte automatiquement les états et perks des survivants et affiche des timers en temps réel par-dessus le jeu.

---

## Pour jouer (aucune installation, Python n'est pas nécessaire)

1. Télécharge `DBD_Assistant.zip` et **décompresse tout le dossier**
2. Lance Dead by Daylight en plein écran (n'importe quelle résolution : 1080p, 1440p, 4K, 16:10, 21:9...)
3. Double-clique sur **`Calibrer.bat`** (une seule fois par résolution) : voir « Calibration » ci-dessous
4. Double-clique sur **`DBD_Assistant.exe`**

Windows SmartScreen peut bloquer l'exécutable (non signé) : « Informations complémentaires » puis « Exécuter quand même ».

---

## Pour développer (Python requis)

Prérequis : Windows 10 / 11, Python 3.12+ avec tkinter.

```
pip install -r requirements.txt
python main.py               # lance l'assistant
python main.py --calibrer    # réglage automatique des portraits
build_exe.bat                # construit dist\DBD_Assistant.zip (l'exécutable à distribuer)
```

`setup.bat` / `start.bat` / `calibrer.bat` sont les anciens lanceurs basés sur un Python portable téléchargé ; ils ne sont plus recommandés (l'exécutable les remplace).

---

## Calibration (une seule fois, en jeu)

Double-clique sur **`Calibrer.bat`** (version exécutable : lance directement l'étape 1) ou, en développement, sur `calibrer.bat` (menu avec les options ci-dessous).

**Étape 1 — Réglage automatique des portraits** *(option 1)*
- Lance le jeu avec les 4 portraits visibles, puis reviens sur le menu → option **1**
- Choisis l'écran, puis confirme ta résolution (détectée automatiquement, ou choisis un préréglage / tape `LARGEURxHAUTEUR`)
- Les 4 cadres sont **calculés** à partir de la résolution. L'état reconnu s'affiche à côté de chaque portrait : si c'est juste, appuie sur `ENTRÉE`
- Si les cadres sont décalés : flèches (ou ZQSD/WASD) pour décaler, `+` / `-` pour l'échelle d'interface, `R` pour remettre à zéro
- L'interface du jeu est dimensionnée par la **hauteur** de l'écran : le ratio (16:9, 16:10, 21:9) ne change pas le calcul
- Sans aucun réglage, l'assistant suppose le jeu en plein écran sur l'écran principal
- L'option **4** garde l'ancienne calibration à la main (clique-glisse) en dernier recours

**Étape 2 — Capturer les templates d'icônes** *(option 2)*
Lance le jeu et joue normalement. Dès qu'un survivant est dans un état particulier, reviens rapidement sur la fenêtre de capture et sauvegarde :

| Touche | État |
|--------|------|
| `1` `2` `3` `4` | Sélectionner le survivant |
| `D` | À terre (downed) |
| `C` | Porté (carried) |
| `H` | Accroché (hooked) |
| `X` | Mort (dead) |
| `E` | Sorti (escaped) |
| `ENTRÉE` | Sauvegarder le template |

Plus tu captures de templates par état (idéalement 3-5), plus la détection est robuste.

**Étape 3 — Vérifier la détection** *(option 3)*
Affiche en temps réel l'état détecté pour chaque portrait avec le score de matching. Un bon score est > 0.80.

---

## Lancement

Double-clique sur **`start.bat`**.

L'overlay apparaît en transparence par-dessus le jeu, juste à droite des portraits des survivants.

---

## Touches en jeu (AZERTY)

| Touche | Action |
|--------|--------|
| `&` `é` `"` `'` | Sélectionner survivant 1 / 2 / 3 / 4 (appuyer deux fois = désélectionner) |
| `²` | Annuler la sélection |
| `(` `-` `è` `_` `ç` `à` | Assigner / retirer une perk manuelle au survivant sélectionné |

---

## Ce qui est détecté automatiquement

**États des survivants**

| État | Méthode de détection |
|------|----------------------|
| À terre / Porté / Accroché / Mort / Sorti | Template matching (niveaux de gris) |
| Deep Wounds | Barre jaune HSV dans le tiers bas du portrait |
| Blessé | Griffures rouges HSV dans le cercle masqué |
| Bonne santé | Aucun des signaux ci-dessus |

**Perks et mécaniques**

| Mécanique | Déclencheur | Durée |
|-----------|-------------|-------|
| Coup Décisif | Accroché → Blessé en < 1s | 60s |
| Fardeau | Échange de barres blanches simultané | 40s |
| Wiggle | Survivant porté | 16s (+4s si le tueur le lâche) |
| Deep Wounds window | Post-décrochage | 15s |

---

## Structure du projet

```
DBD_Assistant/
├── main.py              ← point d'entrée, orchestre les 3 threads
│
├── core/                ← logique métier
│   ├── config.py        ← constantes + chargement de calibration.json
│   ├── layout.py        ← position des portraits calculée depuis la résolution
│   ├── state.py         ← données des survivants + GameState partagé
│   ├── timers.py        ← gestion des timers (CD, Fardeau, Wiggle...)
│   └── logic.py         ← règles du jeu, détection des perks
│
├── vision/              ← tout ce qui touche à l'image
│   ├── capture.py       ← capture d'écran via mss
│   └── analyzer.py      ← analyse des portraits (template matching + HSV)
│
├── ui/                  ← interface utilisateur
│   └── overlay.py       ← fenêtre tkinter transparente par-dessus le jeu
│
├── tools/               ← calibration et debug (jamais lancés en jeu)
│   ├── auto_calibrer.py ← réglage automatique (résolution -> 4 cadres)
│   ├── calibrer_roi.py  ← sélection manuelle de la zone des portraits
│   ├── capture_icon.py  ← capture des templates d'icônes pendant une partie
│   └── test_vision.py   ← debug de la détection en temps réel
│
└── assets/icons/        ← templates (générés par capture_icon.py, non versionnés)
    ├── downed/
    ├── carried/
    ├── hooked/
    ├── dead/
    └── escaped/
```

---

## Fichiers générés localement (non versionnés)

| Fichier / Dossier | Généré par | Contenu |
|---|---|---|
| `calibration.json` | `calibrer_roi.py` | Coordonnées de la zone des portraits + moniteur |
| `assets/icons/` | `capture_icon.py` | Templates de détection des états icônes |
| `python/` | `setup.bat` | Python 3.12 portable |
