@echo off
title Agente Acquisizione Immobili
cd /d "%~dp0"

echo ================================================
echo   AGENTE ACQUISIZIONE IMMOBILI
echo ================================================
echo.
echo Avvio applicazione...
echo.

python main.py

if errorlevel 1 (
    echo.
    echo ================================================
    echo   ERRORE: L'applicazione non si e' avviata
    echo ================================================
    echo.
    echo Possibili cause:
    echo   - Python non e' installato o non e' nel PATH
    echo   - Dipendenze mancanti (esegui: pip install playwright openpyxl)
    echo   - Browser non installato (esegui: playwright install chromium)
    echo.
    pause
)
