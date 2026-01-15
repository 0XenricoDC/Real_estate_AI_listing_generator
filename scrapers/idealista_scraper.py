"""
Scraper per Idealista.it
"""

from typing import List, Optional
from datetime import datetime
import re

from .base_scraper import BaseScraper
from models.lead import Lead
from models.search_filters import SearchFilters
from config import PORTAL_URLS


class IdealistaScraper(BaseScraper):
    """Scraper specifico per Idealista.it"""

    @property
    def nome_portale(self) -> str:
        return "Idealista"

    @property
    def base_url(self) -> str:
        return PORTAL_URLS['idealista']

    def build_search_url(self, filters: SearchFilters, page_num: int = 1) -> str:
        """Costruisce l'URL di ricerca per Idealista.it"""
        # Formato: https://www.idealista.it/vendita-case/milano-provincia/

        localita_slug = filters.localita.lower().replace(' ', '-')
        base = f"{self.base_url}/vendita-case/{localita_slug}/"

        params = []

        # Prezzo
        if filters.prezzo_min and filters.prezzo_max:
            params.append(f"prezzoMin={filters.prezzo_min}")
            params.append(f"prezzoMax={filters.prezzo_max}")
        elif filters.prezzo_max:
            params.append(f"prezzoMax={filters.prezzo_max}")
        elif filters.prezzo_min:
            params.append(f"prezzoMin={filters.prezzo_min}")

        # Superficie
        if filters.mq_min:
            params.append(f"dimensioneMin={filters.mq_min}")
        if filters.mq_max:
            params.append(f"dimensioneMax={filters.mq_max}")

        # Solo privati - Idealista usa un filtro specifico
        params.append("noAgencies=true")

        # Pagina
        if page_num > 1:
            base = base.rstrip('/') + f"/pagina-{page_num}.htm"

        url = base
        if params:
            url += "?" + "&".join(params)

        return url

    def parse_listing_page(self) -> List[dict]:
        """Parsa la pagina dei risultati di Idealista"""
        listings = []

        try:
            # Aspetta che i risultati siano caricati
            self.page.wait_for_selector('[class*="item-info"], .item-container', timeout=10000)

            # Seleziona tutti gli annunci
            items = self.page.query_selector_all('.item-container, [class*="item-info"]')

            for item in items:
                try:
                    listing = {}

                    # URL dell'annuncio
                    link = item.query_selector('a.item-link, a[href*="/immobile/"]')
                    if link:
                        href = link.get_attribute('href')
                        if href:
                            listing['url'] = href if href.startswith('http') else self.base_url + href

                    # Verifica se è un'agenzia
                    professional_el = item.query_selector('[class*="professional"], [class*="agency"]')
                    if professional_el:
                        continue

                    # Prezzo
                    price_el = item.query_selector('[class*="price"], .item-price')
                    if price_el:
                        listing['price'] = self.clean_price(price_el.inner_text())

                    # Località
                    location_el = item.query_selector('[class*="location"], .item-detail')
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
        """Parsa la pagina di dettaglio di un annuncio Idealista"""
        try:
            self.page.goto(listing_url, wait_until='domcontentloaded')
            self.random_delay()

            lead = Lead()
            lead.url_annuncio = listing_url

            # Verifica se è un'agenzia
            advertiser_type = self.page.query_selector('[class*="advertiser-type"], [class*="professional-name"]')
            if advertiser_type:
                if 'professionista' in advertiser_type.inner_text().lower() or \
                   'agenzia' in advertiser_type.inner_text().lower():
                    return None

            # Nome inserzionista
            name_el = self.page.query_selector('[class*="advertiser-name"], [class*="contact-name"]')
            if name_el:
                nome = self.clean_text(name_el.inner_text())
                if not self.is_private_seller(nome):
                    return None
                parts = nome.split(' ', 1)
                lead.nome_venditore = parts[0] if parts else nome
                lead.cognome_venditore = parts[1] if len(parts) > 1 else ""

            # Telefono - Idealista spesso nasconde il numero
            phone_btn = self.page.query_selector('[class*="phone-btn"], [data-action*="phone"]')
            if phone_btn:
                try:
                    phone_btn.click()
                    self.page.wait_for_timeout(1500)
                    phone_el = self.page.query_selector('[class*="phone-number"], [href^="tel:"]')
                    if phone_el:
                        href = phone_el.get_attribute('href')
                        if href and 'tel:' in href:
                            lead.telefono = self.clean_phone(href.replace('tel:', ''))
                        else:
                            lead.telefono = self.clean_phone(phone_el.inner_text())
                except:
                    pass

            # Prezzo
            price_el = self.page.query_selector('[class*="info-data-price"], [class*="price"]')
            if price_el:
                lead.prezzo_richiesto = self.clean_price(price_el.inner_text())

            # Località
            location_el = self.page.query_selector('[class*="header-map-list"], [class*="location"]')
            if location_el:
                full_location = self.clean_text(location_el.inner_text())
                # Prova a estrarre i componenti
                parts = full_location.split(',')
                if len(parts) >= 2:
                    lead.via_indirizzo = parts[0].strip()
                    lead.comune = parts[-1].strip()
                else:
                    lead.comune = full_location

            # Caratteristiche dall'header
            features_el = self.page.query_selector('[class*="info-features"]')
            if features_el:
                text = features_el.inner_text().lower()
                lead.mq = self.extract_mq(text)
                lead.locali = self.extract_locali(text)

            # Dettagli aggiuntivi
            details = self.page.query_selector_all('[class*="details-property-feature-one"] li')
            for detail in details:
                text = detail.inner_text().lower()
                if 'superficie' in text:
                    lead.mq = self.extract_mq(text)
                elif 'locali' in text or 'stanze' in text:
                    lead.locali = self.extract_locali(text)
                elif 'stato' in text:
                    lead.stato_immobile = self.clean_text(detail.inner_text())

            # Tipo immobile
            type_el = self.page.query_selector('[class*="main-info__title"]')
            if type_el:
                tipo_text = type_el.inner_text().lower()
                if 'appartamento' in tipo_text:
                    lead.tipo_immobile = 'Appartamento'
                elif 'villa' in tipo_text:
                    lead.tipo_immobile = 'Villa'
                elif 'casa' in tipo_text:
                    lead.tipo_immobile = 'Casa indipendente'
                elif 'attico' in tipo_text:
                    lead.tipo_immobile = 'Attico'

            # Descrizione
            desc_el = self.page.query_selector('[class*="comment"], [class*="description"]')
            if desc_el:
                lead.descrizione = self.clean_text(desc_el.inner_text())[:500]

            return lead if lead.has_contact_info() else None

        except Exception as e:
            self.log_progress(f"Errore parsing dettaglio: {str(e)}")
            return None

    def has_next_page(self) -> bool:
        """Verifica se c'è una pagina successiva"""
        try:
            next_btn = self.page.query_selector('[class*="pagination"] .next:not(.disabled)')
            return next_btn is not None
        except:
            return False
