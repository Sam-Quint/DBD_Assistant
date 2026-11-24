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
| 2. Localiser les 4 portraits et leurs zones (cercle, marques `!`, 2 barres) | ✅ fait en 1080p, vérifié à l'œil sur 35 captures. **À re-vérifier sur le vrai jeu** (demain) |
| 3. Reconnaître les états (sain, blessé, Deep Wounds, à terre, porté, accroché, mort, sorti, Mori) | ✅ implémenté et confirmé en vidéo (états justes sur 9 captures). 171/171 sur les captures étiquetées, **mais seuils réglés sur ces mêmes captures : à confirmer sur le vrai jeu**. Exemples : Deep Wounds 5, sorti 2, Mori 4 |
| 4. Fenêtre d'état en temps réel | ✅ 4 cartes (état, score, griffures, barre jaune, crochets lus) dans l'app ; lissage sur 3 images. Marques `!` : **à valider** |
| 5. Overlay sur le jeu + timers | ⏳ plus tard |
| 6. Interface de réglages / calibration | ⏳ plus tard |
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

## Pour la prochaine session (a reprendre demain)

1. **Captures du vrai jeu** (promises par l'utilisateur) : verifier le placement des zones (`annoter`) et les etats (`lire`, `evaluer`), surtout la position verticale des portraits et la barre jaune.
2. Ajouter de nouvelles captures a `labels.txt` puis `modeles` + `evaluer` ; chercher des cas faux plutot que de regler sur les memes images.
3. Marques `!` : encore sous-estimees sur fond rouge/blanc. Pistes : seuil relatif au fond local, forme du trait (hauteur/largeur), ou deduire le nombre de crochets d'apres les barres.
4. Tester `publish\DbdAssistant.exe` sur le PC « Fix » (pas encore fait) et noter la reaction de l'antivirus / SmartScreen.
5. Ensuite : overlay sur le jeu, timers (Coup Decisif, Fardeau, Wiggle...) calcules depuis les changements d'etat, ecran de reglages.
6. **Rien n'est commite ni pousse depuis le commit « lecture des etats »** : les changements du jour (barre jaune par teinte, lissage des crochets, 9 captures etiquetees, templates.bin regenere) sont seulement en local.

Commandes utiles (depuis `DBD_Assistant/`) :
- App : `dotnet run --project src/DbdAssistant.App` ; exe : `publier.bat`
- Outils : `dotnet run --project src/DbdAssistant.Tools -- annoter | modeles | evaluer | lire <dossier> <prefixe> | lissage`

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
