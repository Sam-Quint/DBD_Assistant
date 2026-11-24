@echo off
chcp 65001 >nul
title Assistant DBD — Build de l'executable
rem Construit dist\DBD_Assistant\ (exécutable autonome, sans Python requis pour les joueurs).
rem Réservé aux développeurs : nécessite Python 3.12+ avec tkinter sur CETTE machine.

cd /d "%~dp0"

if not exist ".buildenv\Scripts\python.exe" (
    echo [1/4] Creation de l'environnement de build...
    python -m venv .buildenv || (echo [ERREUR] Python introuvable. & pause & exit /b 1)
)

echo [2/4] Installation des dependances...
.buildenv\Scripts\python.exe -m pip install --quiet -r requirements.txt pyinstaller || (pause & exit /b 1)

echo [3/4] Construction de l'executable...
.buildenv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --name DBD_Assistant ^
    --add-data "assets\statuts;assets\statuts" ^
    --hidden-import pynput.keyboard._win32 --hidden-import pynput.mouse._win32 ^
    --collect-submodules tools main.py || (pause & exit /b 1)

echo [4/4] Ajout des lanceurs et creation du zip...
copy /y "release\Calibrer.bat" "dist\DBD_Assistant\Calibrer.bat" >nul
copy /y "release\LISEZMOI.txt" "dist\DBD_Assistant\LISEZMOI.txt" >nul
powershell -Command "Compress-Archive -Path 'dist\DBD_Assistant' -DestinationPath 'dist\DBD_Assistant.zip' -Force"

echo.
echo  Termine : dist\DBD_Assistant.zip
pause
