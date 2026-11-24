@echo off
chcp 65001 >nul
title Assistant DBD — Reglage des portraits
cd /d "%~dp0"
DBD_Assistant.exe --calibrer
pause
