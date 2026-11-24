# Journal de modifications — Assistant DBD

Journal tenu à jour à chaque modification du projet (le plus récent en haut).
Format : date — résumé — fichiers touchés.

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
