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
    echo [OK] Python portable déjà présent.
    goto :install_deps
)

echo [1/4] Téléchargement de Python 3.12 portable...
set PY_URL=https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip
set PY_ZIP=python_embed.zip

powershell -Command "Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_ZIP%'" 2>nul
if errorlevel 1 (
    echo [ERREUR] Téléchargement échoué. Vérifie ta connexion internet.
    pause & exit /b 1
)

echo [2/4] Extraction de Python...
powershell -Command "Expand-Archive -Path '%PY_ZIP%' -DestinationPath 'python' -Force"
del "%PY_ZIP%"

echo [3/4] Configuration de Python portable...
powershell -Command "(Get-Content 'python\python312._pth') -replace '#import site','import site' | Set-Content 'python\python312._pth'"

powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'get-pip.py'" 2>nul
python\python.exe get-pip.py --quiet
del "get-pip.py"

:install_deps
echo [4/4] Installation des librairies...
python\python.exe -m pip install -r requirements.txt --quiet

echo.
echo  Setup terminé !
echo  Lance start.bat pour démarrer l'assistant.
echo  Lance calibrer.bat pour calibrer les portraits.
echo.
pause
