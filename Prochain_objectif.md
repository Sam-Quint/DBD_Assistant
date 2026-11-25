# Prochain objectif — prochaine session

Document de reprise. Tenu à jour à la fin de chaque session. Le détail de ce qui a été fait est dans `JOURNAL.md`.

## Où on en est (fin de session du 2026-11-25)

L'app C# (WPF) lit uniquement les pixels de l'écran pour deviner l'état des 4 survivants. Ça marche sur le vrai jeu, côté tueur et côté survivant, après trois correctifs majeurs de la session : zones des portraits (ancrage en bas + calibration 2 clics), lecture des états indépendante de l'échelle de l'interface, et robustesse aux effets (Peste, sol jaune, scène sombre).

- États : **265/266** sur les captures étiquetées (`dotnet run --project src/DbdAssistant.Tools -- evaluer`).
- Crochets (`!`) : lecture par paires côté **survivant** (imparfaite). Côté **tueur** : ancienne lecture, **jamais vérifiée sur le vrai jeu**.
- Mode du HUD (Tueur / Survivant) : **choix manuel** dans l'app. L'auto par le rond sombre a été mesuré non fiable.
- Rien n'a encore été testé sur le PC « Fix » (celui des amis, sans .NET).

## Objectifs de la prochaine session (dans l'ordre)

### 1. Tester l'exe en vrai (rapide, très utile)
`publish\DbdAssistant.exe`, jeu visible (mode fenêtre sans bordure) :
- Choisir le HUD (Tueur / Survivant), cliquer **Calibrer les portraits** (1er puis 4e portrait, Entrée).
- Regarder si les 4 cartes suivent la partie : états, griffures, barre jaune, crochets.
- Enregistrer des captures (bouton) quand une carte se trompe, et les ranger dans `Captures/<dossier>/`.

### 2. Fichier de vérité terrain des crochets (à faire par l'utilisateur) puis score automatique
L'utilisateur propose un `.txt` avec le nombre de crochets de chaque survivant par capture. Format conseillé :
```
# nom_de_capture  c1 c2 c3 c4      (de haut en bas, 0 à 2, ? si illisible)
3eme (1) 2 1 2 2
4eme (5) 0 1 0 0
```
Ensuite : ajouter dans `evaluer` un score de crochets (par capture et global) pour régler `MarkPairReader` (survivant) et `CountMarks` (tueur) **sans régression**. Inclure des captures **côté tueur** : c'est le HUD de l'app et il n'a pas été vérifié.

### 3. Fiabiliser les marques `!`
Problèmes connus (voir JOURNAL, section « lecture des marques par paires ») :
- El goblino lu 1 au lieu de 0 près d'éclaboussures de sang (4eme 3, 5, 6).
- `!!` pâles sur fond clair lus trop bas (4eme 10, Glitzerhiippo).
- Un bord clair et fin du décor peut compter comme un `!`.
Pistes : exiger que le trait ait une hauteur et une position exactes dans le HUD ; comparer au même emplacement sur plusieurs images (lissage `HookCountSmoother` déjà là) ; apprendre un modèle de `!` à partir des captures étiquetées.

### 4. Détecter tueur/survivant automatiquement
Le rond sombre a échoué (scènes sombres). Autres signaux à mesurer sur des captures étiquetées : forme du cadre du portrait (varie selon la version du jeu), présence du rond d'action sur plusieurs images consécutives, nom en gras/blanc du joueur, ou simplement garder le choix manuel si rien n'est fiable. **Ne pas livrer un détecteur qui bascule à tort.**

### 5. Distribution
Tester l'exe sur le PC « Fix » : démarre-t-il sans rien installer ? Réaction de l'antivirus / SmartScreen ? Si bloqué : signature ou publication GitHub Releases (étape 7 du plan).

### 6. Ensuite (après fiabilisation de la lecture)
Overlay sur le jeu, timers (Coup Décisif, Fardeau, Wiggle…) calculés depuis les changements d'état, écran de réglages.

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
