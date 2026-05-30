# DBD Assistant

Overlay pour Dead by Daylight (côté Tueur). Détecte automatiquement les états et perks des survivants et affiche des timers en temps réel par-dessus le jeu.

---

## Prérequis

- Windows 10 / 11
- Connexion internet (uniquement pour le premier setup)
- Dead by Daylight en **1920x1080 plein écran**

---

## Installation (une seule fois)

Double-clique sur **`setup.bat`**.

Il télécharge automatiquement Python 3.12 portable et installe toutes les librairies. Aucune installation manuelle requise.

---

## Calibration (une seule fois, en jeu)

Double-clique sur **`calibrer.bat`**.

**Étape 1 — Calibrer la zone des portraits**
- Lance le jeu, puis reviens sur le menu de calibration → option **1**
- Si tu as plusieurs écrans, choisis celui qui affiche le jeu
- Clique-glisse pour encadrer la zone des 4 portraits (haut gauche du jeu)
- Appuie sur `ENTRÉE` pour sauvegarder → génère `calibration.json`

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
│   ├── calibrer_roi.py  ← sélection interactive de la zone des portraits
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
