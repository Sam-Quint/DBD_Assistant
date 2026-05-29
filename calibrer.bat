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
echo  1  Tester la capture ROI
echo       ^> Vérifie que les portraits sont bien encadrés
echo.
echo  2  Capturer les icônes d'état
echo       ^> Sauvegarde les templates (downed/carried/hooked...)
echo.
echo  3  Tester la détection vision
echo       ^> Affiche l'état détecté en temps réel + valeurs HSV
echo.
echo  Q  Quitter
echo.
set /p choix=Choix :

if /i "%choix%"=="1" (
    python\python.exe tools\test_capture.py
    goto :menu
)
if /i "%choix%"=="2" (
    python\python.exe tools\capture_icon.py
    goto :menu
)
if /i "%choix%"=="3" (
    python\python.exe tools\test_vision.py
    goto :menu
)
if /i "%choix%"=="q" exit /b 0
goto :menu
