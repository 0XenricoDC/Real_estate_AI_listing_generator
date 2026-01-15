#!/usr/bin/env python3
"""
Agente Acquisizione Immobili
============================

Applicazione per la ricerca automatizzata di annunci immobiliari
da privati su portali italiani (Subito, Immobiliare, Idealista, Casa.it, Bakeca).

Funzionalità:
- Scraping multi-piattaforma con filtri configurabili
- Sistema di scoring e qualificazione lead (1-100)
- Classificazione automatica per priorità (Alta/Media/Bassa)
- Export in Excel con formattazione e fogli separati
- GUI semplice e intuitiva

Uso:
    python main.py

Requisiti:
    pip install playwright openpyxl
    playwright install chromium

Autore: Agente AI
"""

import sys
import os

# Aggiungi la directory corrente al path per gli import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_dependencies():
    """Verifica che le dipendenze siano installate"""
    missing = []

    try:
        import playwright
    except ImportError:
        missing.append('playwright')

    try:
        import openpyxl
    except ImportError:
        missing.append('openpyxl')

    try:
        import requests
    except ImportError:
        missing.append('requests')

    if missing:
        print("=" * 50)
        print("DIPENDENZE MANCANTI")
        print("=" * 50)
        print(f"\nLe seguenti librerie non sono installate: {', '.join(missing)}")
        print("\nEsegui i seguenti comandi per installarle:")
        print(f"\n  pip install {' '.join(missing)}")
        if 'playwright' in missing:
            print("  playwright install chromium")
        print("\n" + "=" * 50)
        return False

    return True


def check_playwright_browsers():
    """Verifica che i browser di Playwright siano installati"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Prova ad avviare chromium
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception as e:
        if 'Executable doesn\'t exist' in str(e) or 'browserType.launch' in str(e):
            print("=" * 50)
            print("BROWSER NON INSTALLATO")
            print("=" * 50)
            print("\nI browser di Playwright non sono installati.")
            print("\nEsegui il seguente comando:")
            print("\n  playwright install chromium")
            print("\n" + "=" * 50)
            return False
        # Altri errori potrebbero essere OK
        return True


def main():
    """Entry point dell'applicazione"""
    print("\n" + "=" * 50)
    print("  AGENTE ACQUISIZIONE IMMOBILI")
    print("=" * 50)
    print("\nControllo dipendenze...")

    # Verifica dipendenze
    if not check_dependencies():
        input("\nPremi INVIO per uscire...")
        sys.exit(1)

    print("Dipendenze OK!")
    print("\nControllo browser Playwright...")

    # Verifica browser Playwright
    if not check_playwright_browsers():
        input("\nPremi INVIO per uscire...")
        sys.exit(1)

    print("Browser OK!")
    print("\nAvvio interfaccia grafica...")
    print("=" * 50 + "\n")

    # Avvia la GUI
    try:
        from gui.main_window import MainWindow
        app = MainWindow()
        app.run()
    except Exception as e:
        print(f"\nErrore durante l'avvio: {str(e)}")
        import traceback
        traceback.print_exc()
        input("\nPremi INVIO per uscire...")
        sys.exit(1)


if __name__ == '__main__':
    main()
