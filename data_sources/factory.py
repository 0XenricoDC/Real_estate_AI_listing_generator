"""
Factory per la selezione delle sorgenti dati.

Logica:
- Per Idealista e Immobiliare.it: usa API se le credenziali sono configurate,
  altrimenti fallback su scraper
- Per Subito, Casa, Bakeca: usa sempre scraper (non hanno API pubbliche)
"""

from typing import List, Dict, Optional
from data_sources.base import BaseDataSource
from config import (
    IDEALISTA_API_KEY,
    IDEALISTA_API_SECRET,
    IMMOBILIARE_API_KEY,
    USE_API_WHEN_AVAILABLE
)


# Cache delle istanze
_data_sources: Dict[str, BaseDataSource] = {}


def _create_idealista_source() -> BaseDataSource:
    """Crea la sorgente dati per Idealista"""
    # Se API disponibile e abilitata, usa API
    if USE_API_WHEN_AVAILABLE and IDEALISTA_API_KEY and IDEALISTA_API_SECRET:
        from data_sources.api.idealista_api import IdealistaAPI
        return IdealistaAPI()

    # Altrimenti usa scraper
    from scrapers.idealista_scraper import IdealistaScraper
    return IdealistaScraper()


def _create_immobiliare_source() -> BaseDataSource:
    """Crea la sorgente dati per Immobiliare.it"""
    # Se API disponibile e abilitata, usa API
    if USE_API_WHEN_AVAILABLE and IMMOBILIARE_API_KEY:
        from data_sources.api.immobiliare_api import ImmobiliareAPI
        return ImmobiliareAPI()

    # Altrimenti usa scraper
    from scrapers.immobiliare_scraper import ImmobiliareScraper
    return ImmobiliareScraper()


def _create_subito_source() -> BaseDataSource:
    """Crea la sorgente dati per Subito (solo scraper)"""
    from scrapers.subito_scraper import SubitoScraper
    return SubitoScraper()


def _create_casa_source() -> BaseDataSource:
    """Crea la sorgente dati per Casa.it (solo scraper)"""
    from scrapers.casa_scraper import CasaScraper
    return CasaScraper()


def _create_bakeca_source() -> BaseDataSource:
    """Crea la sorgente dati per Bakeca (solo scraper)"""
    from scrapers.bakeca_scraper import BakecaScraper
    return BakecaScraper()


# Mapping nome portale -> funzione di creazione
_SOURCE_CREATORS = {
    'idealista': _create_idealista_source,
    'immobiliare': _create_immobiliare_source,
    'subito': _create_subito_source,
    'casa': _create_casa_source,
    'bakeca': _create_bakeca_source
}


def get_data_source(portal_name: str, force_scraper: bool = False) -> Optional[BaseDataSource]:
    """
    Ottiene la sorgente dati per un portale specifico.

    Args:
        portal_name: Nome del portale (es. 'idealista', 'immobiliare')
        force_scraper: Se True, forza l'uso dello scraper anche se API disponibile

    Returns:
        Istanza di BaseDataSource o None se portale non supportato
    """
    portal_name = portal_name.lower()

    if portal_name not in _SOURCE_CREATORS:
        return None

    # Chiave cache (include force_scraper per differenziare)
    cache_key = f"{portal_name}{'_scraper' if force_scraper else ''}"

    if cache_key not in _data_sources:
        if force_scraper:
            # Forza scraper
            if portal_name == 'idealista':
                from scrapers.idealista_scraper import IdealistaScraper
                _data_sources[cache_key] = IdealistaScraper()
            elif portal_name == 'immobiliare':
                from scrapers.immobiliare_scraper import ImmobiliareScraper
                _data_sources[cache_key] = ImmobiliareScraper()
            else:
                _data_sources[cache_key] = _SOURCE_CREATORS[portal_name]()
        else:
            _data_sources[cache_key] = _SOURCE_CREATORS[portal_name]()

    return _data_sources[cache_key]


def get_all_data_sources(portal_names: List[str], force_scraper: bool = False) -> List[BaseDataSource]:
    """
    Ottiene le sorgenti dati per una lista di portali.

    Args:
        portal_names: Lista di nomi portali
        force_scraper: Se True, forza l'uso degli scraper

    Returns:
        Lista di istanze BaseDataSource
    """
    sources = []
    for name in portal_names:
        source = get_data_source(name, force_scraper)
        if source:
            sources.append(source)
    return sources


def get_available_sources_info() -> Dict[str, Dict]:
    """
    Ritorna informazioni sulle sorgenti disponibili per ogni portale.

    Returns:
        Dict con info per ogni portale:
        {
            'idealista': {
                'api_available': True/False,
                'api_configured': True/False,
                'will_use': 'api' o 'scraper'
            },
            ...
        }
    """
    info = {}

    # Idealista
    api_configured = bool(IDEALISTA_API_KEY and IDEALISTA_API_SECRET)
    info['idealista'] = {
        'api_available': True,
        'api_configured': api_configured,
        'will_use': 'api' if (USE_API_WHEN_AVAILABLE and api_configured) else 'scraper'
    }

    # Immobiliare.it
    api_configured = bool(IMMOBILIARE_API_KEY)
    info['immobiliare'] = {
        'api_available': True,
        'api_configured': api_configured,
        'will_use': 'api' if (USE_API_WHEN_AVAILABLE and api_configured) else 'scraper'
    }

    # Portali senza API
    for portal in ['subito', 'casa', 'bakeca']:
        info[portal] = {
            'api_available': False,
            'api_configured': False,
            'will_use': 'scraper'
        }

    return info


def clear_cache():
    """Pulisce la cache delle sorgenti dati"""
    global _data_sources
    _data_sources = {}
