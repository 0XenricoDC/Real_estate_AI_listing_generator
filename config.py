"""
Configurazioni e costanti per l'Agente Acquisizione Immobili
"""

import os

# ============================================
# CONFIGURAZIONE API
# ============================================
# Imposta a True per usare le API quando disponibili (Idealista, Immobiliare.it)
# Se False, usa sempre gli scraper
USE_API_WHEN_AVAILABLE = True

# --------------------------------------------
# Idealista API
# --------------------------------------------
# Per ottenere le credenziali:
# 1. Vai su https://developers.idealista.com/access-request
# 2. Compila il form con i dettagli del tuo progetto
# 3. Attendi approvazione (1-3 giorni lavorativi)
# 4. Riceverai API_KEY e API_SECRET via email
#
# Puoi impostare le credenziali qui o come variabili d'ambiente:
#   export IDEALISTA_API_KEY="tua_api_key"
#   export IDEALISTA_API_SECRET="tuo_api_secret"

IDEALISTA_API_KEY = os.environ.get('IDEALISTA_API_KEY', '')
IDEALISTA_API_SECRET = os.environ.get('IDEALISTA_API_SECRET', '')

# --------------------------------------------
# Immobiliare.it API (Realitycs)
# --------------------------------------------
# Per ottenere le credenziali:
# 1. Vai su https://www.immobiliare.it/insights/en/api/
# 2. Contatta il team commerciale
# 3. Attendi approvazione
#
# Puoi impostare le credenziali qui o come variabili d'ambiente:
#   export IMMOBILIARE_API_KEY="tua_api_key"

IMMOBILIARE_API_KEY = os.environ.get('IMMOBILIARE_API_KEY', '')
IMMOBILIARE_API_URL = os.environ.get('IMMOBILIARE_API_URL', '')  # URL base API (opzionale)

# ============================================
# SCORING WEIGHTS
# ============================================
# Pesi per il sistema di scoring
SCORING_WEIGHTS = {
    'prezzo_mercato': 0.30,
    'urgenza': 0.25,
    'margine': 0.20,
    'completezza': 0.10,
    'anzianita': 0.10,
    'zona': 0.05
}

# Parole chiave che indicano urgenza di vendita
URGENCY_KEYWORDS = [
    'urgente', 'urge', 'urge vendere',
    'trattabile', 'prezzo trattabile', 'trattativa riservata',
    'trasferimento', 'causa trasferimento', 'per trasferimento',
    'eredità', 'successione',
    'affare', 'occasione', 'ottima occasione',
    'no agenzie', 'no agenzia', 'vendo personalmente',
    'privato vende', 'vendo direttamente',
    'prezzo ribassato', 'ribasso', 'sconto'
]

# Indicatori che identificano un'agenzia immobiliare
AGENCY_INDICATORS = [
    'agenzia', 'immobiliare', 'srl', 's.r.l.',
    'sas', 's.a.s.', 'snc', 's.n.c.',
    'spa', 's.p.a.', 'group', 'real estate',
    'p.iva', 'partita iva', 'p. iva',
    'mediazione', 'intermediazione',
    'consulenza immobiliare', 'studio immobiliare'
]

# Tipi di immobile disponibili
PROPERTY_TYPES = [
    'Tutti',
    'Appartamento',
    'Villa',
    'Casa indipendente',
    'Villetta a schiera',
    'Attico',
    'Loft',
    'Mansarda',
    'Terreno',
    'Terreno edificabile',
    'Box/Garage',
    'Posto auto',
    'Negozio',
    'Ufficio',
    'Capannone',
    'Magazzino'
]

# Stati dell'immobile
PROPERTY_STATES = [
    'Tutti',
    'Nuovo',
    'Ottimo stato',
    'Buono stato',
    'Da ristrutturare',
    'In costruzione'
]

# Opzioni raggio di ricerca (in km)
RADIUS_OPTIONS = [5, 10, 15, 20, 25, 30, 40, 50, 75, 100]

# Delay tra le richieste (in secondi) per evitare ban
REQUEST_DELAY_MIN = 2
REQUEST_DELAY_MAX = 5

# User agents per rotazione
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15'
]

# Soglie per classificazione priorità
PRIORITY_THRESHOLDS = {
    'alta': 70,    # Score >= 70
    'media': 40,   # Score >= 40 e < 70
    'bassa': 0     # Score < 40
}

# Colori per formattazione Excel (formato RGB hex)
EXCEL_COLORS = {
    'alta': '90EE90',      # Verde chiaro
    'media': 'FFFF99',     # Giallo chiaro
    'bassa': 'D3D3D3',     # Grigio chiaro
    'header': '4472C4'     # Blu per intestazioni
}

# Numero massimo di pagine da scrapare per sito
MAX_PAGES_PER_SITE = 10

# Timeout per le richieste (in millisecondi)
REQUEST_TIMEOUT = 30000

# URL base dei portali immobiliari
PORTAL_URLS = {
    'subito': 'https://www.subito.it',
    'immobiliare': 'https://www.immobiliare.it',
    'idealista': 'https://www.idealista.it',
    'casa': 'https://www.casa.it',
    'bakeca': 'https://www.bakeca.it'
}

# ============================================
# CONFIGURAZIONE PROXY
# ============================================

# Abilita/disabilita l'uso del proxy
PROXY_ENABLED = False

# Configurazione proxy
# Formati supportati:
#   - HTTP: http://username:password@host:port
#   - SOCKS5: socks5://username:password@host:port
#
# Esempi di provider consigliati (proxy residenziali):
#   - Bright Data: http://user:pass@brd.superproxy.io:22225
#   - Oxylabs: http://user:pass@pr.oxylabs.io:7777
#   - Smartproxy: http://user:pass@gate.smartproxy.com:7000
#   - IPRoyal: http://user:pass@geo.iproyal.com:12321

PROXY_CONFIG = {
    'server': '',      # es: http://proxy.example.com:8080
    'username': '',    # username (se richiesto)
    'password': ''     # password (se richiesta)
}

# File per salvare la configurazione proxy (persistente)
PROXY_CONFIG_FILE = 'proxy_config.json'

# Provider proxy consigliati con prezzi indicativi
PROXY_PROVIDERS = [
    {
        'name': 'Bright Data',
        'url': 'https://brightdata.com',
        'type': 'Residenziale',
        'price': '~$15/GB',
        'format': 'http://user-zone-ZONE:pass@brd.superproxy.io:22225'
    },
    {
        'name': 'Oxylabs',
        'url': 'https://oxylabs.io',
        'type': 'Residenziale',
        'price': '~$15/GB',
        'format': 'http://user:pass@pr.oxylabs.io:7777'
    },
    {
        'name': 'Smartproxy',
        'url': 'https://smartproxy.com',
        'type': 'Residenziale',
        'price': '~$12.5/GB',
        'format': 'http://user:pass@gate.smartproxy.com:7000'
    },
    {
        'name': 'IPRoyal',
        'url': 'https://iproyal.com',
        'type': 'Residenziale',
        'price': '~$7/GB',
        'format': 'http://user:pass@geo.iproyal.com:12321'
    }
]
