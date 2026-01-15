"""
Client API per Immobiliare.it (Realitycs API)

Documentazione: https://www.immobiliare.it/insights/en/api/
Feed API Swagger: https://feed.immobiliare.it/ws/import/docs/swagger-ui.html

Per ottenere le credenziali:
1. Vai su https://www.immobiliare.it/insights/en/api/
2. Contatta il team commerciale per richiedere accesso
3. Riceverai API_KEY via email dopo approvazione

NOTA: L'API Realitycs di Immobiliare.it è orientata principalmente all'analisi
di mercato e dati aggregati. Per cercare singoli annunci, potrebbe essere
necessario utilizzare un'API diversa o combinare con lo scraper.
"""

import requests
from typing import List, Optional
from datetime import datetime

from data_sources.base import BaseDataSource
from models.lead import Lead
from models.search_filters import SearchFilters
from config import (
    IMMOBILIARE_API_KEY,
    IMMOBILIARE_API_URL,
    AGENCY_INDICATORS
)


class ImmobiliareAPI(BaseDataSource):
    """Client per l'API ufficiale di Immobiliare.it"""

    # URL base dell'API (da confermare dopo registrazione)
    DEFAULT_API_URL = "https://api.immobiliare.it/v1/"

    # Mapping tipi immobile italiano -> API
    PROPERTY_TYPE_MAP = {
        'Tutti': 'residenziale',
        'Appartamento': 'appartamento',
        'Villa': 'villa',
        'Casa indipendente': 'casa-indipendente',
        'Villetta a schiera': 'villetta-a-schiera',
        'Attico': 'attico-mansarda',
        'Loft': 'loft',
        'Mansarda': 'attico-mansarda',
        'Box/Garage': 'box-garage',
        'Posto auto': 'posto-auto',
        'Negozio': 'negozio',
        'Ufficio': 'ufficio',
        'Capannone': 'capannone',
        'Magazzino': 'magazzino',
        'Terreno': 'terreno',
        'Terreno edificabile': 'terreno-edificabile'
    }

    def __init__(self):
        super().__init__()
        self._api_url = IMMOBILIARE_API_URL or self.DEFAULT_API_URL

    @property
    def nome_portale(self) -> str:
        return "Immobiliare.it"

    @property
    def source_type(self) -> str:
        return "api"

    def is_available(self) -> bool:
        """Verifica se le credenziali API sono configurate"""
        return bool(IMMOBILIARE_API_KEY)

    def _get_headers(self) -> dict:
        """Ritorna gli headers per le richieste API"""
        return {
            "Authorization": f"Bearer {IMMOBILIARE_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _build_search_params(self, filters: SearchFilters) -> dict:
        """Costruisce i parametri di ricerca per l'API"""
        params = {
            "contratto": "vendita",
            "tipologia": self.PROPERTY_TYPE_MAP.get(filters.tipo_immobile, "residenziale"),
            "limit": min(100, filters.max_risultati_per_sito),
            "offset": 0,
            # Filtra solo privati
            "tipologiaInserzionista": "privato"
        }

        # Località
        if filters.localita:
            params["localita"] = filters.localita

        # Raggio di ricerca
        if filters.raggio_km:
            params["raggio"] = filters.raggio_km

        # Filtri prezzo
        if filters.prezzo_min:
            params["prezzoMinimo"] = filters.prezzo_min
        if filters.prezzo_max:
            params["prezzoMassimo"] = filters.prezzo_max

        # Filtri dimensioni
        if filters.mq_min:
            params["superficieMinima"] = filters.mq_min
        if filters.mq_max:
            params["superficieMassima"] = filters.mq_max

        # Filtri locali
        if filters.locali_min:
            params["localiMinimi"] = filters.locali_min
        if filters.locali_max:
            params["localiMassimi"] = filters.locali_max

        # Stato immobile
        if filters.stato_immobile and filters.stato_immobile != "Tutti":
            stato_map = {
                "Nuovo": "nuovo",
                "Ottimo stato": "ottimo",
                "Buono stato": "buono",
                "Da ristrutturare": "da-ristrutturare",
                "In costruzione": "in-costruzione"
            }
            params["stato"] = stato_map.get(filters.stato_immobile, "")

        return params

    def _is_private_seller(self, listing: dict) -> bool:
        """Verifica se l'annuncio è di un privato"""
        # Controlla il tipo di inserzionista
        advertiser_type = listing.get("tipoInserzionista", "")
        if advertiser_type.lower() == "agenzia":
            return False

        # Controlla il nome per indicatori di agenzia
        advertiser = listing.get("inserzionista", {})
        name = advertiser.get("nome", "")
        for indicator in AGENCY_INDICATORS:
            if indicator.lower() in name.lower():
                return False

        return True

    def _parse_listing(self, listing: dict) -> Optional[Lead]:
        """Converte un listing API in un Lead"""
        try:
            # Estrai dati inserzionista
            advertiser = listing.get("inserzionista", {})
            contact = listing.get("contatti", {})

            # Estrai nome (dividi se possibile)
            full_name = advertiser.get("nome", "")
            name_parts = full_name.split(" ", 1)
            nome = name_parts[0] if name_parts else ""
            cognome = name_parts[1] if len(name_parts) > 1 else ""

            # Estrai contatti
            phone = contact.get("telefono", "")
            email = contact.get("email", "")

            # Estrai indirizzo
            location = listing.get("localizzazione", {})
            address = location.get("indirizzo", "")
            municipality = location.get("comune", "")
            province = location.get("provincia", "")
            postal_code = location.get("cap", "")

            # Estrai caratteristiche
            features = listing.get("caratteristiche", {})
            price = listing.get("prezzo", 0)
            size = features.get("superficie", 0)
            rooms = features.get("locali", 0)

            # Stato immobile
            stato = features.get("stato", "")

            # Data pubblicazione
            pub_date = None
            if listing.get("dataPubblicazione"):
                try:
                    pub_date = datetime.fromisoformat(listing["dataPubblicazione"])
                except:
                    pass

            # Tipo immobile
            tipo = listing.get("tipologia", "")

            lead = Lead(
                nome_venditore=nome,
                cognome_venditore=cognome,
                telefono=phone,
                email=email,
                via_indirizzo=address,
                comune=municipality,
                provincia=province,
                cap=postal_code,
                prezzo_richiesto=int(price) if price else 0,
                tipo_immobile=tipo,
                mq=int(size) if size else 0,
                locali=int(rooms) if rooms else 0,
                stato_immobile=stato,
                descrizione=listing.get("descrizione", "")[:500],
                url_annuncio=listing.get("url", ""),
                data_pubblicazione=pub_date,
                fonte="Immobiliare.it"
            )

            return lead

        except Exception as e:
            self.log_progress(f"Errore parsing listing: {str(e)}")
            return None

    def search(self, filters: SearchFilters) -> List[Lead]:
        """
        Esegue la ricerca su Immobiliare.it via API.

        NOTA: La struttura esatta dell'API potrebbe variare.
        Questo codice è basato su documentazione pubblica e potrebbe
        richiedere modifiche dopo aver ottenuto accesso all'API.
        """
        leads = []

        if not self.is_available():
            self.log_progress("API non disponibile - credenziali mancanti")
            return leads

        try:
            self.log_progress("Avvio ricerca via API...")

            headers = self._get_headers()
            params = self._build_search_params(filters)
            max_results = filters.max_risultati_per_sito
            offset = 0

            while len(leads) < max_results:
                params["offset"] = offset

                self.log_progress(f"Richiesta con offset {offset}...")

                response = requests.get(
                    f"{self._api_url}annunci/ricerca",
                    headers=headers,
                    params=params,
                    timeout=30
                )

                if response.status_code == 401:
                    self.log_progress("Errore autenticazione - verifica API key")
                    break
                elif response.status_code != 200:
                    self.log_progress(f"Errore API: {response.status_code}")
                    # Prova endpoint alternativo
                    response = requests.get(
                        f"{self._api_url}search",
                        headers=headers,
                        params=params,
                        timeout=30
                    )
                    if response.status_code != 200:
                        break

                data = response.json()

                # L'API potrebbe restituire i risultati in diversi formati
                elements = (
                    data.get("results", []) or
                    data.get("annunci", []) or
                    data.get("items", []) or
                    data.get("data", [])
                )

                total = data.get("total", 0) or data.get("totalCount", 0)

                if offset == 0:
                    self.log_progress(f"Trovati {total} annunci totali")

                if not elements:
                    break

                for listing in elements:
                    # Filtra solo privati
                    if not self._is_private_seller(listing):
                        continue

                    lead = self._parse_listing(listing)
                    if lead and lead.has_contact_info():
                        leads.append(lead)
                        self.log_progress(f"Lead trovato: {lead.comune}")

                    if len(leads) >= max_results:
                        break

                # Verifica se ci sono altri risultati
                if len(elements) < params.get("limit", 100):
                    break

                offset += len(elements)

        except requests.exceptions.RequestException as e:
            self.log_progress(f"Errore di rete: {str(e)}")
        except Exception as e:
            self.log_progress(f"Errore ricerca: {str(e)}")

        self.log_progress(f"Ricerca completata: {len(leads)} lead trovati")
        return leads

    def test_connection(self) -> bool:
        """
        Testa la connessione all'API.
        Utile per verificare che le credenziali siano corrette.
        """
        if not self.is_available():
            return False

        try:
            response = requests.get(
                f"{self._api_url}status",
                headers=self._get_headers(),
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
