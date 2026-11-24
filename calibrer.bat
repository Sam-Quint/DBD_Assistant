@echo off
title Assistant DBD - Calibration
cd /d "%~dp0"

if exist "python\python.exe" (set PY=python\python.exe) else (set PY=python)

%PY% -c "import mss, cv2, numpy, pynput, PIL" 2>nul
if errorlevel 1 (
    echo Librairies manquantes : lance setup.bat d'abord.
    pause & exit /b 1
)

:menu
cls
echo.
echo  === Assistant DBD - Calibration ===
echo.
echo  1  Reglage automatique des portraits  ^<^<^< COMMENCER PAR LA
echo  4  Calibrer a la main (si le reglage automatique ne tombe pas juste)
echo  2  Capturer les templates d'icones  ^<^<^< FAIRE EN JEU
echo  3  Tester la detection en temps reel
echo  Q  Quitter
echo.
set /p choix=Choix :

if /i "%choix%"=="1" (%PY% tools\auto_calibrer.py & goto :menu)
if /i "%choix%"=="4" (%PY% tools\calibrer_roi.py & goto :menu)
if /i "%choix%"=="2" (%PY% tools\capture_icon.py & goto :menu)
if /i "%choix%"=="3" (%PY% tools\test_vision.py & pause & goto :menu)
if /i "%choix%"=="q" exit /b 0
goto :menu
