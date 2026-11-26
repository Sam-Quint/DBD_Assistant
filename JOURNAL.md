# Journal de modifications — Assistant DBD

Journal tenu à jour à chaque modification du projet (le plus récent en haut).
Format : date — résumé — fichiers touchés.

---

## Avancement (mis à jour à chaque modification)

Objectif : app Windows en C# qui lit uniquement les pixels de l'écran (aucune injection, aucune lecture clavier/souris), et que l'utilisateur lance d'un double-clic, sans rien installer.

| Étape | État |
| --- | --- |
| 1. Socle .NET + capture d'écran (DXGI) | ✅ fait, validé sur DBD (image non noire, 8-9 images/s) |
| 1b. Exe autonome sans .NET à installer | ✅ généré (60 Mo), démarre sans SDK sur le PC dev ; **à tester sur le PC "Fix"** |
| 2. Localiser les 4 portraits et leurs zones (cercle, marques `!`, 2 barres) | ✅ ancrage en bas à gauche + **calibration en 2 clics** (le vrai jeu est à ~87 % d'échelle) ; vérifié à l'œil sur le vrai jeu tueur (BUGS) et survivant (3eme/4eme). Interface 100 % et ~87 % vues, pas d'autres échelles |
| 3. Reconnaître les états (sain, blessé, Deep Wounds, à terre, porté, accroché, mort, sorti, Mori) | ✅ **265/266** sur les captures étiquetées (vidéo + vrai jeu tueur + vrai jeu survivant), icônes indépendantes de l'échelle, griffures robustes (Peste, assombri), barre jaune robuste (briques jaunes). **Seuils réglés sur ces mêmes images : à confirmer sur de nouvelles captures** |
| 4. Fenêtre d'état en temps réel | ✅ 4 cartes (état, score, griffures, barre jaune, crochets lus) ; lissage sur 3 images ; liste **HUD : Tueur / Survivant** (manuelle) ; bouton **Calibrer les portraits**. Marques `!` : côté survivant lecture par paires (imparfaite), côté tueur **non vérifiée sur le vrai jeu** |
| 5. Overlay sur le jeu + timers | ⏳ plus tard |
| 6. Interface de réglages / calibration | 🔶 calibration + choix du HUD faits ; reste le reste des réglages |
| 7. Distribution (GitHub Releases, signature) | ⏳ plus tard |

### Règles de lecture de l'écran (confirmées par l'utilisateur, 2026-11-24)

- **Le nom ne sert pas de signal** : il devient rouge seulement quand l'action commence (sinon blanc), et certaines options du jeu désactivent les noms. Ne jamais s'appuyer dessus.
- **Les barres sous le portrait sont le signal le plus fiable** (déduction exacte) :
  - 2 barres rouges = les 2 étapes de crochet. La 1re se vide, puis la 2e commence à se vider quand le survivant passe au 2e crochet.
  - 1 barre rouge = à terre (saignement).
  - barre jaune = Deep Wounds (à confirmer avec plus d'exemples).
- **`!` / `!!` près du nom** = nombre de fois que le survivant a été accroché.
- **Crochets blancs `( )` autour d'un portrait** = l'Obsession. Ils **diminuent quand l'Obsession est poursuivie** (signal de poursuite, à exploiter plus tard).
- Les icônes dans le cercle (crochet, rampant, porté) complètent les barres pour distinguer les états.
- **Barre jaune = toujours Deep Wounds. Porté = pas de barre.**
- **3e accrochage = mort du survivant.**
- **Mort / sorti / Mori (vus sur les captures du 2026-11-24 soir)** : crâne qui crie = mort sur crochet ; crâne calme aux yeux rouges = Mori (d'après le classement de l'ancien dossier `Image/icone/{dead,mori}`) ; icône de porte avec personnage qui court = sorti.
- **Cercle bleu à chaînes** et **cercle blanc épais** autour d'un portrait : effets causés par les pouvoirs du tueur. **Pas des états à détecter** ; à ignorer, sauf s'ils gênent la reconnaissance de l'icône (les modèles devront alors gérer ces apparences).
- Les captures viennent d'une **vidéo plein écran** sur le PC client : plus floues que le vrai jeu (compression). Mode d'affichage du jeu : **sans bordure**. Le plein écran exclusif n'a donc pas été testé.

Questions ouvertes : test de capture sur le vrai jeu (pas une vidéo).

---

## 2026-11-26 (renommage des captures, `Crochet.txt`, overlay)

- **Captures renommees** : `tueur 01..44`, `bug 1..7` (`SURVIVANT/` inchange). `labels.txt`, `templates.bin` regeneres ; correspondance dans `Captures/renommage.txt`. `evaluer` toujours 265/266.
- **`Captures/Crochet.txt`** : verite terrain des crochets, preremplie avec la lecture de l'outil (a corriger a la main ; seules `tueur 32/35/41` sont confirmees a l'oeil). Le score de crochets dans `evaluer` n'est pas encore branche. Constat : le HUD tueur a aussi 2 emplacements de crochet (blanc = subi, sombre = libre).
- **Tests reels** (utilisateur) : lecture OK sur plusieurs parties ; l'exe fonctionne sur le PC « Fix ».
- **Overlay** (`OverlayWindow.cs`, case « Overlay » dans l'app) : fenetre WPF transparente plein ecran, click-through, exclue de la capture (`SetWindowDisplayAffinity`, Windows 10 2004+). Anneau colore par etat autour de chaque portrait, 2 pastilles de crochets, emplacement reserve sous le portrait pour les futurs timers. **Pas encore verifie visuellement en jeu.**

---

## Pour la prochaine session

**Voir `Prochain_objectif.md`** (objectifs ordonnes, pieges connus, commandes). En resume : (1) tester l'exe en vrai (calibration, HUD), (2) fichier de verite terrain des crochets + score dans `evaluer`, (3) fiabiliser les marques `!` (survivant puis tueur), (4) detecter tueur/survivant automatiquement par un autre signal, (5) PC « Fix » / antivirus, (6) overlay + timers.

Commandes utiles (depuis `DBD_Assistant/`) :
- App : `dotnet run --project src/DbdAssistant.App` ; exe : `publier.bat`
- Outils : `dotnet run --project src/DbdAssistant.Tools -- annoter | modeles | evaluer | lire <dossier> <prefixe> | marques <dossier> <capture> | jaune <dossier> <capture> <survivant> | lissage`

---

## 2026-11-25 (commit de la session : calibration, HUD survivant, griffures, marques)

Resume de tout ce qui a ete fait depuis « analyse des status survivant avec C# » (details dans les sections datees ci-dessous, de la plus recente a la plus ancienne) :

- **Zones des portraits** : ancrage en bas a gauche (interface a ~87 %), calibration en 2 clics (`PortraitCalibration`, `CalibrationWindow`, bouton « Calibrer les portraits », `%APPDATA%\DbdAssistant\calibration.json`).
- **HUD survivant** : `HudMode` (Tueur/Survivant) choisi dans l'app, memorise (`AppSettings`). Detection automatique par le rond sombre essayee puis abandonnee (non fiable : 5/9 survivant vs 19/51 tueur).
- **Etats** : icones independantes de l'echelle, griffures = traits rouges fins en proportion (anti-Peste, anti-assombrissement), barre jaune plus robuste (teinte, longueur continue, epaisseur, lignes voisines), `templates.bin` 68 modeles. Evaluation **265/266**.
- **Marques `!` survivant** : `MarkPairReader` (paire de traits a ~8 px, clair = subi / sombre = libre). Mode tueur inchange.
- **Outils/donnees** : `labels.txt` +~95 survivants (vrai jeu tueur BUGS, survivant 3eme/4eme), noms de capture avec espaces, `calibration.txt` par dossier, commandes `marques`, `jaune`, `lire` enrichi, `evaluer` avec cas limites de griffures.
- **A savoir** : `Captures/` (pseudos) n'est pas dans git ; les seuils sont regles sur les memes images (a confirmer sur de nouvelles captures). Prochaines etapes : `Prochain_objectif.md`.

---

## 2026-11-25 (nuit, suite 2 : lecture des marques `!` par paires, HUD survivant)

- Nouveau `MarkPairReader` (Core), utilise **uniquement en mode survivant** (le mode tueur garde `CountMarks`). Principe : le HUD survivant dessine toujours 2 emplacements voisins (~8 px, blanc = crochet subi, sombre = libre). On cherche une **paire** de traits fins (clair ou sombre) de meme hauteur/position verticale (+/- 4 px) a ~8 px d'ecart, ne pouvant commencer que juste apres le rond d'action (x ≈ 0..16) ou juste apres l'icone de statut (x ≈ 32..50), puis on compte les traits clairs. Repli : un trait blanc net seul (contraste >= 40) a ces memes positions, sauf si une paire de traits sombres plus nette existe (deux emplacements libres).
- `StateRecognizer.Read(..., HudMode mode)` ; l'app et l'outil passent le mode. Outil : `marques <dossier> <capture>` affiche les traits detectes par portrait.
- Verifie sur les cas connus a l'oeil : barry allen 1 (3eme 2, 3), Hedera 1 (3eme 4, 5, 6), OrcMalade 1 (4eme 5), El goblino 2 / Orc 1 (3eme 1, 9), El goblino 0 / Orc 2 / Bebopidop 2 (4eme 10, nom en gras = joueur), Bebopidop 1 (4eme 7, 8). Faux bords du decor (manteau, briques) ecartes.
- **Encore imparfait** : El goblino lu 1 au lieu de 0 sur 4eme 3, 5, 6 (eclaboussures de sang pres des marques) ; Glitzerhiippo (4eme 10, `!!` pales sur fond clair) lue 1 au lieu de 2 ; OrcMalade (4eme 1, 2) lue 0, `!` non visible. Pas de verite terrain automatisee pour les marques : verification a l'oeil seulement.
- Etats : toujours 265/266. Exe regenere dans `publish/`. Rien commite.

---

## 2026-11-25 (nuit, suite : 10 nouvelles captures survivant `4eme (n)`)

- Captures du vrai jeu cote survivant (`Captures/SURVIVANT/4eme (1..10).png`). Les 9 precedentes ont ete renommees `3eme (1..9)` par l'utilisateur : `labels.txt` mis a jour (correspondance verifiee par la taille des fichiers) et le lecteur d'etiquettes accepte maintenant les noms avec espaces.
- **Etats** : les 40 nouveaux survivants sont lus justes (y compris les « A terre » alors que leurs icones n'etaient pas dans les modeles). Evaluation globale 265/266 ; reste `234217.3`.
- **Faux Deep Wounds sur sol de briques jaunes** (4 cas, captures 4 a 6) : la « barre jaune » etait une rangee de briques. Corrections de `HasYellowBar` : (1) moyenne de plusieurs lignes autour (a 6..12 px), (2) epaisseur <= ~8,5 px, (3) **longueur continue** : mesure sur 8 vraies barres, au moins une des deux est quasi pleine (>= 87 % de jaune, suite >= 41/47 px) ; les briques font <= 20 px. Une barre qui se vide est acceptee si elle reste collee au bord gauche de la 1re zone. Deep Wounds toujours 7/7.
- **Marques `!`** : un trait doit etre une suite verticale continue (>= 40 % de la hauteur) et fine (<= 6 px), 1 colonne creuse tolere ; zone survivant (99, -26, 69, 26) pour ne pas toucher l'anneau dore du rond d'action. Verifie : barry allen 1, Hedera 1, El goblino (capture 10, marques noires) 0.
- **Limite connue** : un bord clair et fin du decor dans la zone (ex. le manteau du tueur sur la capture 5, OrcMalade lue 2 au lieu de 1) peut compter comme un `!`.
- `templates.bin` : 68 modeles. Outil : `jaune <dossier> <capture> <survivant>` affiche les statistiques de la barre jaune.
- Exe regenere dans `publish/`. Rien commite.

---

## 2026-11-25 (nuit : HUD survivant, griffures, la Peste)

- Nouvelles captures `Captures/SURVIVANT` (9, partie cote survivant contre la Peste, interface 100 %). Problemes constates : (1) crochets `!` jamais lus, (2) faux « Blesse » a cause des eclaboussures de l'infection, (3) vraies griffures non lues quand le portrait est assombri.
- **HUD survivant** : a droite du portrait il y a un rond d'action sombre (~35 px, centre ≈ +76 px), parfois une icone de statut (rond rouge barre), puis les marques. Il y a toujours **2 emplacements de crochet : blanc = crochet subi, sombre = libre**. Zone des marques large cote survivant (`MarksSurvivor` : dx 96, w 72) contre dx 57 cote tueur. `PortraitLayout.Compute(..., HudMode mode)`.
- **Detection auto tueur/survivant par le rond sombre : essayee, NON fiable, abandonnee.** Mesure sur 9 captures survivant et ~50 captures tueur : survivant >= 2 ronds : 5/9 ; tueur >= 2 ronds : 19/51 (les scenes sombres imitent un rond). Un detecteur qui bascule a tort casserait la lecture. A la place : liste deroulante **« HUD : Tueur / Survivant »** dans l'app, memorisee dans `%APPDATA%\DbdAssistant\settings.json` (`AppSettings`, `HudMode`). Piste si on veut de l'auto plus tard : un signal different du rond (par ex. la forme du cadre du portrait, qui varie selon la version du jeu).
- **Griffures** (`StateRecognizer.ScratchFraction`) : rouge en proportion (R>=110, V et B <= 40 % de R) au lieu de R>=200/V,B<=70 ; seuls les **traits fins** comptent (rouge moins son ouverture 3x3), donc les taches larges (eclaboussures de la Peste, arc rouge de poursuite) disparaissent. Seuil `ScratchThreshold` 0,002 -> 0,0115 (nouvelle echelle). Marge faible : sains <= 0,021 (1 cas) puis 0,011 ; blesses >= 0,012 puis 0,021.
- **Marques `!`** : seuil de blanc relatif au fond (mediane + 60, entre 95 et 165) : le `!` du HUD survivant ne depasse pas ~125. Verifie sur les cas connus (barry allen 1, Hedera 1, El goblino accroche 2, OrcMalade 1).
- **Etiquettes** : +55 survivants dans `labels.txt` (9 SURVIVANT, 4 BUGS verifies a l'oeil). `templates.bin` regenere : 64 modeles (anneau d'infection, vrai jeu). Les captures `BUGS` ont un `calibration.txt` (110,545,772) ; un dossier dont le nom contient SURVIVANT est lu en mode survivant ; `evaluer` affiche les cas limites de griffures.
- **Resultats** : evaluation 218/226 avant la correction des griffures (8 erreurs : 4 griffures ternes, 2 eclaboussures Peste, 2 arcs rouges) -> **225/226**. Reste : `234217.3` (ancienne video, sain lu blesse, 0,021). Reglage fait sur ces memes captures : a confirmer sur de nouvelles.
- Correction d'une erreur de lecture du soir : l'icone du joueur « a terre » de la capture 003510 etait en fait « Porte » (meme icone vue pendant un portage sur la 211743).
- Non verifie : le HUD survivant a d'autres echelles d'interface (seul 100 % vu) ; les marques grises de la 212218 (Tinkitinkiee, Hedera) lues 2 sans certitude.
- Exe regenere dans `publish/`. Rien commite.

---

## 2026-11-25 (soir : zones decalees sur le vrai jeu + calibration)

- Constat (7 captures `Captures/BUGS`, vrai jeu) : l'app ne lisait ni griffures ni crochets car les zones tombaient a cote des portraits. Mesure : portraits a x≈110, y≈545/622/698/772 (pas 76), contre 128 / 457 + 88i dans le code (mesure sur la video a 100 %). L'echelle d'interface du joueur est ≈ 0,87 et l'interface est **ancree en bas a gauche** : la distance au bas de l'ecran est proportionnelle a l'echelle (1080 - 623·k pour le 1er portrait). L'ancien Python marchait mieux car il avait une calibration par clics (`Detecteur_griffures/detecteur.py`).
- `PortraitLayout.Compute` : ancrage en bas (identique a avant en 1080p a 100 %), nouveau parametre `calibration`. Zones des barres : dy 23 -> 25, h 10 -> 12 (barres mesurees ~28 px sous le centre).
- Nouveau `PortraitCalibration` (Core) : x, y du 1er et du 4e portrait en fraction de la hauteur d'ecran, enregistre dans `%APPDATA%\DbdAssistant\calibration.json`.
- Nouveau bouton **« Calibrer les portraits »** (`CalibrationWindow`) : capture figee en plein ecran, clic au centre du 1er puis du 4e portrait, apercu des 4 cercles/barres, Entree = valider, clic = recommencer, Echap = annuler. L'app affiche un avertissement tant qu'elle n'est pas calibree.
- Reconnaissance d'icones independante de l'echelle : `StateRecognizer` reechantillonne (bilineaire) le cercle a la taille des modeles (k = diametre/64). Sans cela, les icones accroche/a terre d'une interface a 87 % ne correspondaient pas aux modeles.
- Barre jaune assouplie (saturation >= 0,45, teinte 32-76, luminosite >= 130) : sur fond violet la barre vaut ~(187,148,87), refusee avant.
- Outil : variable `CALIB="x,y1,y4"` (pixels de la capture) pour `annoter | lire | evaluer | modeles` ; `lire` affiche aussi score d'icone et griffures.
- Resultats, avec calibration simulee `CALIB=110,545,772` sur les 7 captures BUGS : zones centrees sur les 28 portraits (verifie a l'oeil), griffures lues, 2 barres jaunes (KS2) lues, 2 accroches lus. Anciennes captures : toujours 171/171.
- **Encore faux sur BUGS** : (a) joueur a terre « QuemTela » (003510) lu « Porte » 0,85 ; (b) Kate (003613) a terre, icone « A terre » a 0,61 < seuil 0,72, lue « Blesse » ; (c) Nova (003438) saine avec un arc rouge autour du portrait lue « Blesse » (griffures 0,052 : l'arc rouge est compte comme griffures) ; (d) marques `!` toujours peu fiables.
- A faire pour (a)(b) : etiqueter ces captures du vrai jeu dans `labels.txt` (avec `CALIB`) et regenerer `templates.bin`. Pour (c) : restreindre la zone de griffures au visage (a valider sur plus de cas).
- Exe regenere dans `publish/`. Rien commite.

---

## 2026-11-25 (captures de la video avec le retour de l'app)

- 9 nouvelles captures (`capture_20261125_*`) recues, avec les cartes de l'app visibles. Etats : tous justes. Defaut confirme : la barre jaune de « hateuue » etait visible mais l'app affichait « barre jaune : non » (ancien exe).
- Cause mesuree : sur cette map verte la barre vaut ~(201, 213, 72), teinte 65-71 degres, hors de ma plage 40-66. Plage elargie a 40-76 (le vert de feuillage, ~90+, reste exclu ; le sable orange, ~30, aussi). Deep Wounds : 5/5 sur les captures etiquetees (1/1 avant).
- Marques `!` : seuil de luminosite 190 -> 165 (deux `!!` supplementaires lus ; a 140 de faux `!!` apparaissent). Reste imparfait : `!!` flous sur fond rouge ou blanc encore lus 0.
- `labels.txt` : +36 survivants etiquetes (total 171), `templates.bin` regenere (53 modeles). Evaluation : 171/171. Reglage fait en regardant ces memes captures : a confirmer sur de nouvelles.
- Outil : commande `lire <dossier> <prefixe>` (affiche les etats lus pour des captures).
- Exe regenere dans `publish/`.

---

## 2026-11-25 (retours du test sur video)

- Retour utilisateur : la detection des etats fonctionne bien ; la barre jaune n'est pas toujours detectee (depend du fond) ; le nombre de crochets oscille 1 -> 0 -> 1.
- Crochets : nouveau `HookCountSmoother` (Core). Monte si une valeur est lue sur >= 8 des 20 dernieres images ; ne redescend que si elle n'est plus vue pendant 60 images. Verifie sur des sequences de test (commande `lissage` de l'outil) : scintillement stabilise a 1 apres ~1,4 s, pic parasite ignore, `!` masque 0,5 s sans effet.
- Barre jaune : detection par teinte (jaune 40-66 degres, saturee) et par forme (bande horizontale remplie >= 25 %, lignes voisines peu jaunes) au lieu de seuils RVB fixes, avec tolerance verticale de 2 px. Meme resultat sur les 135 survivants etiquetes (le sable orange reste refuse). **Non valide sur les cas reels rates** : les nouvelles captures n'ont pas ete retrouvees dans le projet.
- Exe regenere dans `publish/`.

---

## 2026-11-25 (etape 3 : lecture des etats)

- Nouveau (Core) : `SurvivorState.cs` (etats), `TemplateLibrary.cs` + `templates.bin` (47 modeles d'icones embarques dans l'exe), `StateRecognizer.cs`, `StateSmoother.cs` (un etat n'est accepte qu'apres 3 images identiques).
- Methode : (1) icone par comparaison de modeles sur l'image « blanc minimal » (min des canaux R,V,B : fonds rouges et cercles bleus disparaissent) → accroche, a terre, porte, mort, Mori, sorti ; (2) sinon barre jaune stricte (R>=220, V>=200, B<=90) → Deep Wounds ; (3) sinon rouge tres vif (R>=200, V<=70, B<=70) dans le cercle → blesse ; (4) sinon sain. Seuil d'icone 0,72.
- Nouveau (Tools) : labels.txt (135 survivants etiquetes a l'oeil sur 35 captures), commandes `modeles` (regenere templates.bin), `evaluer` (leave-one-capture-out, matrice de confusion), `annoter`.
- Resultats : 1re version 94 % ; apres reglage des seuils 135/135. Reglage fait sur ces memes captures, donc optimiste. Rouge vif : 0 sur les 53 sains, >= 0,2 % sur les 34 blesses (marge faible).
- App : 4 cartes d'etat en direct ; fenetre placee a droite de l'ecran pour ne pas cacher les portraits. Verifie : exe lance au-dessus d'une capture plein ecran, etats lus correctement sur les 4 survivants (capture presente dans les modeles).
- Limites : marques `!` peu fiables (des sains en lisent 2 ou 3) ; 1080p seulement ; Captures/ n'est pas dans git, donc `modeles` ne se relance qu'avec les captures en local.

---

## 2026-11-25 (etape 2 : zones des portraits)

- Nouveau : `src/DbdAssistant.Core/PortraitLayout.cs` : calcule pour les 4 survivants les zones a lire (cercle/icone, marques `!`, barre 1, barre 2) a partir de la hauteur d'ecran. Reference mesuree en 1080p : centre x=128, 1er portrait y=457, pas 88 ; echelle proportionnelle a la hauteur, reglages fins `uiScale`, `offsetX`, `offsetY`.
- Nouveau : `src/DbdAssistant.Tools` (outil dev, Windows) : dessine les zones sur chaque capture. `dotnet run --project src/DbdAssistant.Tools` lit `Captures/` et ecrit `Captures/annotees/`.
- Verifie : 35 captures annotees, zones bien placees sur les 4 survivants (cercles sur les portraits, rectangles sur les barres et les `!`). Les captures viennent d'une video, pas du vrai jeu.
- Non fait : lecture des couleurs/icones (etape 3).

---

## 2026-11-24 (exe autonome)

- `DbdAssistant.App.csproj` : publication en un seul `.exe` autonome (win-x64, runtime .NET embarqué, compressé) ; nom d'assemblage `DbdAssistant`.
- Nouveau : `publier.bat` (dev uniquement) → `publish\DbdAssistant.exe`. `.gitignore` : ajout `publish/`.
- Vérifié : l'exe (60 Mo) démarre et répond avec un `PATH` sans `dotnet`. Pas encore testé sur le PC "Fix".
- Pour l'utilisateur : copier `DbdAssistant.exe` et double-cliquer. Aucun SDK ni runtime à installer (Windows 10/11 64 bits).

---

## 2026-11-24 (etape 1 : socle .NET + capture)

- Nouveau : `DbdAssistant.sln`, `src/DbdAssistant.Core` (bibliotheque, `ScreenCapturer.cs` : lecture des pixels de l'ecran principal via DXGI Desktop Duplication, Vortice 3.8.3), `src/DbdAssistant.App` (fenetre WPF : apercu en direct, images/s, alerte « image noire », bouton « Enregistrer une capture » vers `Captures/`).
- `.gitignore` : ajout `bin/ obj/ .vs/ Captures/`.
- Verifie : compilation OK (0 erreur), l'app demarre et reste ouverte 8 s sans planter. Pas encore verifie visuellement ni avec DBD lance.
- Lancer : `dotnet run --project src/DbdAssistant.App`.

---

## 2026-11-24 (refonte)

- Decision : repartir de zero en C# / .NET (WPF). Perimetre V0 : lecture des pixels des 4 portraits et de leur etat uniquement. Aucune injection, aucune lecture clavier/souris. 1920x1080 16:9.
- Reorganisation : tout le Python non reutilise deplace dans `DBD_Assistant/V1_Python/` (main.py, ui/, tools/, release/, .bat, README, requirements, spec, build/dist/.buildenv, core/{logic,state,timers,paths}, vision/capture).
- Conserve a la racine comme reference pour le C# : `vision/analyzer.py`, `vision/status_recognizer.py`, `core/config.py`, `core/layout.py`, `assets/` (templates et icones), `RECAP.md`.
- `JOURNAL.md` se trouve dans `DBD_Assistant/` (seul depot git avec remote).
- Rien de commite ni pousse pour cette reorganisation.

---

## 2026-11-24 (suite)

- Fix : `setup.bat`, `start.bat`, `calibrer.bat` reecrits en ASCII pur (les caracteres UTF-8 + `chcp 65001` cassaient `cmd` : setup se fermait, calibrer affichait des erreurs `'alibration' n'est pas reconnu`). Ils utilisent maintenant `python\python.exe` s'il existe, sinon le Python du systeme. Non teste sur la machine de l'utilisateur.
- Constat : l'antivirus signale probablement l'exe PyInstaller non signe (faux positif, `pynput` = ecoute clavier global).
- Fichiers : `setup.bat`, `start.bat`, `calibrer.bat`.

## 2026-11-24

- Création du journal de modifications (`JOURNAL.md`) à la racine du projet.
- Relecture de la mémoire projet et de `DBD_Assistant/RECAP.md` pour établir l'état de référence ci-dessous.

- Constat (README) : lancement = `python main.py` (dev) ou `DBD_Assistant.exe` (build via `build_exe.bat`) ; `setup.bat`/`start.bat`/`calibrer.bat` (Python portable) sont dépréciés. Calibration auto via `python main.py --calibrer`.

---

## État de référence (d'après la mémoire du 2026-05-31 et `RECAP.md`)

**Projet** : overlay Python (mss, OpenCV, pynput, tkinter) côté Tueur pour Dead by Daylight, Windows 1920x1080.

| Composant | État |
| --- | --- |
| `setup.bat` / `start.bat` / `calibrer.bat` | ✅ |
| Calibration ROI multi-écrans | ✅ |
| Capture mss, détection healthy / injured / deep_wounds | ✅ (à valider en jeu) |
| Timers Coup Décisif (60s), Fardeau (40s), Wiggle (16s +4s), DW window (15s) | ✅ (à valider en jeu) |
| Overlay tkinter + perks manuelles (affichage) | ✅ |
| Détection downed / carried / hooked / dead / escaped | ⏳ templates à capturer en jeu |
| Reset automatique de partie | ❌ |
| Dead Hard automatique (V.3.0) | ❌ |
| Perks manuelles déclenchant des timers (V.2.0) | ❌ affichage seulement |

**Dossiers non suivis à ce jour** : `Detecteur_griffures/`, `Entrainement/`, `Sans titre-1.psd`.
