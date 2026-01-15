"""
Scraper per Casa.it
"""

from typing import List, Optional
from datetime import datetime
import re

from .base_scraper import BaseScraper
from models.lead import Lead
from models.search_filters import SearchFilters
from config import PORTAL_URLS


class CasaScraper(BaseScraper):
    """Scraper specifico per Casa.it"""

    @property
    def nome_portale(self) -> str:
        return "Casa.it"

    @property
    def base_url(self) -> str:
        return PORTAL_URLS['casa']

    def build_search_url(self, filters: SearchFilters, page_num: int = 1) -> str:
        """Costruisce l'URL di ricerca per Casa.it"""
        # Formato: https://www.casa.it/vendita/residenziale/milano/

        localita_slug = filters.localita.lower().replace(' ', '-')
        base = f"{self.base_url}/vendita/residenziale/{localita_slug}/"

        params = []

        # Prezzo
        if filters.prezzo_min:
            params.append(f"prezzoMinimo={filters.prezzo_min}")
        if filters.prezzo_max:
            params.append(f"prezzoMassimo={filters.prezzo_max}")

        # Superficie
        if filters.mq_min:
            params.append(f"mqMinimi={filters.mq_min}")
        if filters.mq_max:
            params.append(f"mqMassimi={filters.mq_max}")

        # Locali
        if filters.locali_min:
            params.append(f"localiMinimi={filters.locali_min}")

        # Solo privati
        params.append("tipoInserzionista=privato")

        # Pagina
        if page_num > 1:
            params.append(f"page={page_num}")

        url = base
        if params:
            url += "?" + "&".join(params)

        return url

    def parse_listing_page(self) -> List[dict]:
        """Parsa la pagina dei risultati di Casa.it"""
        listings = []

        try:
            # Aspetta che i risultati siano caricati
            self.page.wait_for_selector('[class*="listing-card"], [class*="annuncio"]', timeout=10000)

            # Seleziona tutti gli annunci
            items = self.page.query_selector_all('[class*="listing-card"], [class*="annuncio"]')

            for item in items:
                try:
                    listing = {}

                    # URL dell'annuncio
                    link = item.query_selector('a[href*="/dettaglio/"], a[href*="/annuncio/"]')
                    if link:
                        href = link.get_attribute('href')
                        if href:
                            listing['url'] = href if href.startswith('http') else self.base_url + href

                    # Verifica se è un'agenzia
                    agency_badge = item.query_selector('[class*="agency"], [class*="agenzia"]')
                    if agency_badge:
                        continue

                    # Prezzo
                    price_el = item.query_selector('[class*="price"], [class*="prezzo"]')
                    if price_el:
                        listing['price'] = self.clean_price(price_el.inner_text())

                    # Località
                    location_el = item.query_selector('[class*="address"], [class*="località"]')
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
        """Parsa la pagina di dettaglio di un annuncio Casa.it"""
        try:
            self.page.goto(listing_url, wait_until='domcontentloaded')
            self.random_delay()

            lead = Lead()
            lead.url_annuncio = listing_url

            # Verifica se è un privato
            seller_type = self.page.query_selector('[class*="advertiser-type"], [class*="tipo-inserzionista"]')
            if seller_type:
                if 'agenzia' in seller_type.inner_text().lower():
                    return None

            # Nome inserzionista
            name_el = self.page.query_selector('[class*="advertiser-name"], [class*="nome-inserzionista"]')
            if name_el:
                nome = self.clean_text(name_el.inner_text())
                if not self.is_private_seller(nome):
                    return None
                parts = nome.split(' ', 1)
                lead.nome_venditore = parts[0] if parts else nome
                lead.cognome_venditore = parts[1] if len(parts) > 1 else ""

            # Telefono
            phone_el = self.page.query_selector('[href^="tel:"], [class*="phone"]')
            if phone_el:
                href = phone_el.get_attribute('href')
                if href and 'tel:' in href:
                    lead.telefono = self.clean_phone(href.replace('tel:', ''))
                else:
                    lead.telefono = self.clean_phone(phone_el.inner_text())

            # Prova con bottone mostra telefono
            if not lead.telefono:
                show_btn = self.page.query_selector('[class*="show-phone"], button[class*="telefono"]')
                if show_btn:
                    try:
                        show_btn.click()
                        self.page.wait_for_timeout(1500)
                        phone_el = self.page.query_selector('[class*="phone-revealed"], [class*="telefono-visibile"]')
                        if phone_el:
                            lead.telefono = self.clean_phone(phone_el.inner_text())
                    except:
                        pass

            # Prezzo
            price_el = self.page.query_selector('[class*="detail-price"], [class*="prezzo-dettaglio"]')
            if price_el:
                lead.prezzo_richiesto = self.clean_price(price_el.inner_text())

            # Indirizzo
            address_el = self.page.query_selector('[class*="address"], [class*="indirizzo"]')
            if address_el:
                full_address = self.clean_text(address_el.inner_text())
                # Prova a parsare
                match = re.search(r'(.+?),?\s*(\d{5})?\s*(.+?)\s*\((\w{2})\)', full_address)
                if match:
                    lead.via_indirizzo = match.group(1).strip()
                    lead.cap = match.group(2) or ""
                    lead.comune = match.group(3).strip()
                    lead.provincia = match.group(4).upper()
                else:
                    lead.comune = full_address

            # Caratteristiche
            features_container = self.page.query_selector('[class*="features"], [class*="caratteristiche"]')
            if features_container:
                features = features_container.query_selector_all('li, [class*="feature-item"]')
                for feature in features:
                    text = feature.inner_text().lower()
                    if 'mq' in text or 'superficie' in text:
                        lead.mq = self.extract_mq(text)
                    elif 'local' in text or 'vani' in text:
                        lead.locali = self.extract_locali(text)
                    elif 'stato' in text:
                        lead.stato_immobile = self.clean_text(feature.inner_text())

            # Tipo immobile
            type_el = self.page.query_selector('[class*="property-type"], [class*="tipologia"]')
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
            next_btn = self.page.query_selector('[class*="pagination"] .next:not(.disabled), [aria-label="Prossima"]')
            return next_btn is not None
        except:
            return False
