"""
Finestra principale dell'applicazione
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List
import os

from models.lead import Lead
from models.search_filters import SearchFilters
from services.scoring_service import ScoringService
from services.excel_exporter import ExcelExporter
from services.deduplicator import Deduplicator
from data_sources import get_data_source, get_all_data_sources
from data_sources.factory import get_available_sources_info
from scrapers.base_scraper import get_proxy_config, load_proxy_config

from .filters_frame import FiltersFrame
from .results_frame import ResultsFrame
from .progress_dialog import ProgressDialog, SearchWorker
from .proxy_dialog import ProxyDialog


class MainWindow:
    """Finestra principale dell'applicazione"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Agente Acquisizione Immobili")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)

        # Carica configurazione proxy
        load_proxy_config()

        # Servizi
        self.scoring_service = ScoringService()
        self.excel_exporter = ExcelExporter()
        self.deduplicator = Deduplicator()

        # Dati correnti
        self.current_leads: List[Lead] = []
        self.current_filters: SearchFilters = None

        # Configura stile
        self._setup_style()

        # Crea menu
        self._create_menu()

        # Crea i widget
        self._create_widgets()

        # Centra la finestra
        self._center_window()

        # Mostra stato proxy
        self._update_proxy_status()

    def _setup_style(self):
        """Configura lo stile dell'applicazione"""
        style = ttk.Style()

        # Prova a usare un tema moderno
        available_themes = style.theme_names()
        if 'clam' in available_themes:
            style.theme_use('clam')
        elif 'vista' in available_themes:
            style.theme_use('vista')

        # Stile per il bottone principale
        style.configure('Accent.TButton', font=('Helvetica', 10, 'bold'))

    def _create_menu(self):
        """Crea la barra dei menu"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Menu File
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Esporta risultati...", command=self._on_export)
        file_menu.add_separator()
        file_menu.add_command(label="Esci", command=self.root.quit)

        # Menu Impostazioni
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Impostazioni", menu=settings_menu)
        settings_menu.add_command(label="Configura Proxy...", command=self._open_proxy_settings)

        # Menu Aiuto
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Aiuto", menu=help_menu)
        help_menu.add_command(label="Guida Proxy", command=self._show_proxy_help)
        help_menu.add_separator()
        help_menu.add_command(label="Info", command=self._show_about)

    def _create_widgets(self):
        """Crea tutti i widget della finestra"""
        # Frame principale con padding
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header con titolo e stato proxy
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        # Titolo
        title_label = ttk.Label(header_frame, text="AGENTE ACQUISIZIONE IMMOBILI",
                                font=('Helvetica', 16, 'bold'))
        title_label.pack(side=tk.LEFT)

        # Stato proxy (a destra)
        self.proxy_status_label = ttk.Label(header_frame, text="",
                                            font=('Helvetica', 9))
        self.proxy_status_label.pack(side=tk.RIGHT)

        # Bottone configura proxy
        proxy_btn = ttk.Button(header_frame, text="Proxy",
                              command=self._open_proxy_settings, width=8)
        proxy_btn.pack(side=tk.RIGHT, padx=10)

        # Sottotitolo
        subtitle = ttk.Label(main_frame,
                            text="Ricerca annunci di privati su portali immobiliari italiani",
                            font=('Helvetica', 10))
        subtitle.pack(pady=(0, 15))

        # Frame filtri
        self.filters_frame = FiltersFrame(main_frame, self._on_search)
        self.filters_frame.pack(fill=tk.X, pady=(0, 10))

        # Frame risultati
        self.results_frame = ResultsFrame(main_frame, self._on_export)
        self.results_frame.pack(fill=tk.BOTH, expand=True)

        # Barra di stato
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))

        self.status_label = ttk.Label(status_frame, text="Pronto",
                                       relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X)

    def _center_window(self):
        """Centra la finestra sullo schermo"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'+{x}+{y}')

    def _update_proxy_status(self):
        """Aggiorna lo stato del proxy visualizzato"""
        proxy_config = get_proxy_config()
        if proxy_config.enabled and proxy_config.server:
            self.proxy_status_label.config(
                text="Proxy: ATTIVO",
                foreground='green'
            )
        else:
            self.proxy_status_label.config(
                text="Proxy: NON ATTIVO",
                foreground='red'
            )

    def _open_proxy_settings(self):
        """Apre la finestra di configurazione proxy"""
        dialog = ProxyDialog(self.root)
        self.root.wait_window(dialog)
        # Aggiorna lo stato dopo la chiusura
        load_proxy_config()
        self._update_proxy_status()

    def _show_proxy_help(self):
        """Mostra la guida per il proxy"""
        help_text = """GUIDA CONFIGURAZIONE PROXY

I portali immobiliari italiani (Subito, Immobiliare, etc.)
utilizzano sistemi anti-bot che bloccano le richieste automatizzate.

Per utilizzare questa applicazione serve un PROXY RESIDENZIALE.

COS'E' UN PROXY RESIDENZIALE?
Un proxy residenziale usa indirizzi IP di utenti reali,
rendendo le richieste indistinguibili da quelle umane.

PROVIDER CONSIGLIATI:
- IPRoyal: ~7 EUR/GB (economico)
- Smartproxy: ~12.5 EUR/GB
- Bright Data: ~15 EUR/GB (affidabile)
- Oxylabs: ~15 EUR/GB

COME CONFIGURARE:
1. Registrati su un provider
2. Ottieni le credenziali (server, username, password)
3. Vai su Impostazioni > Configura Proxy
4. Inserisci i dati e salva

FORMATO SERVER:
http://indirizzo:porta
Esempio: http://geo.iproyal.com:12321

CONSUMO DATI STIMATO:
Una ricerca completa consuma circa 50-100 MB.
Con 1 GB puoi fare circa 10-20 ricerche.
"""
        messagebox.showinfo("Guida Proxy", help_text)

    def _show_about(self):
        """Mostra informazioni sull'applicazione"""
        # Ottieni info sulle sorgenti
        sources_info = get_available_sources_info()

        about_text = """AGENTE ACQUISIZIONE IMMOBILI

Versione: 2.0 (con supporto API)

Applicazione per la ricerca automatizzata
di annunci immobiliari da privati.

Funzionalita':
- API ufficiali (Idealista, Immobiliare.it)
- Scraping fallback per altri portali
- Sistema di scoring lead
- Export in Excel

Portali supportati:
"""
        for portal, info in sources_info.items():
            status = "API" if info['will_use'] == 'api' else "Scraper"
            if info['api_available'] and not info['api_configured']:
                status = "Scraper (API disponibile ma non configurata)"
            about_text += f"- {portal.capitalize()}: {status}\n"

        messagebox.showinfo("Info", about_text)

    def _on_search(self, filters: SearchFilters):
        """Gestisce l'avvio della ricerca"""
        # Valida i filtri
        valid, error_msg = filters.validate()
        if not valid:
            messagebox.showerror("Errore filtri", error_msg)
            return

        self.current_filters = filters

        # Ottieni info sulle sorgenti disponibili
        sources_info = get_available_sources_info()

        # Verifica se useremo scraper (per mostrare avviso proxy)
        will_use_scraper = any(
            sources_info.get(site, {}).get('will_use') == 'scraper'
            for site in filters.siti_attivi
        )

        # Verifica proxy solo se useremo scraper
        proxy_config = get_proxy_config()
        if will_use_scraper and not proxy_config.enabled:
            # Mostra quali siti useranno scraper
            scraper_sites = [
                site for site in filters.siti_attivi
                if sources_info.get(site, {}).get('will_use') == 'scraper'
            ]
            api_sites = [
                site for site in filters.siti_attivi
                if sources_info.get(site, {}).get('will_use') == 'api'
            ]

            msg = "ATTENZIONE: Il proxy non e' configurato.\n\n"
            if api_sites:
                msg += f"Siti con API (OK): {', '.join(api_sites)}\n"
            msg += f"Siti con scraper (richiede proxy): {', '.join(scraper_sites)}\n\n"
            msg += "Senza proxy, i siti con scraper potrebbero bloccare le richieste.\n\n"
            msg += "Vuoi configurare il proxy adesso?\n"
            msg += "(Clicca 'No' per provare comunque)"

            result = messagebox.askyesno("Proxy non configurato", msg)
            if result:
                self._open_proxy_settings()
                return

        # Ottieni le sorgenti dati per i siti selezionati (API o scraper)
        data_sources = get_all_data_sources(filters.siti_attivi)

        if not data_sources:
            messagebox.showerror("Errore", "Nessun sito selezionato")
            return

        # Log quali sorgenti verranno usate
        for source in data_sources:
            source_type = "API" if source.source_type == "api" else "Scraper"
            print(f"[{source.nome_portale}] Usando: {source_type}")

        # Disabilita i controlli
        self.filters_frame.set_searching(True)
        self.status_label.config(text="Ricerca in corso...")

        # Apri dialog di progresso
        progress_dialog = ProgressDialog(self.root, "Ricerca in corso...")

        # Avvia il worker (usa data_sources invece di scrapers)
        worker = SearchWorker(
            dialog=progress_dialog,
            scrapers=data_sources,  # Il worker funziona con qualsiasi BaseDataSource
            filters=filters,
            scoring_service=self.scoring_service,
            deduplicator=self.deduplicator,
            callback=self._on_search_complete
        )
        worker.start()

    def _on_search_complete(self, leads: List[Lead]):
        """Callback chiamata al termine della ricerca"""
        self.current_leads = leads

        # Riabilita i controlli
        self.filters_frame.set_searching(False)

        # Mostra i risultati
        self.results_frame.set_leads(leads)

        # Aggiorna status
        if leads:
            self.status_label.config(text=f"Ricerca completata: {len(leads)} lead trovati")
        else:
            self.status_label.config(text="Ricerca completata: nessun risultato")

    def _on_export(self):
        """Gestisce l'export in Excel"""
        if not self.current_leads:
            messagebox.showwarning("Attenzione", "Nessun lead da esportare")
            return

        # Chiedi dove salvare
        default_name = f"acquisizioni_{self.current_filters.localita.replace(' ', '_')}.xlsx"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile=default_name
        )

        if not file_path:
            return

        try:
            self.status_label.config(text="Esportazione in corso...")
            self.root.update()

            output_path = self.excel_exporter.export(
                self.current_leads,
                self.current_filters,
                file_path
            )

            self.status_label.config(text=f"File salvato: {output_path}")
            messagebox.showinfo("Export completato",
                               f"File Excel salvato correttamente:\n{output_path}")

            # Chiedi se aprire il file
            if messagebox.askyesno("Apri file", "Vuoi aprire il file Excel?"):
                os.startfile(output_path)

        except Exception as e:
            self.status_label.config(text="Errore durante l'export")
            messagebox.showerror("Errore export", f"Errore durante l'esportazione:\n{str(e)}")

    def run(self):
        """Avvia l'applicazione"""
        self.root.mainloop()
