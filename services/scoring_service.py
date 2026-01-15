"""
Servizio per la qualificazione e scoring dei lead immobiliari
"""

from typing import List
from datetime import datetime, timedelta
import re

from models.lead import Lead
from config import (
    SCORING_WEIGHTS,
    URGENCY_KEYWORDS,
    PRIORITY_THRESHOLDS
)


class ScoringService:
    """
    Servizio che calcola il punteggio di qualificazione per ogni lead.
    Il punteggio va da 0 a 100 e considera vari fattori:
    - Prezzo rispetto al mercato (30%)
    - Indicatori di urgenza (25%)
    - Margine potenziale (20%)
    - Completezza dell'annuncio (10%)
    - Anzianità dell'annuncio (10%)
    - Appetibilità della zona (5%)
    """

    def __init__(self, prezzo_medio_zona: int = None):
        """
        Inizializza il servizio di scoring.

        Args:
            prezzo_medio_zona: Prezzo medio al mq nella zona di ricerca.
                              Se non fornito, usa un valore di default.
        """
        self.prezzo_medio_zona = prezzo_medio_zona or 2500  # €/mq default

    def set_prezzo_medio_zona(self, prezzo: int):
        """Imposta il prezzo medio della zona"""
        self.prezzo_medio_zona = prezzo

    def calculate_score(self, lead: Lead) -> int:
        """
        Calcola il punteggio totale per un lead.

        Returns:
            Punteggio da 0 a 100
        """
        scores = {
            'prezzo_mercato': self._score_prezzo_mercato(lead),
            'urgenza': self._score_urgenza(lead),
            'margine': self._score_margine(lead),
            'completezza': self._score_completezza(lead),
            'anzianita': self._score_anzianita(lead),
            'zona': self._score_zona(lead)
        }

        # Calcola punteggio pesato
        total = 0
        for key, score in scores.items():
            weight = SCORING_WEIGHTS.get(key, 0)
            total += score * weight

        return min(100, max(0, int(total)))

    def _score_prezzo_mercato(self, lead: Lead) -> int:
        """
        Valuta il prezzo rispetto al mercato.
        Un prezzo sotto la media di zona ottiene punteggio alto.
        """
        if not lead.prezzo_richiesto or not lead.mq:
            return 50  # Valore neutro se mancano dati

        prezzo_al_mq = lead.prezzo_richiesto / lead.mq

        # Calcola la differenza percentuale rispetto alla media
        diff_percent = ((self.prezzo_medio_zona - prezzo_al_mq) / self.prezzo_medio_zona) * 100

        if diff_percent >= 30:
            return 100  # Molto sotto mercato
        elif diff_percent >= 20:
            return 85
        elif diff_percent >= 10:
            return 70
        elif diff_percent >= 0:
            return 55
        elif diff_percent >= -10:
            return 40
        elif diff_percent >= -20:
            return 25
        else:
            return 10  # Molto sopra mercato

    def _score_urgenza(self, lead: Lead) -> int:
        """
        Valuta gli indicatori di urgenza nella descrizione.
        Più parole chiave di urgenza = punteggio più alto.
        """
        if not lead.descrizione:
            return 30  # Valore basso se manca descrizione

        descrizione_lower = lead.descrizione.lower()
        titolo_lower = (lead.note or "").lower()
        text_to_check = f"{descrizione_lower} {titolo_lower}"

        urgency_count = 0
        found_keywords = []

        for keyword in URGENCY_KEYWORDS:
            if keyword.lower() in text_to_check:
                urgency_count += 1
                found_keywords.append(keyword)

        # Salva le keyword trovate nelle note
        if found_keywords and lead.note:
            lead.note += f" | Urgenza: {', '.join(found_keywords)}"
        elif found_keywords:
            lead.note = f"Urgenza: {', '.join(found_keywords)}"

        if urgency_count >= 3:
            return 100
        elif urgency_count == 2:
            return 80
        elif urgency_count == 1:
            return 60
        else:
            return 30

    def _score_margine(self, lead: Lead) -> int:
        """
        Stima il margine potenziale di guadagno.
        Basato su prezzo, stato dell'immobile e zona.
        """
        if not lead.prezzo_richiesto:
            return 50

        score = 50  # Base

        # Immobili da ristrutturare hanno più margine potenziale
        if lead.stato_immobile:
            stato_lower = lead.stato_immobile.lower()
            if 'ristrutturare' in stato_lower or 'ristrut' in stato_lower:
                score += 20
            elif 'buono' in stato_lower:
                score += 10
            elif 'ottimo' in stato_lower or 'nuovo' in stato_lower:
                score -= 5

        # Prezzo basso = più margine
        if lead.mq and lead.prezzo_richiesto:
            prezzo_mq = lead.prezzo_richiesto / lead.mq
            if prezzo_mq < self.prezzo_medio_zona * 0.7:
                score += 25
            elif prezzo_mq < self.prezzo_medio_zona * 0.85:
                score += 15

        return min(100, max(0, score))

    def _score_completezza(self, lead: Lead) -> int:
        """
        Valuta la completezza dell'annuncio.
        Annunci completi indicano venditori seri.
        """
        score = 0
        max_score = 100

        # Campi presenti
        fields_to_check = [
            (lead.telefono, 20),
            (lead.email, 10),
            (lead.via_indirizzo, 10),
            (lead.comune, 10),
            (lead.prezzo_richiesto, 15),
            (lead.mq, 10),
            (lead.locali, 5),
            (lead.tipo_immobile, 5),
            (lead.stato_immobile, 5),
            (lead.descrizione and len(lead.descrizione) > 100, 10)
        ]

        for field, points in fields_to_check:
            if field:
                score += points

        return min(max_score, score)

    def _score_anzianita(self, lead: Lead) -> int:
        """
        Valuta l'anzianità dell'annuncio.
        Annunci più vecchi indicano possibile maggiore disponibilità a trattare.
        """
        if not lead.data_pubblicazione:
            return 50  # Valore neutro

        days_old = (datetime.now() - lead.data_pubblicazione).days

        if days_old > 90:
            return 100  # Molto vecchio - probabilmente trattabile
        elif days_old > 60:
            return 85
        elif days_old > 30:
            return 70
        elif days_old > 14:
            return 55
        elif days_old > 7:
            return 40
        else:
            return 25  # Molto recente

    def _score_zona(self, lead: Lead) -> int:
        """
        Valuta l'appetibilità della zona.
        Zone più richieste = vendita più veloce.

        Nota: Questa è una valutazione semplificata.
        In produzione si userebbe un database di zone con indici di appetibilità.
        """
        # Per ora usiamo un valore fisso medio
        # In futuro si potrebbe integrare con API di valutazione immobiliare
        return 50

    def assign_priority(self, lead: Lead) -> str:
        """
        Assegna la priorità al lead basandosi sullo score.

        Returns:
            'ALTA', 'MEDIA' o 'BASSA'
        """
        score = lead.lead_score

        if score >= PRIORITY_THRESHOLDS['alta']:
            return 'ALTA'
        elif score >= PRIORITY_THRESHOLDS['media']:
            return 'MEDIA'
        else:
            return 'BASSA'

    def process_leads(self, leads: List[Lead]) -> List[Lead]:
        """
        Processa una lista di lead calcolando score e priorità per ognuno.
        Ordina i lead per score decrescente.

        Args:
            leads: Lista di Lead da processare

        Returns:
            Lista di Lead con score e priorità assegnati, ordinata per score
        """
        for lead in leads:
            lead.lead_score = self.calculate_score(lead)
            lead.priorita = self.assign_priority(lead)

        # Ordina per score decrescente
        leads.sort(key=lambda x: x.lead_score, reverse=True)

        return leads

    def get_statistics(self, leads: List[Lead]) -> dict:
        """
        Calcola statistiche sui lead processati.

        Returns:
            Dizionario con statistiche
        """
        if not leads:
            return {
                'totale': 0,
                'alta_priorita': 0,
                'media_priorita': 0,
                'bassa_priorita': 0,
                'score_medio': 0,
                'score_max': 0,
                'score_min': 0,
                'prezzo_medio': 0
            }

        alta = sum(1 for l in leads if l.priorita == 'ALTA')
        media = sum(1 for l in leads if l.priorita == 'MEDIA')
        bassa = sum(1 for l in leads if l.priorita == 'BASSA')

        scores = [l.lead_score for l in leads]
        prezzi = [l.prezzo_richiesto for l in leads if l.prezzo_richiesto]

        return {
            'totale': len(leads),
            'alta_priorita': alta,
            'media_priorita': media,
            'bassa_priorita': bassa,
            'score_medio': sum(scores) / len(scores) if scores else 0,
            'score_max': max(scores) if scores else 0,
            'score_min': min(scores) if scores else 0,
            'prezzo_medio': sum(prezzi) / len(prezzi) if prezzi else 0
        }
