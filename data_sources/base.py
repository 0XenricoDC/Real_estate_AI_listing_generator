"""
Interfaccia base per tutte le sorgenti dati (API e Scrapers)
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Callable
from models.lead import Lead
from models.search_filters import SearchFilters


class BaseDataSource(ABC):
    """
    Classe base astratta per tutte le sorgenti dati.
    Fornisce un'interfaccia comune per API e Scrapers.
    """

    def __init__(self):
        self._progress_callback: Optional[Callable[[str], None]] = None

    @property
    @abstractmethod
    def nome_portale(self) -> str:
        """Nome del portale (es. 'Idealista', 'Immobiliare')"""
        pass

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Tipo di sorgente: 'api' o 'scraper'"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Verifica se la sorgente dati è disponibile.
        Per API: verifica se le credenziali sono configurate.
        Per Scraper: sempre True.
        """
        pass

    @abstractmethod
    def search(self, filters: SearchFilters) -> List[Lead]:
        """
        Esegue la ricerca e ritorna la lista di Lead trovati.
        """
        pass

    def set_progress_callback(self, callback: Callable[[str], None]):
        """Imposta la callback per aggiornamenti di progresso"""
        self._progress_callback = callback

    def log_progress(self, message: str):
        """Logga un messaggio di progresso"""
        source_type = "API" if self.source_type == "api" else "Scraper"
        if self._progress_callback:
            self._progress_callback(f"[{self.nome_portale}] [{source_type}] {message}")
