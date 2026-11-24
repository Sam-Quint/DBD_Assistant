@echo off
chcp 65001 >nul
title Assistant DBD

cd /d "%~dp0"

if not exist "python\python.exe" (
    echo [ERREUR] Python portable introuvable.
    echo Lance setup.bat en premier.
    pause & exit /b 1
)

python\python.exe -c "import mss, cv2, numpy, pynput, PIL" 2>nul
if errorlevel 1 (
    echo Librairies manquantes, installation en cours...
    python\python.exe -m pip install -r requirements.txt
)

python\python.exe main.py
if errorlevel 1 (
    echo.
    echo [ERREUR] L'assistant s'est arrete. Message ci-dessus.
    pause
)
