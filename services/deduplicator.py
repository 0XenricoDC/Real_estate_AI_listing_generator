"""
Servizio per la rimozione dei duplicati tra i lead
"""

from typing import List, Set, Tuple
import re

from models.lead import Lead


class Deduplicator:
    """
    Servizio per identificare e rimuovere lead duplicati.
    Due lead sono considerati duplicati se:
    - Hanno lo stesso numero di telefono
    - Hanno lo stesso indirizzo e comune
    """

    def __init__(self):
        self.seen_phones: Set[str] = set()
        self.seen_addresses: Set[Tuple[str, str]] = set()

    def normalize_phone(self, phone: str) -> str:
        """
        Normalizza un numero di telefono per il confronto.
        Rimuove spazi, trattini e prefisso internazionale.
        """
        if not phone:
            return ""

        # Rimuovi tutto tranne i numeri
        normalized = re.sub(r'[^\d]', '', phone)

        # Rimuovi prefisso italiano se presente
        if normalized.startswith('39') and len(normalized) > 10:
            normalized = normalized[2:]
        elif normalized.startswith('0039') and len(normalized) > 12:
            normalized = normalized[4:]

        return normalized

    def normalize_address(self, address: str) -> str:
        """
        Normalizza un indirizzo per il confronto.
        """
        if not address:
            return ""

        # Converti in minuscolo
        normalized = address.lower().strip()

        # Rimuovi punteggiatura comune
        normalized = re.sub(r'[,.\-\'\"()]', ' ', normalized)

        # Normalizza abbreviazioni comuni
        replacements = {
            'via': 'v',
            'viale': 'vle',
            'piazza': 'p.za',
            'piazzale': 'p.le',
            'corso': 'c.so',
            'largo': 'l.go',
            'vicolo': 'vic',
            'strada': 'str',
            'borgo': 'b.go'
        }

        words = normalized.split()
        normalized_words = []
        for word in words:
            normalized_words.append(replacements.get(word, word))

        # Rimuovi spazi multipli
        return ' '.join(normalized_words)

    def normalize_comune(self, comune: str) -> str:
        """
        Normalizza il nome del comune per il confronto.
        """
        if not comune:
            return ""

        # Converti in minuscolo e rimuovi spazi extra
        normalized = comune.lower().strip()

        # Rimuovi suffissi comuni
        suffixes_to_remove = [
            ' (mi)', ' (rm)', ' (na)', ' (to)', ' (bo)',  # Province
            ' città', ' centro', ' paese'
        ]

        for suffix in suffixes_to_remove:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]

        return normalized

    def is_duplicate(self, lead: Lead) -> bool:
        """
        Verifica se un lead è un duplicato di uno già visto.

        Returns:
            True se è un duplicato, False altrimenti
        """
        # Controlla telefono
        if lead.telefono:
            normalized_phone = self.normalize_phone(lead.telefono)
            if normalized_phone and len(normalized_phone) >= 9:  # Telefono valido
                if normalized_phone in self.seen_phones:
                    return True
                self.seen_phones.add(normalized_phone)

        # Controlla indirizzo + comune
        if lead.via_indirizzo and lead.comune:
            normalized_addr = self.normalize_address(lead.via_indirizzo)
            normalized_comune = self.normalize_comune(lead.comune)

            if normalized_addr and normalized_comune:
                address_key = (normalized_addr, normalized_comune)
                if address_key in self.seen_addresses:
                    return True
                self.seen_addresses.add(address_key)

        return False

    def remove_duplicates(self, leads: List[Lead]) -> Tuple[List[Lead], int]:
        """
        Rimuove i duplicati da una lista di lead.

        Args:
            leads: Lista di Lead da deduplicare

        Returns:
            Tuple (lista_dedupplicata, numero_duplicati_rimossi)
        """
        # Reset dei set per una nuova deduplicazione
        self.seen_phones.clear()
        self.seen_addresses.clear()

        unique_leads = []
        duplicates_count = 0

        for lead in leads:
            if not self.is_duplicate(lead):
                unique_leads.append(lead)
            else:
                duplicates_count += 1

        return unique_leads, duplicates_count

    def merge_leads(self, lead1: Lead, lead2: Lead) -> Lead:
        """
        Unisce due lead duplicati prendendo i dati migliori da entrambi.
        Utile quando lo stesso immobile è presente su più siti.

        Args:
            lead1: Primo lead
            lead2: Secondo lead

        Returns:
            Lead unificato con i dati più completi
        """
        merged = Lead()

        # Per ogni campo, prendi il valore non vuoto (preferendo lead1)
        merged.nome_venditore = lead1.nome_venditore or lead2.nome_venditore
        merged.cognome_venditore = lead1.cognome_venditore or lead2.cognome_venditore
        merged.telefono = lead1.telefono or lead2.telefono
        merged.email = lead1.email or lead2.email
        merged.via_indirizzo = lead1.via_indirizzo or lead2.via_indirizzo
        merged.comune = lead1.comune or lead2.comune
        merged.provincia = lead1.provincia or lead2.provincia
        merged.cap = lead1.cap or lead2.cap
        merged.prezzo_richiesto = lead1.prezzo_richiesto or lead2.prezzo_richiesto
        merged.tipo_immobile = lead1.tipo_immobile or lead2.tipo_immobile
        merged.mq = lead1.mq or lead2.mq
        merged.locali = lead1.locali or lead2.locali
        merged.stato_immobile = lead1.stato_immobile or lead2.stato_immobile

        # Descrizione: prendi la più lunga
        if len(lead1.descrizione or "") >= len(lead2.descrizione or ""):
            merged.descrizione = lead1.descrizione
        else:
            merged.descrizione = lead2.descrizione

        # URL: combina le fonti
        merged.url_annuncio = lead1.url_annuncio
        merged.fonte = f"{lead1.fonte}, {lead2.fonte}" if lead2.fonte else lead1.fonte

        # Data: prendi la più recente
        if lead1.data_pubblicazione and lead2.data_pubblicazione:
            merged.data_pubblicazione = max(lead1.data_pubblicazione, lead2.data_pubblicazione)
        else:
            merged.data_pubblicazione = lead1.data_pubblicazione or lead2.data_pubblicazione

        # Score: prendi il migliore
        merged.lead_score = max(lead1.lead_score, lead2.lead_score)
        merged.priorita = lead1.priorita if lead1.lead_score >= lead2.lead_score else lead2.priorita

        # Note: combina
        notes = []
        if lead1.note:
            notes.append(lead1.note)
        if lead2.note:
            notes.append(lead2.note)
        merged.note = " | ".join(notes)

        return merged

    def get_statistics(self) -> dict:
        """
        Ritorna statistiche sulla deduplicazione.
        """
        return {
            'telefoni_unici': len(self.seen_phones),
            'indirizzi_unici': len(self.seen_addresses)
        }
