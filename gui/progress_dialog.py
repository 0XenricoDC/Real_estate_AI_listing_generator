"""
Dialog per mostrare il progresso dello scraping
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable
import threading
import queue


class ProgressDialog(tk.Toplevel):
    """Finestra di dialogo per mostrare il progresso dello scraping"""

    def __init__(self, parent, title: str = "Ricerca in corso..."):
        super().__init__(parent)

        self.title(title)
        self.geometry("500x350")
        self.resizable(False, False)

        # Rendi la finestra modale
        self.transient(parent)
        self.grab_set()

        # Centra la finestra
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 500) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 350) // 2
        self.geometry(f"+{x}+{y}")

        # Variabili di stato
        self.cancelled = False
        self.message_queue = queue.Queue()

        self._create_widgets()

        # Inizia a controllare la coda messaggi
        self._check_queue()

    def _create_widgets(self):
        """Crea i widget del dialog"""
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Label stato corrente
        self.status_label = ttk.Label(main_frame, text="Inizializzazione...",
                                       font=('Helvetica', 10, 'bold'))
        self.status_label.pack(pady=(0, 10))

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate', length=400)
        self.progress.pack(pady=10)
        self.progress.start(10)

        # Label sito corrente
        self.site_label = ttk.Label(main_frame, text="")
        self.site_label.pack(pady=5)

        # Area log
        log_frame = ttk.LabelFrame(main_frame, text="Log operazioni", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Scrollbar per il log
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(log_frame, height=10, width=55, state='disabled',
                                yscrollcommand=scrollbar.set, font=('Consolas', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)

        # Bottone annulla
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        self.cancel_btn = ttk.Button(btn_frame, text="Annulla", command=self._on_cancel)
        self.cancel_btn.pack()

        # Gestisci chiusura finestra
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def update_status(self, message: str):
        """Aggiorna il messaggio di stato (thread-safe)"""
        self.message_queue.put(('status', message))

    def update_site(self, site_name: str):
        """Aggiorna il sito corrente (thread-safe)"""
        self.message_queue.put(('site', site_name))

    def add_log(self, message: str):
        """Aggiunge un messaggio al log (thread-safe)"""
        self.message_queue.put(('log', message))

    def set_progress_determinate(self, total: int):
        """Imposta la progress bar in modalità determinata"""
        self.message_queue.put(('progress_mode', ('determinate', total)))

    def update_progress(self, current: int):
        """Aggiorna il valore della progress bar"""
        self.message_queue.put(('progress', current))

    def _check_queue(self):
        """Controlla la coda messaggi e aggiorna la UI"""
        try:
            while True:
                msg_type, msg_data = self.message_queue.get_nowait()

                if msg_type == 'status':
                    self.status_label.config(text=msg_data)
                elif msg_type == 'site':
                    self.site_label.config(text=f"Sito corrente: {msg_data}")
                elif msg_type == 'log':
                    self.log_text.config(state='normal')
                    self.log_text.insert(tk.END, msg_data + '\n')
                    self.log_text.see(tk.END)
                    self.log_text.config(state='disabled')
                elif msg_type == 'progress_mode':
                    mode, total = msg_data
                    self.progress.stop()
                    self.progress.config(mode=mode, maximum=total, value=0)
                elif msg_type == 'progress':
                    self.progress.config(value=msg_data)

        except queue.Empty:
            pass

        # Continua a controllare se non è stata chiusa
        if self.winfo_exists():
            self.after(100, self._check_queue)

    def _on_cancel(self):
        """Gestisce il click su Annulla"""
        self.cancelled = True
        self.status_label.config(text="Annullamento in corso...")
        self.cancel_btn.config(state='disabled')

    def is_cancelled(self) -> bool:
        """Ritorna True se l'operazione è stata annullata"""
        return self.cancelled

    def close(self):
        """Chiude il dialog"""
        self.progress.stop()
        self.grab_release()
        self.destroy()


class SearchWorker:
    """Worker per eseguire la ricerca in un thread separato"""

    def __init__(self, dialog: ProgressDialog, scrapers: list, filters,
                 scoring_service, deduplicator, callback: Callable):
        self.dialog = dialog
        self.scrapers = scrapers
        self.filters = filters
        self.scoring_service = scoring_service
        self.deduplicator = deduplicator
        self.callback = callback
        self.all_leads = []

    def start(self):
        """Avvia il worker in un thread separato"""
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self):
        """Esegue la ricerca"""
        try:
            total_sites = len(self.scrapers)
            self.dialog.set_progress_determinate(total_sites)

            for i, scraper in enumerate(self.scrapers):
                if self.dialog.is_cancelled():
                    break

                site_name = scraper.nome_portale
                self.dialog.update_site(site_name)
                self.dialog.update_status(f"Ricerca su {site_name}...")
                self.dialog.add_log(f"Avvio ricerca su {site_name}")

                # Imposta callback per log
                scraper.set_progress_callback(self.dialog.add_log)

                try:
                    leads = scraper.search(self.filters)
                    self.all_leads.extend(leads)
                    self.dialog.add_log(f"Trovati {len(leads)} lead su {site_name}")
                except Exception as e:
                    self.dialog.add_log(f"Errore su {site_name}: {str(e)}")

                self.dialog.update_progress(i + 1)

            if not self.dialog.is_cancelled():
                # Deduplicazione
                self.dialog.update_status("Rimozione duplicati...")
                self.dialog.add_log(f"Lead totali prima della deduplicazione: {len(self.all_leads)}")

                unique_leads, removed = self.deduplicator.remove_duplicates(self.all_leads)
                self.dialog.add_log(f"Rimossi {removed} duplicati")

                # Scoring
                self.dialog.update_status("Calcolo score e priorità...")
                scored_leads = self.scoring_service.process_leads(unique_leads)
                self.dialog.add_log(f"Lead finali: {len(scored_leads)}")

                self.all_leads = scored_leads

            # Chiama la callback nel thread principale
            self.dialog.after(100, lambda: self._complete())

        except Exception as e:
            self.dialog.add_log(f"Errore critico: {str(e)}")
            self.dialog.after(100, lambda: self._complete())

    def _complete(self):
        """Completa l'operazione"""
        self.dialog.close()
        self.callback(self.all_leads if not self.dialog.is_cancelled() else [])
