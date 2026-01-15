@echo off
title Installazione Agente Immobiliare
cd /d "%~dp0"

echo ================================================
echo   INSTALLAZIONE DIPENDENZE
echo   Agente Acquisizione Immobili
echo ================================================
echo.

echo [1/3] Installazione librerie Python...
pip install playwright openpyxl playwright-stealth
if errorlevel 1 (
    echo ERRORE: Installazione pip fallita
    pause
    exit /b 1
)

echo.
echo [2/3] Installazione browser Chromium...
python -m playwright install chromium
if errorlevel 1 (
    echo ERRORE: Installazione browser fallita
    pause
    exit /b 1
)

echo.
echo [3/3] Verifica installazione...
python -c "import playwright; import openpyxl; print('OK')"
if errorlevel 1 (
    echo ERRORE: Verifica fallita
    pause
    exit /b 1
)

echo.
echo ================================================
echo   INSTALLAZIONE COMPLETATA!
echo ================================================
echo.
echo Ora puoi avviare l'applicazione con:
echo   - Doppio click su "avvia.bat"
echo   - Oppure: python main.py
echo.
pause
