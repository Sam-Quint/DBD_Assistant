# Récap — Assistant DBD

Ce document résume ce qui a été fait, les décisions prises et l'état actuel du projet.

---

## Ce qui est construit

### Infrastructure

- **Python portable** : `setup.bat` télécharge Python 3.12 embeddable et installe les dépendances automatiquement. Aucune installation manuelle requise sur n'importe quelle machine Windows.
- **3 scripts `.bat`** à la racine : `setup.bat`, `start.bat`, `calibrer.bat`
- **Tout est local** : `calibration.json`, `assets/icons/` et `python/` sont dans le `.gitignore`. Chaque machine fait sa propre calibration.

### Architecture du code

Le projet est découpé en 4 couches :

| Dossier | Rôle |
|---------|------|
| `core/` | Logique métier pure : état du jeu, timers, règles des perks |
| `vision/` | Capture d'écran (mss) et analyse des portraits (OpenCV) |
| `ui/` | Overlay tkinter transparent par-dessus le jeu |
| `tools/` | Outils de calibration et debug, jamais lancés en jeu |

**3 threads en parallèle** : thread principal (tkinter), thread capture (10 FPS), thread clavier (pynput).

### Détection des états

Deux systèmes combinés :

1. **Template matching** (niveaux de gris, zone centrale 50% du portrait)
   - Détecte : downed, carried, hooked, dead, escaped
   - Les templates sont capturés par l'utilisateur en jeu via `tools/capture_icon.py`
   - Stockés dans `assets/icons/{état}/` en 32×32 px
   - Plusieurs templates par état supportés (score max retenu)

2. **Signaux HSV** (si aucun template ne matche)
   - Barre jaune dans le tiers bas → `deep_wounds`
   - Griffures rouges très saturées dans le cercle masqué → `injured`
   - Aucun signal → `healthy`

### Perks détectées automatiquement

| Perk | Logique |
|------|---------|
| **Coup Décisif** | Transition ACCROCHÉ → BLESSÉ en < 1s → timer 60s |
| **Fardeau** | Survivant A gagne une barre au même instant que B en perd une → timer 40s |
| **Wiggle** | Survivant porté → timer 16s, +4s si le tueur le lâche |
| **Deep Wounds window** | Post-décrochage → timer 15s |

### Overlay

- Fenêtre tkinter sans bordure, transparente, toujours au premier plan
- Affiche pour chaque survivant : état, nombre de crochets (●○), perks actives, barres de timers colorées
- Bordure verte si accroché, jaune si sélectionné manuellement
- Rafraîchissement à 10 FPS via `root.after()`

---

## Ce qui n'est pas encore fait

### V.2.0 — Perks manuelles
Le système existe déjà dans le code (touches AZERTY, `manual_perks` dans `SurvivorData`, affichage dans l'overlay), mais les perks manuelles ne déclenchent pas de timers ni de comportements. C'est un affichage informatif uniquement pour l'instant.

### V.3.0 — Détection automatique avancée
- **Dead Hard** : détecté quand la touche M1 est pressée ET qu'un survivant passe en Deep Wounds dans les 300ms. La touche M1 est un placeholder (`"m"`) à adapter selon le setup du joueur.
- **Souplesse, Finesse, Mine Explosif, etc.** : non implémentées.

### Reset automatique de partie
Actuellement il n'y a pas de détection de début de nouvelle partie. Si l'utilisateur rejoue, les états et perks de la partie précédente restent affichés. Un reset manuel n'est pas encore exposé (la méthode `game_state.reset()` existe mais n'est pas déclenchée).

### Calibration des PORTRAIT_POSITIONS
`PORTRAIT_POSITIONS` définit la position de chaque portrait **dans** la ROI capturée. Ces coordonnées sont fixes dans `config.py` et ont été ajustées manuellement. Si la ROI change beaucoup, il faudra les réajuster à la main.

---

## Décisions techniques notables

| Sujet | Décision | Raison |
|-------|----------|--------|
| Détection des états icônes | Template matching niveaux de gris | Plus robuste que HSV sur fond variable selon la map |
| Détection des états vivants | Signaux HSV (griffures, barre jaune) | Pas besoin de template, signaux très distincts |
| Python portable | Pas d'installation système | Permet de cloner + lancer sans rien installer |
| Templates non versionnés | `.gitignore` sur `assets/icons/` | Propres à chaque résolution/paramètres graphiques |
| Thread principal = tkinter | Obligation tkinter | tkinter n'est pas thread-safe |
| `game_state.lock` partout | Threading.Lock | Accès concurrent depuis 3 threads |

---

## État actuel : ce qui fonctionne, ce qui reste à valider

| Composant                                            | État                                                     |
| ---------------------------------------------------- | -------------------------------------------------------- |
| `setup.bat` / `start.bat` / `calibrer.bat`           | ✅ Fonctionnel                                            |
| Calibration ROI multi-écrans                         | ✅ Fonctionnel                                            |
| Capture d'écran (mss)                                | ✅ Fonctionnel                                            |
| Détection healthy / injured / deep_wounds            | ✅ Implémenté, à valider en jeu                           |
| Détection downed / carried / hooked / dead / escaped | ⏳ Implémenté, **nécessite capture des templates en jeu** |
| Timers Coup Décisif, Fardeau, Wiggle, DW window      | ✅ Implémenté, à valider en jeu                           |
| Overlay tkinter                                      | ✅ Implémenté, à valider en jeu                           |
| Perks manuelles (affichage)                          | ✅ Fonctionnel                                            |
| Reset automatique de partie                          | ❌ Non implémenté                                         |
| Dead Hard automatique                                | ❌ Non implémenté (V.3.0)                                 |
