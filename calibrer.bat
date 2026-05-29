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
echo  1  Calibrer la zone des portraits  ^<^<^< COMMENCER PAR LA
echo       ^> Clique-glisse pour encadrer les 4 portraits
echo.
echo  2  Tester la detection en temps reel
echo       ^> Verifie que les etats sont bien detectes
echo.
echo  Q  Quitter
echo.
set /p choix=Choix :

if /i "%choix%"=="1" (
    python\python.exe tools\calibrer_roi.py
    goto :menu
)
if /i "%choix%"=="2" (
    python\python.exe tools\test_vision.py
    goto :menu
)
if /i "%choix%"=="q" exit /b 0
goto :menu
