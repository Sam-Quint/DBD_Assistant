@echo off
title Assistant DBD - Setup
cd /d "%~dp0"
echo.
echo  === Assistant DBD - Setup ===
echo.

if exist "python\python.exe" (
    python\python.exe -c "import tkinter" 2>nul
    if not errorlevel 1 (
        echo [OK] Python portable deja present.
        set PY=python\python.exe
        goto :install_deps
    )
    echo [INFO] Le Python portable existant n'a pas tkinter : reinstallation.
    rmdir /s /q python
)

rem Python du systeme (3.12+ avec tkinter) : pas besoin de telecharger
python -c "import tkinter" 2>nul
if not errorlevel 1 (
    echo [OK] Python du systeme utilise.
    set PY=python
    goto :install_deps
)

echo [1/3] Telechargement de Python 3.12 (installeur officiel python.org)...
set PY_URL=https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe
powershell -Command "Invoke-WebRequest -Uri '%PY_URL%' -OutFile 'python_installer.exe'" 2>nul
if errorlevel 1 (
    echo [ERREUR] Telechargement echoue. Verifie ta connexion internet.
    pause & exit /b 1
)

echo [2/3] Installation de Python dans le dossier du projet...
start /wait "" python_installer.exe /quiet /log "%~dp0python_install.log" InstallAllUsers=0 "TargetDir=%~dp0python" Include_tcltk=1 Include_pip=1 Include_launcher=0 Include_test=0 Include_doc=0 Include_dev=0 Shortcuts=0 AssociateFiles=0 PrependPath=0 CompileAll=0
del python_installer.exe
if not exist "python\python.exe" (
    echo [ERREUR] L'installation de Python a echoue. Journal : %~dp0python_install.log
    pause & exit /b 1
)
set PY=python\python.exe

:install_deps
echo [3/3] Installation des librairies...
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERREUR] Installation des librairies echouee.
    pause & exit /b 1
)

echo.
echo  Setup termine. Lance start.bat puis calibrer.bat.
echo.
pause
