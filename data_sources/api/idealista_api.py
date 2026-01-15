"""
Client API per Idealista.it

Documentazione: https://developers.idealista.com/access-request
Base URL: https://api.idealista.com/3.5/

Per ottenere le credenziali:
1. Vai su https://developers.idealista.com/access-request
2. Compila il form con i dettagli del tuo progetto
3. Attendi approvazione (di solito 1-3 giorni lavorativi)
4. Riceverai API_KEY e API_SECRET via email
"""

import requests
import base64
from typing import List, Optional
from datetime import datetime

from data_sources.base import BaseDataSource
from models.lead import Lead
from models.search_filters import SearchFilters
from config import (
    IDEALISTA_API_KEY,
    IDEALISTA_API_SECRET,
    AGENCY_INDICATORS
)


class IdealistaAPI(BaseDataSource):
    """Client per l'API ufficiale di Idealista"""

    BASE_URL = "https://api.idealista.com/3.5/"
    TOKEN_URL = "https://api.idealista.com/oauth/token"

    # Mapping tipi immobile italiano -> API
    PROPERTY_TYPE_MAP = {
        'Tutti': 'homes',
        'Appartamento': 'homes',
        'Villa': 'homes',
        'Casa indipendente': 'homes',
        'Villetta a schiera': 'homes',
        'Attico': 'homes',
        'Loft': 'homes',
        'Mansarda': 'homes',
        'Box/Garage': 'garages',
        'Posto auto': 'garages',
        'Negozio': 'premises',
        'Ufficio': 'offices',
        'Capannone': 'premises',
        'Magazzino': 'premises',
        'Terreno': 'homes',
        'Terreno edificabile': 'homes'
    }

    def __init__(self):
        super().__init__()
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    @property
    def nome_portale(self) -> str:
        return "Idealista"

    @property
    def source_type(self) -> str:
        return "api"

    def is_available(self) -> bool:
        """Verifica se le credenziali API sono configurate"""
        return bool(IDEALISTA_API_KEY and IDEALISTA_API_SECRET)

    def _get_access_token(self) -> Optional[str]:
        """
        Ottiene un access token OAuth2.
        Il token viene cachato fino alla scadenza.
        """
        # Se abbiamo un token valido, riusalo
        if self._access_token and self._token_expires:
            if datetime.now() < self._token_expires:
                return self._access_token

        if not self.is_available():
            self.log_progress("Credenziali API non configurate")
            return None

        try:
            # Crea le credenziali base64
            credentials = f"{IDEALISTA_API_KEY}:{IDEALISTA_API_SECRET}"
            encoded = base64.b64encode(credentials.encode()).decode()

            headers = {
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/x-www-form-urlencoded"
            }

            response = requests.post(
                self.TOKEN_URL,
                headers=headers,
                data={"grant_type": "client_credentials"},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                self._access_token = data.get("access_token")
                # Il token scade dopo 3600 secondi (1 ora), impostiamo scadenza a 50 minuti
                from datetime import timedelta
                self._token_expires = datetime.now() + timedelta(minutes=50)
                self.log_progress("Token OAuth ottenuto con successo")
                return self._access_token
            else:
                self.log_progress(f"Errore autenticazione: {response.status_code}")
                return None

        except Exception as e:
            self.log_progress(f"Errore ottenimento token: {str(e)}")
            return None

    def _build_search_params(self, filters: SearchFilters) -> dict:
        """Costruisce i parametri di ricerca per l'API"""
        params = {
            "country": "it",
            "language": "it",
            "operation": "sale",
            "propertyType": self.PROPERTY_TYPE_MAP.get(filters.tipo_immobile, "homes"),
            "maxItems": min(50, filters.max_risultati_per_sito),  # API limite max 50
            "numPage": 1,
            # Filtra solo privati
            "showAllAgents": "false"
        }

        # Località - L'API usa coordinate o locationId
        # Per semplicità, usiamo il nome della località come center
        if filters.localita:
            # L'API preferisce coordinate, ma accetta anche locationName
            params["locationName"] = filters.localita

        # Raggio di ricerca
        if filters.raggio_km:
            params["distance"] = filters.raggio_km * 1000  # Converti km in metri

        # Filtri prezzo
        if filters.prezzo_min:
            params["minPrice"] = filters.prezzo_min
        if filters.prezzo_max:
            params["maxPrice"] = filters.prezzo_max

        # Filtri dimensioni
        if filters.mq_min:
            params["minSize"] = filters.mq_min
        if filters.mq_max:
            params["maxSize"] = filters.mq_max

        # Filtri locali (bedrooms nell'API)
        if filters.locali_min:
            params["bedrooms"] = f"{filters.locali_min},"
        if filters.locali_max:
            if "bedrooms" in params:
                params["bedrooms"] = f"{filters.locali_min},{filters.locali_max}"
            else:
                params["bedrooms"] = f"0,{filters.locali_max}"

        return params

    def _is_private_seller(self, listing: dict) -> bool:
        """Verifica se l'annuncio è di un privato"""
        # Controlla il campo 'advertiser' o 'isAgency'
        if listing.get("isAgency", False):
            return False

        advertiser = listing.get("advertiser", {})
        if advertiser.get("type", "").lower() == "agency":
            return False

        # Controlla il nome per indicatori di agenzia
        name = advertiser.get("name", "")
        for indicator in AGENCY_INDICATORS:
            if indicator.lower() in name.lower():
                return False

        return True

    def _parse_listing(self, listing: dict) -> Optional[Lead]:
        """Converte un listing API in un Lead"""
        try:
            # Estrai dati venditore
            advertiser = listing.get("advertiser", {})
            contact = listing.get("contactInfo", {})

            # Estrai nome venditore (dividi se possibile)
            full_name = advertiser.get("name", "")
            name_parts = full_name.split(" ", 1)
            nome = name_parts[0] if name_parts else ""
            cognome = name_parts[1] if len(name_parts) > 1 else ""

            # Estrai contatti
            phone = contact.get("phone", "") or listing.get("phone", "")
            email = contact.get("email", "")

            # Estrai indirizzo
            address = listing.get("address", "")
            municipality = listing.get("municipality", "")
            province = listing.get("province", "")
            postal_code = listing.get("postalCode", "")

            # Estrai caratteristiche immobile
            price = listing.get("price", 0)
            size = listing.get("size", 0)
            rooms = listing.get("rooms", 0)

            # Stato immobile
            status_map = {
                "newdevelopment": "Nuovo",
                "good": "Buono stato",
                "renew": "Da ristrutturare"
            }
            status = listing.get("status", "")
            stato = status_map.get(status, status)

            # Data pubblicazione
            pub_date = None
            if listing.get("publishDate"):
                try:
                    pub_date = datetime.fromisoformat(
                        listing["publishDate"].replace("Z", "+00:00")
                    )
                except:
                    pass

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
                tipo_immobile=listing.get("propertyType", ""),
                mq=int(size) if size else 0,
                locali=int(rooms) if rooms else 0,
                stato_immobile=stato,
                descrizione=listing.get("description", "")[:500],  # Limita descrizione
                url_annuncio=listing.get("url", ""),
                data_pubblicazione=pub_date,
                fonte="Idealista"
            )

            return lead

        except Exception as e:
            self.log_progress(f"Errore parsing listing: {str(e)}")
            return None

    def search(self, filters: SearchFilters) -> List[Lead]:
        """
        Esegue la ricerca su Idealista via API.
        """
        leads = []

        if not self.is_available():
            self.log_progress("API non disponibile - credenziali mancanti")
            return leads

        token = self._get_access_token()
        if not token:
            self.log_progress("Impossibile ottenere token di accesso")
            return leads

        try:
            self.log_progress("Avvio ricerca via API...")

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/x-www-form-urlencoded"
            }

            params = self._build_search_params(filters)
            total_found = 0
            page = 1
            max_results = filters.max_risultati_per_sito

            while len(leads) < max_results:
                params["numPage"] = page

                self.log_progress(f"Richiesta pagina {page}...")

                response = requests.post(
                    f"{self.BASE_URL}it/search",
                    headers=headers,
                    data=params,
                    timeout=30
                )

                if response.status_code != 200:
                    self.log_progress(f"Errore API: {response.status_code}")
                    break

                data = response.json()
                elements = data.get("elementList", [])
                total = data.get("total", 0)

                if page == 1:
                    self.log_progress(f"Trovati {total} annunci totali")
                    total_found = total

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

                # Verifica se ci sono altre pagine
                total_pages = data.get("totalPages", 1)
                if page >= total_pages:
                    break

                page += 1

        except Exception as e:
            self.log_progress(f"Errore ricerca: {str(e)}")

        self.log_progress(f"Ricerca completata: {len(leads)} lead trovati")
        return leads
