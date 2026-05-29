@echo off
chcp 65001 >nul
title Assistant DBD

cd /d "%~dp0"

if not exist "python\python.exe" (
    echo [ERREUR] Python portable introuvable.
    echo Lance setup.bat en premier.
    pause & exit /b 1
)

python\python.exe main.py
