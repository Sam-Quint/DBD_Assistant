@echo off
rem Reserve au developpeur (SDK .NET 9 requis sur CETTE machine).
rem Produit publish\DbdAssistant.exe : un seul fichier, aucun .NET a installer chez l'utilisateur.
cd /d "%~dp0"

if exist publish rmdir /s /q publish
dotnet publish src\DbdAssistant.App -c Release -o publish
if errorlevel 1 (
    echo [ERREUR] La publication a echoue.
    pause & exit /b 1
)

echo.
echo  Termine : %~dp0publish\DbdAssistant.exe
echo  Copie ce fichier sur le PC de l'utilisateur et double-clique dessus.
echo.
pause
