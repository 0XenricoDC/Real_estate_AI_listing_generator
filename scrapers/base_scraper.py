"""
Classe base astratta per gli scrapers dei portali immobiliari
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Callable, Dict
import random
import time
import re
import json
import os

from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext

from models.lead import Lead
from models.search_filters import SearchFilters
from config import (
    USER_AGENTS,
    REQUEST_DELAY_MIN,
    REQUEST_DELAY_MAX,
    REQUEST_TIMEOUT,
    AGENCY_INDICATORS,
    PROXY_CONFIG_FILE
)


class ProxyConfig:
    """Gestisce la configurazione del proxy"""

    def __init__(self):
        self.enabled: bool = False
        self.server: str = ""
        self.username: str = ""
        self.password: str = ""

    def load_from_file(self) -> bool:
        """Carica la configurazione dal file JSON"""
        try:
            if os.path.exists(PROXY_CONFIG_FILE):
                with open(PROXY_CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.enabled = data.get('enabled', False)
                    self.server = data.get('server', '')
                    self.username = data.get('username', '')
                    self.password = data.get('password', '')
                    return True
        except Exception:
            pass
        return False

    def save_to_file(self) -> bool:
        """Salva la configurazione nel file JSON"""
        try:
            data = {
                'enabled': self.enabled,
                'server': self.server,
                'username': self.username,
                'password': self.password
            }
            with open(PROXY_CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False

    def get_playwright_proxy(self) -> Optional[Dict]:
        """Ritorna la configurazione proxy per Playwright"""
        if not self.enabled or not self.server:
            return None

        proxy = {'server': self.server}

        if self.username:
            proxy['username'] = self.username
        if self.password:
            proxy['password'] = self.password

        return proxy

    def is_valid(self) -> bool:
        """Verifica se la configurazione è valida"""
        if not self.enabled:
            return True  # Proxy disabilitato è valido
        return bool(self.server)

    def get_display_string(self) -> str:
        """Ritorna una stringa per visualizzazione (nasconde password)"""
        if not self.enabled:
            return "Proxy disabilitato"
        if not self.server:
            return "Proxy non configurato"

        # Nascondi password nella visualizzazione
        if self.username:
            return f"{self.username}:***@{self.server}"
        return self.server


# Configurazione proxy globale
_proxy_config = ProxyConfig()


def get_proxy_config() -> ProxyConfig:
    """Ritorna la configurazione proxy globale"""
    return _proxy_config


def load_proxy_config():
    """Carica la configurazione proxy dal file"""
    _proxy_config.load_from_file()


class BaseScraper(ABC):
    """Classe base per tutti gli scrapers dei portali immobiliari"""

    def __init__(self, headless: bool = True, use_stealth: bool = True):
        self.headless = headless
        self.use_stealth = use_stealth
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.stealth = None
        self._progress_callback: Optional[Callable[[str], None]] = None

    @property
    @abstractmethod
    def nome_portale(self) -> str:
        """Nome del portale (es. 'Subito', 'Immobiliare')"""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """URL base del portale"""
        pass

    @property
    def source_type(self) -> str:
        """Tipo di sorgente dati - sempre 'scraper' per questa classe"""
        return "scraper"

    def is_available(self) -> bool:
        """Gli scraper sono sempre disponibili (non richiedono configurazione API)"""
        return True

    def set_progress_callback(self, callback: Callable[[str], None]):
        """Imposta la callback per aggiornamenti di progresso"""
        self._progress_callback = callback

    def log_progress(self, message: str):
        """Logga un messaggio di progresso"""
        if self._progress_callback:
            self._progress_callback(f"[{self.nome_portale}] {message}")

    def start_browser(self):
        """Avvia il browser Playwright con supporto proxy e stealth"""
        self.log_progress("Avvio browser...")

        proxy_config = get_proxy_config()
        proxy = proxy_config.get_playwright_proxy()

        if proxy:
            self.log_progress(f"Usando proxy: {proxy_config.get_display_string()}")

        # Usa playwright-stealth se disponibile e abilitato
        if self.use_stealth:
            try:
                from playwright_stealth import Stealth
                self.stealth = Stealth(
                    navigator_languages_override=('it-IT', 'it'),
                    navigator_platform_override='Win32'
                )
                self.playwright = self.stealth.use_sync(sync_playwright()).__enter__()
                self.log_progress("Stealth mode attivato")
            except ImportError:
                self.log_progress("playwright-stealth non disponibile, uso normale")
                self.playwright = sync_playwright().start()
        else:
            self.playwright = sync_playwright().start()

        # Avvia il browser
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )

        # Crea il contesto con o senza proxy
        context_options = {
            'user_agent': random.choice(USER_AGENTS),
            'viewport': {'width': 1920, 'height': 1080},
            'locale': 'it-IT',
            'timezone_id': 'Europe/Rome'
        }

        if proxy:
            context_options['proxy'] = proxy

        self.context = self.browser.new_context(**context_options)
        self.page = self.context.new_page()
        self.page.set_default_timeout(REQUEST_TIMEOUT)

        # Aggiungi script per nascondere webdriver
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

    def close_browser(self):
        """Chiude il browser"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.stealth:
                # Chiudi il context manager di stealth
                try:
                    self.stealth.use_sync(sync_playwright()).__exit__(None, None, None)
                except:
                    pass
            elif self.playwright:
                self.playwright.stop()
        except Exception as e:
            pass
        self.log_progress("Browser chiuso")

    def random_delay(self):
        """Attende un tempo casuale per evitare ban"""
        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        time.sleep(delay)

    def accept_cookies(self):
        """Prova ad accettare i cookie se presente il banner"""
        cookie_selectors = [
            '#didomi-notice-agree-button',
            '[id*="accept"]',
            '[class*="accept"]',
            'button:has-text("Accetta")',
            'button:has-text("Accetto")',
            'button:has-text("OK")',
            '[data-testid*="accept"]'
        ]

        for selector in cookie_selectors:
            try:
                btn = self.page.query_selector(selector)
                if btn and btn.is_visible():
                    btn.click()
                    self.page.wait_for_timeout(1000)
                    self.log_progress("Cookie accettati")
                    return True
            except:
                continue

        return False

    def is_private_seller(self, seller_name: str, description: str = "") -> bool:
        """
        Verifica se il venditore è un privato (non un'agenzia).
        Ritorna True se è un privato, False se sembra un'agenzia.
        """
        text_to_check = f"{seller_name} {description}".lower()

        for indicator in AGENCY_INDICATORS:
            if indicator.lower() in text_to_check:
                return False

        return True

    def clean_price(self, price_text: str) -> int:
        """Pulisce e converte il testo del prezzo in intero"""
        if not price_text:
            return 0
        # Rimuovi tutto tranne i numeri
        cleaned = re.sub(r'[^\d]', '', price_text)
        try:
            return int(cleaned)
        except ValueError:
            return 0

    def clean_phone(self, phone_text: str) -> str:
        """Pulisce il numero di telefono"""
        if not phone_text:
            return ""
        # Mantieni solo numeri e alcuni caratteri
        cleaned = re.sub(r'[^\d+\-\s]', '', phone_text)
        # Rimuovi spazi multipli
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def clean_text(self, text: str) -> str:
        """Pulisce un testo generico"""
        if not text:
            return ""
        # Rimuovi newline e spazi multipli
        cleaned = re.sub(r'\s+', ' ', text).strip()
        return cleaned

    def extract_mq(self, text: str) -> int:
        """Estrae i metri quadri da un testo"""
        if not text:
            return 0
        # Cerca pattern come "85 mq", "85mq", "85 m²"
        match = re.search(r'(\d+)\s*(?:mq|m²|m2)', text.lower())
        if match:
            return int(match.group(1))
        return 0

    def extract_locali(self, text: str) -> int:
        """Estrae il numero di locali da un testo"""
        if not text:
            return 0
        # Cerca pattern come "3 locali", "trilocale", etc.
        match = re.search(r'(\d+)\s*(?:local|vani|stanz)', text.lower())
        if match:
            return int(match.group(1))

        # Cerca nomi specifici
        locali_map = {
            'monolocale': 1,
            'bilocale': 2,
            'trilocale': 3,
            'quadrilocale': 4,
            'pentalocale': 5
        }
        text_lower = text.lower()
        for nome, num in locali_map.items():
            if nome in text_lower:
                return num

        return 0

    @abstractmethod
    def build_search_url(self, filters: SearchFilters, page_num: int = 1) -> str:
        """
        Costruisce l'URL di ricerca con i filtri applicati.
        Da implementare per ogni portale specifico.
        """
        pass

    @abstractmethod
    def parse_listing_page(self) -> List[dict]:
        """
        Parsa la pagina dei risultati e ritorna una lista di dizionari
        con i dati base di ogni annuncio (url, prezzo, titolo, etc.).
        Da implementare per ogni portale specifico.
        """
        pass

    @abstractmethod
    def parse_listing_detail(self, listing_url: str) -> Optional[Lead]:
        """
        Parsa la pagina di dettaglio di un annuncio e ritorna un Lead.
        Da implementare per ogni portale specifico.
        """
        pass

    def has_next_page(self) -> bool:
        """
        Verifica se esiste una pagina successiva.
        Override nei sottoclassi se necessario.
        """
        return False

    def search(self, filters: SearchFilters) -> List[Lead]:
        """
        Esegue la ricerca completa e ritorna la lista di Lead trovati.
        """
        leads = []
        page_num = 1

        try:
            self.start_browser()

            while page_num <= 10:  # Massimo 10 pagine
                url = self.build_search_url(filters, page_num)
                self.log_progress(f"Caricamento pagina {page_num}...")

                try:
                    self.page.goto(url, wait_until='networkidle', timeout=45000)
                    self.random_delay()

                    # Prova ad accettare cookie al primo caricamento
                    if page_num == 1:
                        self.accept_cookies()

                    # Parsa i risultati della pagina
                    listings = self.parse_listing_page()

                    if not listings:
                        self.log_progress(f"Nessun risultato nella pagina {page_num}")
                        break

                    self.log_progress(f"Trovati {len(listings)} annunci nella pagina {page_num}")

                    # Per ogni annuncio, estrai i dettagli
                    for i, listing in enumerate(listings):
                        if not listing.get('url'):
                            continue

                        # Verifica se è un privato già dai dati base
                        seller = listing.get('seller_name', '')
                        if seller and not self.is_private_seller(seller):
                            continue

                        self.log_progress(f"Analisi annuncio {i+1}/{len(listings)}...")

                        try:
                            lead = self.parse_listing_detail(listing['url'])
                            if lead and lead.has_contact_info():
                                # Verifica finale che sia un privato
                                if self.is_private_seller(lead.nome_completo, lead.descrizione):
                                    lead.fonte = self.nome_portale
                                    leads.append(lead)
                                    self.log_progress(f"Lead valido trovato: {lead.comune}")
                        except Exception as e:
                            self.log_progress(f"Errore parsing dettaglio: {str(e)}")

                        self.random_delay()

                        # Limita il numero di risultati
                        if len(leads) >= filters.max_risultati_per_sito:
                            break

                    # Verifica se c'è una pagina successiva
                    if not self.has_next_page() or len(leads) >= filters.max_risultati_per_sito:
                        break

                    page_num += 1

                except Exception as e:
                    self.log_progress(f"Errore caricamento pagina: {str(e)}")
                    break

        except Exception as e:
            self.log_progress(f"Errore generale: {str(e)}")

        finally:
            self.close_browser()

        self.log_progress(f"Ricerca completata: {len(leads)} lead trovati")
        return leads
