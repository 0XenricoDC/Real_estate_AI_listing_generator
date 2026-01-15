# Agente Acquisizione Immobili

Sistema di scraping multi-piattaforma per acquisizione lead immobiliari da privati.

## Build & Development

```bash
# Installazione dipendenze
pip install -r requirements.txt

# Installazione browser Playwright
playwright install chromium

# Avvio GUI
python main.py

# Oppure con batch file
avvia.bat
```

## Architecture

```
agente_immobiliare/
├── main.py              # Entry point applicazione
├── config.py            # Configurazioni, costanti, API keys
├── scrapers/            # Scraper per ogni portale
│   ├── base_scraper.py      # Classe base (Playwright async)
│   ├── subito_scraper.py    # Subito.it
│   ├── immobiliare_scraper.py
│   ├── idealista_scraper.py
│   ├── casa_scraper.py
│   └── bakeca_scraper.py
├── gui/                 # Interfaccia Tkinter
│   ├── main_window.py       # Finestra principale
│   ├── filters_frame.py     # Frame filtri ricerca
│   ├── results_frame.py     # Tabella risultati
│   ├── progress_dialog.py   # Dialog progresso
│   └── proxy_dialog.py      # Configurazione proxy
├── data_sources/        # API clients (Idealista, Immobiliare.it)
├── models/              # Pydantic models
└── services/            # Servizi supporto
```

## Key Features

- **Multi-portale**: Subito, Immobiliare.it, Idealista, Casa.it, Bakeca
- **Filtro privati**: Esclude automaticamente agenzie
- **Lead scoring**: Sistema di qualificazione 1-100
- **Export Excel**: Fogli separati per priorita (Alta/Media/Bassa)
- **Proxy support**: Configurazione proxy residenziali
- **Rate limiting**: Delay randomizzato tra richieste

## Configuration (config.py)

- `USE_API_WHEN_AVAILABLE`: Usa API ufficiali se disponibili
- `IDEALISTA_API_KEY/SECRET`: Credenziali API Idealista
- `IMMOBILIARE_API_KEY`: Credenziali API Immobiliare.it
- `PROXY_ENABLED`: Abilita proxy
- `SCORING_WEIGHTS`: Pesi per calcolo lead score

## Lead Scoring Formula

```
SCORE = (PrezzoScore * 0.30) + (UrgenzaScore * 0.25) +
        (MargineScore * 0.20) + (CompletezzaScore * 0.10) +
        (AnzianitaScore * 0.10) + (ZonaScore * 0.05)
```

## Output

File Excel con fogli:
1. Lead Alta Priorita (Score 70-100)
2. Lead Media Priorita (Score 40-69)
3. Lead Bassa Priorita (Score 1-39)
4. Tutti i Lead
5. Statistiche
