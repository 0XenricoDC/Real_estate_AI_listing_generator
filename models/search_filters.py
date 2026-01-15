"""
Modello dati per i filtri di ricerca
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SearchFilters:
    """Filtri per la ricerca di immobili"""

    # Località
    localita: str = ""
    raggio_km: int = 20

    # Prezzo
    prezzo_min: Optional[int] = None
    prezzo_max: Optional[int] = None

    # Caratteristiche immobile
    tipo_immobile: str = "Tutti"
    stato_immobile: str = "Tutti"
    mq_min: Optional[int] = None
    mq_max: Optional[int] = None
    locali_min: Optional[int] = None
    locali_max: Optional[int] = None

    # Siti da cercare
    siti_attivi: List[str] = field(default_factory=lambda: [
        'subito', 'immobiliare', 'idealista', 'casa', 'bakeca'
    ])

    # Numero massimo di risultati per sito
    max_risultati_per_sito: int = 100

    def validate(self) -> tuple[bool, str]:
        """
        Valida i filtri e ritorna (valido, messaggio_errore)
        """
        if not self.localita or not self.localita.strip():
            return False, "Inserisci una località per la ricerca"

        if self.prezzo_min and self.prezzo_max and self.prezzo_min > self.prezzo_max:
            return False, "Il prezzo minimo non può essere maggiore del prezzo massimo"

        if self.mq_min and self.mq_max and self.mq_min > self.mq_max:
            return False, "I mq minimi non possono essere maggiori dei mq massimi"

        if self.locali_min and self.locali_max and self.locali_min > self.locali_max:
            return False, "I locali minimi non possono essere maggiori dei locali massimi"

        if not self.siti_attivi:
            return False, "Seleziona almeno un sito per la ricerca"

        return True, ""

    def to_dict(self) -> dict:
        """Converte i filtri in dizionario"""
        return {
            'localita': self.localita,
            'raggio_km': self.raggio_km,
            'prezzo_min': self.prezzo_min,
            'prezzo_max': self.prezzo_max,
            'tipo_immobile': self.tipo_immobile,
            'stato_immobile': self.stato_immobile,
            'mq_min': self.mq_min,
            'mq_max': self.mq_max,
            'locali_min': self.locali_min,
            'locali_max': self.locali_max,
            'siti_attivi': self.siti_attivi,
            'max_risultati_per_sito': self.max_risultati_per_sito
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SearchFilters':
        """Crea un oggetto SearchFilters da un dizionario"""
        return cls(**data)

    def get_prezzo_display(self) -> str:
        """Ritorna una stringa formattata per il range di prezzo"""
        if self.prezzo_min and self.prezzo_max:
            return f"€{self.prezzo_min:,} - €{self.prezzo_max:,}".replace(',', '.')
        elif self.prezzo_min:
            return f"Da €{self.prezzo_min:,}".replace(',', '.')
        elif self.prezzo_max:
            return f"Fino a €{self.prezzo_max:,}".replace(',', '.')
        return "Qualsiasi prezzo"

    def __str__(self) -> str:
        """Rappresentazione testuale dei filtri"""
        parts = [f"Località: {self.localita} ({self.raggio_km}km)"]

        if self.prezzo_min or self.prezzo_max:
            parts.append(f"Prezzo: {self.get_prezzo_display()}")

        if self.tipo_immobile != "Tutti":
            parts.append(f"Tipo: {self.tipo_immobile}")

        if self.stato_immobile != "Tutti":
            parts.append(f"Stato: {self.stato_immobile}")

        parts.append(f"Siti: {', '.join(self.siti_attivi)}")

        return " | ".join(parts)
