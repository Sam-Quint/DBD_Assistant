# DBD Assistant

Overlay pour Dead by Daylight (côté Tueur). Détecte automatiquement les états et perks des survivants et affiche des timers en temps réel par-dessus le jeu.

---

## Prérequis

- Windows 10 / 11
- Connexion internet (uniquement pour le setup)
- Dead by Daylight en **1920x1080 plein écran**

---

## Installation (une seule fois)

Double-clique sur **`setup.bat`**.

Il télécharge automatiquement Python portable et installe toutes les librairies. Aucune installation manuelle nécessaire.

---

## Calibration (une seule fois, en jeu)

Double-clique sur **`calibrer.bat`**, puis :

**Étape 1 — Calibrer la zone des portraits**
Lance le jeu, reviens sur le menu de calibration et choisis l'option 1.
- Si tu as plusieurs écrans, choisis celui qui affiche le jeu
- Clique-glisse pour encadrer la zone des 4 portraits (haut gauche du jeu)
- Appuie sur `ENTRÉE` pour sauvegarder

**Étape 2 — Vérifier la détection**
Choisis l'option 2. Les états détectés s'affichent en temps réel. La détection est entièrement automatique, aucune configuration supplémentaire n'est nécessaire.

---

## Lancement

Double-clique sur **`start.bat`**.

L'overlay apparaît en transparence par-dessus le jeu, à côté des portraits.

---

## Touches (AZERTY)

| Touche | Action |
|--------|--------|
| `&` `é` `"` `'` | Sélectionner survivant 1 / 2 / 3 / 4 |
| `²` | Annuler la sélection |
| `(` `-` `è` `_` `ç` `à` | Assigner une perk manuelle au survivant sélectionné |

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
│   └── analyzer.py      ← analyse des portraits (OpenCV, signaux HSV)
│
├── ui/                  ← interface utilisateur
│   └── overlay.py       ← fenêtre tkinter transparente par-dessus le jeu
│
└── tools/               ← calibration et debug (pas utilisés en jeu)
    ├── calibrer_roi.py  ← sélection interactive de la zone des portraits
    ├── test_capture.py  ← vérification visuelle de la ROI capturée
    └── test_vision.py   ← debug de la détection en temps réel
```

---

## Ce qui est détecté automatiquement

| Mécanique | Déclencheur | Durée |
|-----------|-------------|-------|
| Coup Décisif | Décrochage rapide (< 1s) | 60s |
| Fardeau | Échange de barres simultané | 40s |
| Wiggle | Survivant porté | 16s (+4s si lâché) |
| Deep Wounds window | Post-décrochage | 15s |
