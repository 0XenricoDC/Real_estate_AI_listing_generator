"""
Modello dati per un Lead immobiliare
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime


@dataclass
class Lead:
    """Rappresenta un lead immobiliare estratto da un portale"""

    # Dati del venditore
    nome_venditore: str = ""
    cognome_venditore: str = ""
    telefono: str = ""
    email: str = ""

    # Dati dell'immobile
    via_indirizzo: str = ""
    comune: str = ""
    provincia: str = ""
    cap: str = ""
    prezzo_richiesto: int = 0
    tipo_immobile: str = ""
    mq: int = 0
    locali: int = 0
    stato_immobile: str = ""
    descrizione: str = ""

    # Metadati annuncio
    url_annuncio: str = ""
    data_pubblicazione: Optional[datetime] = None
    fonte: str = ""

    # Scoring
    lead_score: int = 0
    priorita: str = "BASSA"

    # Note aggiuntive
    note: str = ""

    # Timestamp di estrazione
    data_estrazione: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Converte il lead in dizionario per export"""
        data = asdict(self)
        # Converti datetime in stringa
        if self.data_pubblicazione:
            data['data_pubblicazione'] = self.data_pubblicazione.strftime('%d/%m/%Y')
        else:
            data['data_pubblicazione'] = ''
        data['data_estrazione'] = self.data_estrazione.strftime('%d/%m/%Y %H:%M')
        return data

    def to_excel_row(self) -> list:
        """Ritorna i dati come lista per riga Excel"""
        return [
            self.lead_score,
            self.priorita,
            self.nome_venditore,
            self.cognome_venditore,
            self.telefono,
            self.email,
            self.via_indirizzo,
            self.comune,
            self.provincia,
            f"€ {self.prezzo_richiesto:,}".replace(',', '.') if self.prezzo_richiesto else "",
            self.tipo_immobile,
            self.mq if self.mq else "",
            self.locali if self.locali else "",
            self.stato_immobile,
            self.data_pubblicazione.strftime('%d/%m/%Y') if self.data_pubblicazione else "",
            self.fonte,
            self.url_annuncio,
            self.note
        ]

    @property
    def nome_completo(self) -> str:
        """Ritorna nome e cognome combinati"""
        parts = [self.nome_venditore, self.cognome_venditore]
        return ' '.join(p for p in parts if p).strip()

    @property
    def indirizzo_completo(self) -> str:
        """Ritorna l'indirizzo completo formattato"""
        parts = []
        if self.via_indirizzo:
            parts.append(self.via_indirizzo)
        if self.cap:
            parts.append(self.cap)
        if self.comune:
            parts.append(self.comune)
        if self.provincia:
            parts.append(f"({self.provincia})")
        return ' '.join(parts)

    def has_contact_info(self) -> bool:
        """Verifica se il lead ha informazioni di contatto valide"""
        return bool(self.telefono or self.email)

    def __hash__(self):
        """Hash basato su telefono e indirizzo per deduplicazione"""
        return hash((self.telefono, self.via_indirizzo, self.comune))

    def __eq__(self, other):
        """Due lead sono uguali se hanno stesso telefono O stesso indirizzo+comune"""
        if not isinstance(other, Lead):
            return False
        # Stesso telefono (se presente)
        if self.telefono and other.telefono and self.telefono == other.telefono:
            return True
        # Stesso indirizzo e comune
        if (self.via_indirizzo and other.via_indirizzo and
            self.comune and other.comune and
            self.via_indirizzo.lower() == other.via_indirizzo.lower() and
            self.comune.lower() == other.comune.lower()):
            return True
        return False
