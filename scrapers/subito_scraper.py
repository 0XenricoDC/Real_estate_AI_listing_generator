"""
Scraper per Subito.it
"""

from typing import List, Optional
from datetime import datetime
import re

from .base_scraper import BaseScraper
from models.lead import Lead
from models.search_filters import SearchFilters
from config import PORTAL_URLS


class SubitoScraper(BaseScraper):
    """Scraper specifico per Subito.it"""

    @property
    def nome_portale(self) -> str:
        return "Subito.it"

    @property
    def base_url(self) -> str:
        return PORTAL_URLS['subito']

    def build_search_url(self, filters: SearchFilters, page_num: int = 1) -> str:
        """Costruisce l'URL di ricerca per Subito.it"""
        # URL base per vendita immobili
        # Formato: https://www.subito.it/annunci-italia/vendita/immobili/?q=milano

        base = f"{self.base_url}/annunci-italia/vendita/immobili/"

        params = []

        # Località
        if filters.localita:
            params.append(f"q={filters.localita.replace(' ', '+')}")

        # Solo privati
        params.append("advt=s")  # s = privati, c = aziende

        # Prezzo
        if filters.prezzo_min:
            params.append(f"ps={filters.prezzo_min}")
        if filters.prezzo_max:
            params.append(f"pe={filters.prezzo_max}")

        # Pagina
        if page_num > 1:
            params.append(f"o={page_num}")

        # Raggio (Subito usa un sistema diverso, ma possiamo aggiungere distanza)
        if filters.raggio_km:
            params.append(f"r={filters.raggio_km}")

        url = base
        if params:
            url += "?" + "&".join(params)

        return url

    def parse_listing_page(self) -> List[dict]:
        """Parsa la pagina dei risultati di Subito.it"""
        listings = []

        try:
            # Aspetta che i risultati siano caricati
            self.page.wait_for_selector('[class*="items__item"]', timeout=10000)

            # Seleziona tutti gli annunci
            items = self.page.query_selector_all('[class*="items__item"]')

            for item in items:
                try:
                    listing = {}

                    # URL dell'annuncio
                    link = item.query_selector('a[href*="/annunci/"]')
                    if link:
                        href = link.get_attribute('href')
                        if href:
                            listing['url'] = href if href.startswith('http') else self.base_url + href

                    # Titolo
                    title_el = item.query_selector('[class*="item-title"]')
                    if title_el:
                        listing['title'] = self.clean_text(title_el.inner_text())

                    # Prezzo
                    price_el = item.query_selector('[class*="price"]')
                    if price_el:
                        listing['price'] = self.clean_price(price_el.inner_text())

                    # Località
                    location_el = item.query_selector('[class*="town"]')
                    if location_el:
                        listing['location'] = self.clean_text(location_el.inner_text())

                    # Verifica se è un privato (badge agenzia)
                    agency_badge = item.query_selector('[class*="company"]')
                    if agency_badge:
                        continue  # Salta se è un'agenzia

                    if listing.get('url'):
                        listings.append(listing)

                except Exception as e:
                    continue

        except Exception as e:
            self.log_progress(f"Errore parsing lista: {str(e)}")

        return listings

    def parse_listing_detail(self, listing_url: str) -> Optional[Lead]:
        """Parsa la pagina di dettaglio di un annuncio Subito.it"""
        try:
            self.page.goto(listing_url, wait_until='domcontentloaded')
            self.random_delay()

            lead = Lead()
            lead.url_annuncio = listing_url

            # Verifica che sia un privato
            seller_type = self.page.query_selector('[class*="advertiser-info"] [class*="type"]')
            if seller_type:
                if 'agenzia' in seller_type.inner_text().lower():
                    return None

            # Nome venditore
            seller_name = self.page.query_selector('[class*="advertiser-info"] [class*="name"]')
            if seller_name:
                nome = self.clean_text(seller_name.inner_text())
                parts = nome.split(' ', 1)
                lead.nome_venditore = parts[0] if parts else nome
                lead.cognome_venditore = parts[1] if len(parts) > 1 else ""

            # Telefono - potrebbe richiedere click su un bottone
            phone_btn = self.page.query_selector('[class*="phone-button"], [data-testid*="phone"]')
            if phone_btn:
                try:
                    phone_btn.click()
                    self.page.wait_for_timeout(1000)
                    phone_el = self.page.query_selector('[class*="phone-number"], [href^="tel:"]')
                    if phone_el:
                        lead.telefono = self.clean_phone(phone_el.inner_text())
                except:
                    pass

            # Se non troviamo il telefono con il bottone, cerca nel testo
            if not lead.telefono:
                # Cerca pattern telefonico nella pagina
                page_text = self.page.content()
                phone_match = re.search(r'(?:tel|telefono|cell)[:\s]*([+\d\s\-]{8,})', page_text, re.I)
                if phone_match:
                    lead.telefono = self.clean_phone(phone_match.group(1))

            # Prezzo
            price_el = self.page.query_selector('[class*="price"]')
            if price_el:
                lead.prezzo_richiesto = self.clean_price(price_el.inner_text())

            # Località
            location_el = self.page.query_selector('[class*="location"]')
            if location_el:
                location_text = self.clean_text(location_el.inner_text())
                # Prova a estrarre comune e provincia
                match = re.search(r'(.+?)\s*\((\w{2})\)', location_text)
                if match:
                    lead.comune = match.group(1).strip()
                    lead.provincia = match.group(2).upper()
                else:
                    lead.comune = location_text

            # Indirizzo (se disponibile)
            address_el = self.page.query_selector('[class*="address"]')
            if address_el:
                lead.via_indirizzo = self.clean_text(address_el.inner_text())

            # Caratteristiche immobile
            features = self.page.query_selector_all('[class*="feature"]')
            for feature in features:
                text = feature.inner_text().lower()
                if 'mq' in text or 'm²' in text:
                    lead.mq = self.extract_mq(text)
                elif 'local' in text or 'vani' in text:
                    lead.locali = self.extract_locali(text)

            # Tipo immobile
            category_el = self.page.query_selector('[class*="category"]')
            if category_el:
                lead.tipo_immobile = self.clean_text(category_el.inner_text())

            # Descrizione
            desc_el = self.page.query_selector('[class*="description"]')
            if desc_el:
                lead.descrizione = self.clean_text(desc_el.inner_text())[:500]  # Limita a 500 char

            # Data pubblicazione
            date_el = self.page.query_selector('[class*="date"]')
            if date_el:
                date_text = date_el.inner_text()
                # Prova a parsare la data
                try:
                    if 'oggi' in date_text.lower():
                        lead.data_pubblicazione = datetime.now()
                    elif 'ieri' in date_text.lower():
                        from datetime import timedelta
                        lead.data_pubblicazione = datetime.now() - timedelta(days=1)
                    else:
                        # Prova formato GG/MM/AAAA o simili
                        match = re.search(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})', date_text)
                        if match:
                            day, month, year = match.groups()
                            if len(year) == 2:
                                year = '20' + year
                            lead.data_pubblicazione = datetime(int(year), int(month), int(day))
                except:
                    pass

            return lead if lead.has_contact_info() else None

        except Exception as e:
            self.log_progress(f"Errore parsing dettaglio: {str(e)}")
            return None

    def has_next_page(self) -> bool:
        """Verifica se c'è una pagina successiva"""
        try:
            next_btn = self.page.query_selector('[class*="pagination"] [class*="next"]:not([disabled])')
            return next_btn is not None
        except:
            return False
