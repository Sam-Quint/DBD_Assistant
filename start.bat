@echo off
title Assistant DBD
cd /d "%~dp0"

if exist "python\python.exe" (set PY=python\python.exe) else (set PY=python)

%PY% -c "import mss, cv2, numpy, pynput, PIL" 2>nul
if errorlevel 1 (
    echo Librairies manquantes, installation en cours...
    %PY% -m pip install -r requirements.txt
)

%PY% main.py
if errorlevel 1 (
    echo.
    echo [ERREUR] L'assistant s'est arrete. Message ci-dessus.
)
pause
