"""
Scraper per Immobiliare.it
"""

from typing import List, Optional
from datetime import datetime
import re

from .base_scraper import BaseScraper
from models.lead import Lead
from models.search_filters import SearchFilters
from config import PORTAL_URLS


class ImmobiliareScraper(BaseScraper):
    """Scraper specifico per Immobiliare.it"""

    @property
    def nome_portale(self) -> str:
        return "Immobiliare.it"

    @property
    def base_url(self) -> str:
        return PORTAL_URLS['immobiliare']

    def build_search_url(self, filters: SearchFilters, page_num: int = 1) -> str:
        """Costruisce l'URL di ricerca per Immobiliare.it"""
        # Formato: https://www.immobiliare.it/vendita-case/milano/?criterio=rilevanza

        localita_slug = filters.localita.lower().replace(' ', '-')
        base = f"{self.base_url}/vendita-case/{localita_slug}/"

        params = []

        # Solo privati
        params.append("noAgenzie=1")

        # Prezzo
        if filters.prezzo_min:
            params.append(f"prezzoMinimo={filters.prezzo_min}")
        if filters.prezzo_max:
            params.append(f"prezzoMassimo={filters.prezzo_max}")

        # Superficie
        if filters.mq_min:
            params.append(f"superficieMinima={filters.mq_min}")
        if filters.mq_max:
            params.append(f"superficieMassima={filters.mq_max}")

        # Locali
        if filters.locali_min:
            params.append(f"localiMinimo={filters.locali_min}")
        if filters.locali_max:
            params.append(f"localiMassimo={filters.locali_max}")

        # Raggio
        if filters.raggio_km:
            params.append(f"raggio={filters.raggio_km}")

        # Pagina
        if page_num > 1:
            params.append(f"pag={page_num}")

        url = base
        if params:
            url += "?" + "&".join(params)

        return url

    def parse_listing_page(self) -> List[dict]:
        """Parsa la pagina dei risultati di Immobiliare.it"""
        listings = []

        try:
            # Aspetta che i risultati siano caricati
            self.page.wait_for_selector('[class*="listing-item"], [class*="in-realEstateResults"]', timeout=10000)

            # Seleziona tutti gli annunci
            items = self.page.query_selector_all('[class*="listing-item"], li[class*="in-realEstateResults"]')

            for item in items:
                try:
                    listing = {}

                    # URL dell'annuncio
                    link = item.query_selector('a[href*="/annunci/"]')
                    if link:
                        href = link.get_attribute('href')
                        if href:
                            listing['url'] = href if href.startswith('http') else self.base_url + href

                    # Verifica se è un'agenzia
                    agency_el = item.query_selector('[class*="agency"], [class*="agenzia"]')
                    if agency_el:
                        continue  # Salta le agenzie

                    # Prezzo
                    price_el = item.query_selector('[class*="price"], [class*="prezzo"]')
                    if price_el:
                        listing['price'] = self.clean_price(price_el.inner_text())

                    # Località
                    location_el = item.query_selector('[class*="location"], [class*="titolo"]')
                    if location_el:
                        listing['location'] = self.clean_text(location_el.inner_text())

                    if listing.get('url'):
                        listings.append(listing)

                except Exception as e:
                    continue

        except Exception as e:
            self.log_progress(f"Errore parsing lista: {str(e)}")

        return listings

    def parse_listing_detail(self, listing_url: str) -> Optional[Lead]:
        """Parsa la pagina di dettaglio di un annuncio Immobiliare.it"""
        try:
            self.page.goto(listing_url, wait_until='domcontentloaded')
            self.random_delay()

            lead = Lead()
            lead.url_annuncio = listing_url

            # Verifica che non sia un'agenzia
            agency_el = self.page.query_selector('[class*="agency-info"], [class*="real-estate-agency"]')
            if agency_el:
                agency_text = agency_el.inner_text().lower()
                if any(ind in agency_text for ind in ['agenzia', 'immobiliare', 'srl']):
                    return None

            # Nome inserzionista
            advertiser = self.page.query_selector('[class*="advertiser-name"], [class*="inserzionista"]')
            if advertiser:
                nome = self.clean_text(advertiser.inner_text())
                if not self.is_private_seller(nome):
                    return None
                parts = nome.split(' ', 1)
                lead.nome_venditore = parts[0] if parts else nome
                lead.cognome_venditore = parts[1] if len(parts) > 1 else ""

            # Telefono
            phone_el = self.page.query_selector('[class*="phone"], [href^="tel:"]')
            if phone_el:
                if phone_el.get_attribute('href'):
                    lead.telefono = self.clean_phone(phone_el.get_attribute('href').replace('tel:', ''))
                else:
                    lead.telefono = self.clean_phone(phone_el.inner_text())

            # Se non trovato, prova con il bottone mostra telefono
            if not lead.telefono:
                show_phone_btn = self.page.query_selector('[class*="show-phone"], [data-action*="phone"]')
                if show_phone_btn:
                    try:
                        show_phone_btn.click()
                        self.page.wait_for_timeout(1500)
                        phone_el = self.page.query_selector('[class*="phone-number"]')
                        if phone_el:
                            lead.telefono = self.clean_phone(phone_el.inner_text())
                    except:
                        pass

            # Email (se disponibile)
            email_el = self.page.query_selector('[href^="mailto:"]')
            if email_el:
                lead.email = email_el.get_attribute('href').replace('mailto:', '')

            # Prezzo
            price_el = self.page.query_selector('[class*="features__price"], [class*="prezzo"]')
            if price_el:
                lead.prezzo_richiesto = self.clean_price(price_el.inner_text())

            # Località e indirizzo
            location_el = self.page.query_selector('[class*="location"], [class*="indirizzo"]')
            if location_el:
                full_location = self.clean_text(location_el.inner_text())
                # Formato tipico: "Via Roma 1, 20100 Milano (MI)"
                match = re.search(r'(.+?),?\s*(\d{5})?\s*(.+?)\s*\((\w{2})\)', full_location)
                if match:
                    lead.via_indirizzo = match.group(1).strip()
                    lead.cap = match.group(2) or ""
                    lead.comune = match.group(3).strip()
                    lead.provincia = match.group(4).upper()
                else:
                    lead.comune = full_location

            # Caratteristiche
            features = self.page.query_selector_all('[class*="features-list"] li, [class*="caratteristiche"] li')
            for feature in features:
                text = feature.inner_text().lower()
                if 'superficie' in text or 'mq' in text:
                    lead.mq = self.extract_mq(text)
                elif 'local' in text or 'vani' in text:
                    lead.locali = self.extract_locali(text)
                elif 'stato' in text:
                    lead.stato_immobile = self.clean_text(feature.inner_text())

            # Tipo immobile
            type_el = self.page.query_selector('[class*="typology"], [class*="tipologia"]')
            if type_el:
                lead.tipo_immobile = self.clean_text(type_el.inner_text())

            # Descrizione
            desc_el = self.page.query_selector('[class*="description"], [class*="descrizione"]')
            if desc_el:
                lead.descrizione = self.clean_text(desc_el.inner_text())[:500]

            return lead if lead.has_contact_info() else None

        except Exception as e:
            self.log_progress(f"Errore parsing dettaglio: {str(e)}")
            return None

    def has_next_page(self) -> bool:
        """Verifica se c'è una pagina successiva"""
        try:
            next_btn = self.page.query_selector('[class*="pagination"] [class*="next"]:not(.disabled)')
            return next_btn is not None
        except:
            return False
