@echo off
chcp 65001 >nul
title Assistant DBD — Calibration

cd /d "%~dp0"

if not exist "python\python.exe" (
    echo [ERREUR] Python portable introuvable.
    echo Lance setup.bat en premier.
    pause & exit /b 1
)

:menu
cls
echo.
echo  ╔══════════════════════════════════════╗
echo  ║     Assistant DBD — Calibration      ║
echo  ╚══════════════════════════════════════╝
echo.
echo  1  Reglage automatique des portraits  ^<^<^< COMMENCER PAR LA
echo       ^> Indique ta resolution, les 4 cadres sont calcules
echo.
echo  4  Calibrer a la main (si le reglage automatique ne tombe pas juste)
echo       ^> Clique-glisse pour encadrer les 4 portraits
echo.
echo  2  Capturer les templates d'icones  ^<^<^< FAIRE EN JEU
echo       ^> Sauvegarde les icones d'etat pour le matching
echo.
echo  3  Tester la detection en temps reel
echo       ^> Verifie les etats detectes et les scores de matching
echo.
echo  Q  Quitter
echo.
set /p choix=Choix :

if /i "%choix%"=="1" (
    python\python.exe tools\auto_calibrer.py
    goto :menu
)
if /i "%choix%"=="4" (
    python\python.exe tools\calibrer_roi.py
    goto :menu
)
if /i "%choix%"=="2" (
    python\python.exe tools\capture_icon.py
    goto :menu
)
if /i "%choix%"=="3" (
    python\python.exe tools\test_vision.py
    pause
    goto :menu
)
if /i "%choix%"=="q" exit /b 0
goto :menu
