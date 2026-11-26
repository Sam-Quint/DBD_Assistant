# Prochain objectif — prochaine session

Document de reprise. Tenu à jour à la fin de chaque session. Le détail de ce qui a été fait est dans `JOURNAL.md`.

## Où on en est (fin de session du 2026-11-26)

L'app C# (WPF) lit uniquement les pixels de l'écran pour deviner l'état des 4 survivants. Validé par l'utilisateur sur plusieurs vraies parties ; l'exe fonctionne sur le PC « Fix ».

- États : **265/266** sur les captures étiquetées (`dotnet run --project src/DbdAssistant.Tools -- evaluer`).
- **Overlay fait** (`OverlayWindow.cs`, case « Overlay ») : anneau coloré par état + 2 pastilles de crochets autour des portraits, emplacement réservé sous chaque portrait pour les futurs timers. Fenêtre click-through, exclue de la capture. Fonctionne en jeu.
- **Crochets (`!`) : encore aléatoires.** Faux crochets sur des survivants à 0 (éclaboussures de sang, bords clairs du décor). C'est le point faible principal.
- Captures renommées : `tueur 01..44`, `bug 1..7`, `3eme (n)`, `4eme (n)`. Correspondance : `Captures/renommage.txt`.
- `Captures/Crochet.txt` : vérité terrain des crochets, **préremplie avec la lecture de l'outil, à corriger** (seules `tueur 32/35/41` confirmées à l'œil).
- Le HUD tueur a aussi 2 emplacements de crochet (blanc = subi, sombre = libre).
- Exe `publish\` pas régénéré avec l'overlay : lancer `publier.bat`.

## Objectifs de la prochaine session (dans l'ordre)

### 1. Fiabiliser les crochets
- L'utilisateur enregistre des captures (bouton de l'app) quand l'overlay affiche un faux crochet, et note survivant (haut en bas) + vrai nombre.
- L'utilisateur corrige `Captures/Crochet.txt`.
- Brancher le **score de crochets dans `evaluer`** (par capture et global, côté tueur et survivant) à partir de `Crochet.txt`, puis régler `MarkPairReader` / `CountMarks` sans régression. Piste : utiliser le lecteur par paires aussi en mode tueur ; apprendre un modèle de `!`.
- Décision à prendre : garder ou masquer les pastilles de crochets de l'overlay tant que la lecture n'est pas fiable.

### 2. Timers (après fiabilisation)
Calculés depuis les changements d'état, affichés dans l'emplacement réservé de l'overlay : Coup Décisif 60 s, Fardeau 40 s, Deep Wounds post-décrochage 15 s, Wiggle 16 s (+4 s si lâché). Voir `Assistant_DBD.md` (tableau des timers). Choisir d'abord lesquels et les règles.

### 3. Ensuite
Écran de réglages (HUD, calibration, position/taille de l'overlay) ; détection automatique tueur/survivant (seulement si un signal fiable est trouvé, sinon garder le choix manuel).

## Pièges à ne pas oublier

- **Régler sur les mêmes captures est optimiste** : toujours valider sur de nouvelles captures avant de croire un score. Les seuils actuels (griffures 0,0115 ; barre jaune ; marques) ont été réglés sur les captures présentes.
- La marge sur les griffures est faible (sains ≤ 0,021 dont 1 cas, puis 0,011 ; blessés ≥ 0,012).
- L'interface du jeu est **ancrée en bas à gauche** et dimensionnée par la **hauteur** de l'écran. Seules les échelles ~87 % et 100 % ont été vues.
- Le HUD survivant a **toujours 2 emplacements de crochet** (blanc = subi, sombre = libre) ; le HUD tueur n'a pas ce rond d'action ni ces emplacements.
- `Captures/` contient des pseudos : **jamais dans git**. Seul `DBD_Assistant/` est un dépôt à pousser (remote Sam-Quint/DBD_Assistant, branche Feature/Detection-des-survivants).
- Ne rien coder sans l'autorisation explicite de l'utilisateur ; tenir `JOURNAL.md` à jour.

## Commandes utiles (depuis `DBD_Assistant/`)

- App : `dotnet run --project src/DbdAssistant.App` ; exe autonome : `dotnet publish src/DbdAssistant.App -c Release -o publish` (ou `publier.bat`).
- Outils (`dotnet run --project src/DbdAssistant.Tools -- <commande>`) :
  - `evaluer` : exactitude des états (leave-one-capture-out) + cas limites de griffures.
  - `modeles` : régénère `templates.bin` depuis `labels.txt`.
  - `lire <dossier> <préfixe>` : états/crochets lus par capture.
  - `marques <dossier> <capture>` : traits détectés par le lecteur de marques.
  - `jaune <dossier> <capture> <survivant>` : statistiques de la barre jaune.
  - `annoter <dossier> <sortie>` : dessine les zones lues sur les captures.
- Calibration pour les tests : `CALIB="x,y1,y4"` (pixels) ou `calibration.txt` dans le dossier de captures. Un dossier dont le nom contient `SURVIVANT` est lu en mode survivant.
