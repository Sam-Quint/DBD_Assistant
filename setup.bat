@echo off
chcp 65001 >nul
title Assistant DBD — Setup
echo.
echo  ╔══════════════════════════════════════╗
echo  ║     Assistant DBD — Setup            ║
echo  ╚══════════════════════════════════════╝
echo.

cd /d "%~dp0"

if exist "python\python.exe" (
    python\python.exe -c "import tkinter" 2>nul
    if not errorlevel 1 (
        echo [OK] Python portable déjà présent.
        goto :install_deps
    )
    echo [INFO] Le Python portable existant n'a pas tkinter ^(necessaire a l'overlay^) : reinstallation.
    rmdir /s /q python
)

echo [1/3] Téléchargement de Python 3.12 ^(installeur officiel python.org^)...
set PY_URL=https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe
powershell -Command "Invoke-WebRequest -Uri '%PY_URL%' -OutFile 'python_installer.exe'" 2>nul
if errorlevel 1 (
    echo [ERREUR] Téléchargement échoué. Vérifie ta connexion internet.
    pause & exit /b 1
)

echo [2/3] Installation de Python dans le dossier du projet ^(sans droits administrateur, ne modifie pas le PATH^)...
start /wait "" python_installer.exe /quiet InstallAllUsers=0 "TargetDir=%~dp0python" Include_tcltk=1 Include_pip=1 Include_launcher=0 Include_test=0 Include_doc=0 Include_dev=0 Shortcuts=0 AssociateFiles=0 PrependPath=0 CompileAll=0
del python_installer.exe
if not exist "python\python.exe" (
    echo [ERREUR] L'installation de Python a échoué.
    pause & exit /b 1
)

:install_deps
echo [3/3] Installation des librairies...
python\python.exe -m pip install -r requirements.txt --quiet

echo.
echo  Setup terminé !
echo  Lance start.bat pour démarrer l'assistant.
echo  Lance calibrer.bat pour calibrer les portraits.
echo.
pause
