# DBD Assistant

Overlay pour Dead by Daylight (côté Tueur). Détecte automatiquement les perks des survivants et affiche des timers en temps réel par-dessus le jeu.

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

Double-clique sur **`calibrer.bat`**, puis suis les étapes dans l'ordre :

**Étape 1 — Tester la capture ROI**
Lance le jeu, reviens sur le menu de calibration et choisis l'option 1.
Une fenêtre s'ouvre avec la zone capturée en temps réel. Les rectangles verts doivent encadrer les 4 portraits des survivants.
Si ce n'est pas le cas, ajuste `PORTRAITS_ROI` et `PORTRAIT_POSITIONS` dans `config.py`.

**Étape 2 — Capturer les icônes d'état**
Choisis l'option 2. En jeu, mets chaque survivant dans un état différent et appuie sur la touche correspondante pour sauvegarder le template :

| Touche | État |
|--------|------|
| `D` | À terre |
| `C` | Porté |
| `H` | Accroché |
| `X` | Mort |
| `E` | Sorti |
| `Z` | Déconnecté |

Utilise `1` `2` `3` `4` pour choisir quel portrait capturer.

**Étape 3 — Vérifier la détection**
Choisis l'option 3. L'état détecté de chaque survivant s'affiche en temps réel avec les valeurs HSV. Vérifie que les états correspondent bien à ce que tu vois en jeu.

---

## Lancement

Double-clique sur **`start.bat`**.

L'overlay apparaît en transparence par-dessus le jeu, en haut à droite des portraits.

---

## Touches (AZERTY)

| Touche | Action |
|--------|--------|
| `&` `é` `"` `'` | Sélectionner survivant 1 / 2 / 3 / 4 |
| `²` | Annuler la sélection |
| `(` `-` `è` `_` `ç` `à` | Assigner une perk manuelle au survivant sélectionné |

---

## Ce qui est détecté automatiquement

| Mécanique | Déclencheur | Durée |
|-----------|-------------|-------|
| Coup Décisif | Décrochage rapide (< 1s) | 60s |
| Fardeau | Échange de barres simultané | 40s |
| Wiggle | Survivant porté | 16s (+4s si lâché) |
| Deep Wounds window | Post-décrochage | 15s |
