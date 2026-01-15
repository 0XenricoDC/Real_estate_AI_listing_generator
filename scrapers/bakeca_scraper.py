"""
Scraper per Bakeca.it
"""

from typing import List, Optional
from datetime import datetime
import re

from .base_scraper import BaseScraper
from models.lead import Lead
from models.search_filters import SearchFilters
from config import PORTAL_URLS


class BakecaScraper(BaseScraper):
    """Scraper specifico per Bakeca.it"""

    @property
    def nome_portale(self) -> str:
        return "Bakeca.it"

    @property
    def base_url(self) -> str:
        return PORTAL_URLS['bakeca']

    def build_search_url(self, filters: SearchFilters, page_num: int = 1) -> str:
        """Costruisce l'URL di ricerca per Bakeca.it"""
        # Formato: https://www.bakeca.it/annunci/vendita-case/milano/

        localita_slug = filters.localita.lower().replace(' ', '-')
        base = f"{self.base_url}/annunci/vendita-case/{localita_slug}/"

        params = []

        # Prezzo
        if filters.prezzo_min:
            params.append(f"pr_min={filters.prezzo_min}")
        if filters.prezzo_max:
            params.append(f"pr_max={filters.prezzo_max}")

        # Superficie
        if filters.mq_min:
            params.append(f"mq_min={filters.mq_min}")
        if filters.mq_max:
            params.append(f"mq_max={filters.mq_max}")

        # Solo privati
        params.append("tipo_inserzionista=privato")

        # Pagina
        if page_num > 1:
            params.append(f"pag={page_num}")

        url = base
        if params:
            url += "?" + "&".join(params)

        return url

    def parse_listing_page(self) -> List[dict]:
        """Parsa la pagina dei risultati di Bakeca.it"""
        listings = []

        try:
            # Aspetta che i risultati siano caricati
            self.page.wait_for_selector('[class*="annuncio"], [class*="list-item"]', timeout=10000)

            # Seleziona tutti gli annunci
            items = self.page.query_selector_all('[class*="annuncio"], [class*="list-item"]')

            for item in items:
                try:
                    listing = {}

                    # URL dell'annuncio
                    link = item.query_selector('a[href*="/dettaglio/"], a[href*="/annuncio/"]')
                    if link:
                        href = link.get_attribute('href')
                        if href:
                            listing['url'] = href if href.startswith('http') else self.base_url + href

                    # Verifica se è un'agenzia (cerca badge o indicatori)
                    agency_el = item.query_selector('[class*="agenzia"], [class*="pro"]')
                    if agency_el:
                        continue

                    # Prezzo
                    price_el = item.query_selector('[class*="prezzo"], [class*="price"]')
                    if price_el:
                        listing['price'] = self.clean_price(price_el.inner_text())

                    # Località
                    location_el = item.query_selector('[class*="localita"], [class*="location"]')
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
        """Parsa la pagina di dettaglio di un annuncio Bakeca.it"""
        try:
            self.page.goto(listing_url, wait_until='domcontentloaded')
            self.random_delay()

            lead = Lead()
            lead.url_annuncio = listing_url

            # Verifica se è un privato
            seller_type = self.page.query_selector('[class*="tipo-venditore"], [class*="seller-type"]')
            if seller_type:
                if 'professionista' in seller_type.inner_text().lower() or \
                   'agenzia' in seller_type.inner_text().lower():
                    return None

            # Nome inserzionista
            name_el = self.page.query_selector('[class*="nome-inserzionista"], [class*="seller-name"]')
            if name_el:
                nome = self.clean_text(name_el.inner_text())
                if not self.is_private_seller(nome):
                    return None
                parts = nome.split(' ', 1)
                lead.nome_venditore = parts[0] if parts else nome
                lead.cognome_venditore = parts[1] if len(parts) > 1 else ""

            # Telefono - Bakeca spesso mostra il telefono direttamente
            phone_el = self.page.query_selector('[href^="tel:"], [class*="telefono"]')
            if phone_el:
                href = phone_el.get_attribute('href')
                if href and 'tel:' in href:
                    lead.telefono = self.clean_phone(href.replace('tel:', ''))
                else:
                    lead.telefono = self.clean_phone(phone_el.inner_text())

            # Cerca nel testo della pagina
            if not lead.telefono:
                page_content = self.page.content()
                # Pattern per numeri italiani
                phone_patterns = [
                    r'(?:tel|telefono|cell|mobile)[.:\s]*(\+?39)?[\s.-]?(\d{2,4})[\s.-]?(\d{6,7})',
                    r'(\+39|0039)?[\s.-]?(3\d{2})[\s.-]?(\d{6,7})',
                    r'(\d{3})[\s.-](\d{3})[\s.-](\d{4})'
                ]
                for pattern in phone_patterns:
                    match = re.search(pattern, page_content, re.I)
                    if match:
                        lead.telefono = self.clean_phone(''.join(filter(None, match.groups())))
                        break

            # Email
            email_el = self.page.query_selector('[href^="mailto:"]')
            if email_el:
                lead.email = email_el.get_attribute('href').replace('mailto:', '')

            # Prezzo
            price_el = self.page.query_selector('[class*="prezzo"], [class*="price-detail"]')
            if price_el:
                lead.prezzo_richiesto = self.clean_price(price_el.inner_text())

            # Località
            location_el = self.page.query_selector('[class*="localita"], [class*="location-detail"]')
            if location_el:
                full_location = self.clean_text(location_el.inner_text())
                # Formato tipico: "Milano (MI)" o "Via Roma 1, Milano"
                match = re.search(r'(.+?)\s*\((\w{2})\)', full_location)
                if match:
                    lead.comune = match.group(1).strip()
                    lead.provincia = match.group(2).upper()
                else:
                    parts = full_location.split(',')
                    if len(parts) > 1:
                        lead.via_indirizzo = parts[0].strip()
                        lead.comune = parts[-1].strip()
                    else:
                        lead.comune = full_location

            # Caratteristiche
            features = self.page.query_selector_all('[class*="caratteristiche"] li, [class*="details"] dt, dd')
            for i, feature in enumerate(features):
                text = feature.inner_text().lower()
                if 'superficie' in text or 'mq' in text:
                    # Il valore potrebbe essere nel prossimo elemento
                    if i + 1 < len(features):
                        lead.mq = self.extract_mq(features[i + 1].inner_text())
                    else:
                        lead.mq = self.extract_mq(text)
                elif 'locali' in text or 'vani' in text:
                    if i + 1 < len(features):
                        lead.locali = self.extract_locali(features[i + 1].inner_text())
                    else:
                        lead.locali = self.extract_locali(text)
                elif 'stato' in text:
                    if i + 1 < len(features):
                        lead.stato_immobile = self.clean_text(features[i + 1].inner_text())

            # Tipo immobile dal titolo
            title_el = self.page.query_selector('h1, [class*="titolo"]')
            if title_el:
                title = title_el.inner_text().lower()
                if 'appartamento' in title:
                    lead.tipo_immobile = 'Appartamento'
                elif 'villa' in title:
                    lead.tipo_immobile = 'Villa'
                elif 'casa' in title:
                    lead.tipo_immobile = 'Casa indipendente'
                elif 'attico' in title:
                    lead.tipo_immobile = 'Attico'
                elif 'terreno' in title:
                    lead.tipo_immobile = 'Terreno'

            # Descrizione
            desc_el = self.page.query_selector('[class*="descrizione"], [class*="description"]')
            if desc_el:
                lead.descrizione = self.clean_text(desc_el.inner_text())[:500]

            return lead if lead.has_contact_info() else None

        except Exception as e:
            self.log_progress(f"Errore parsing dettaglio: {str(e)}")
            return None

    def has_next_page(self) -> bool:
        """Verifica se c'è una pagina successiva"""
        try:
            next_btn = self.page.query_selector('[class*="pagination"] .next:not(.disabled), a[rel="next"]')
            return next_btn is not None
        except:
            return False
