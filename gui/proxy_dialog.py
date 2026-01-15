"""
Dialog per la configurazione del proxy
"""

import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

from scrapers.base_scraper import get_proxy_config, ProxyConfig
from config import PROXY_PROVIDERS


class ProxyDialog(tk.Toplevel):
    """Finestra di dialogo per configurare il proxy"""

    def __init__(self, parent):
        super().__init__(parent)

        self.title("Configurazione Proxy")
        self.geometry("550x500")
        self.resizable(False, False)

        # Rendi modale
        self.transient(parent)
        self.grab_set()

        # Centra
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 550) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 500) // 2
        self.geometry(f"+{x}+{y}")

        # Carica configurazione corrente
        self.proxy_config = get_proxy_config()

        self._create_widgets()
        self._load_current_config()

    def _create_widgets(self):
        """Crea i widget del dialog"""
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === Titolo e spiegazione ===
        title = ttk.Label(main_frame, text="Configurazione Proxy",
                         font=('Helvetica', 12, 'bold'))
        title.pack(anchor=tk.W)

        info_text = """I portali immobiliari italiani bloccano i bot.
Per utilizzare l'applicazione serve un proxy residenziale."""
        info = ttk.Label(main_frame, text=info_text, wraplength=500)
        info.pack(anchor=tk.W, pady=(5, 15))

        # === Checkbox abilita proxy ===
        self.enabled_var = tk.BooleanVar()
        self.enabled_cb = ttk.Checkbutton(
            main_frame,
            text="Abilita proxy",
            variable=self.enabled_var,
            command=self._on_enable_change
        )
        self.enabled_cb.pack(anchor=tk.W, pady=5)

        # === Frame configurazione ===
        config_frame = ttk.LabelFrame(main_frame, text="Configurazione", padding=10)
        config_frame.pack(fill=tk.X, pady=10)

        # Server
        ttk.Label(config_frame, text="Server proxy:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.server_entry = ttk.Entry(config_frame, width=45)
        self.server_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(config_frame, text="es: http://proxy.example.com:8080",
                 font=('Helvetica', 8)).grid(row=1, column=1, sticky=tk.W)

        # Username
        ttk.Label(config_frame, text="Username:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.username_entry = ttk.Entry(config_frame, width=30)
        self.username_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

        # Password
        ttk.Label(config_frame, text="Password:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.password_entry = ttk.Entry(config_frame, width=30, show="*")
        self.password_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)

        # Mostra password
        self.show_pass_var = tk.BooleanVar()
        show_pass_cb = ttk.Checkbutton(config_frame, text="Mostra password",
                                       variable=self.show_pass_var,
                                       command=self._toggle_password)
        show_pass_cb.grid(row=4, column=1, sticky=tk.W, padx=5)

        # === Provider consigliati ===
        providers_frame = ttk.LabelFrame(main_frame, text="Provider Proxy Consigliati", padding=10)
        providers_frame.pack(fill=tk.X, pady=10)

        # Crea tabella provider
        columns = ('name', 'type', 'price')
        self.providers_tree = ttk.Treeview(providers_frame, columns=columns,
                                           show='headings', height=4)

        self.providers_tree.heading('name', text='Provider')
        self.providers_tree.heading('type', text='Tipo')
        self.providers_tree.heading('price', text='Prezzo')

        self.providers_tree.column('name', width=150)
        self.providers_tree.column('type', width=100)
        self.providers_tree.column('price', width=100)

        for provider in PROXY_PROVIDERS:
            self.providers_tree.insert('', tk.END, values=(
                provider['name'],
                provider['type'],
                provider['price']
            ))

        self.providers_tree.pack(fill=tk.X)
        self.providers_tree.bind('<Double-1>', self._on_provider_click)

        ttk.Label(providers_frame, text="Doppio click per aprire il sito del provider",
                 font=('Helvetica', 8)).pack(anchor=tk.W, pady=(5, 0))

        # === Bottoni ===
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=15)

        ttk.Button(btn_frame, text="Test Connessione",
                  command=self._test_connection).pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="Salva",
                  command=self._save_config).pack(side=tk.RIGHT, padx=5)

        ttk.Button(btn_frame, text="Annulla",
                  command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _load_current_config(self):
        """Carica la configurazione corrente nei campi"""
        self.enabled_var.set(self.proxy_config.enabled)
        self.server_entry.insert(0, self.proxy_config.server)
        self.username_entry.insert(0, self.proxy_config.username)
        self.password_entry.insert(0, self.proxy_config.password)
        self._on_enable_change()

    def _on_enable_change(self):
        """Gestisce il cambio dello stato di abilitazione"""
        enabled = self.enabled_var.get()
        state = 'normal' if enabled else 'disabled'
        self.server_entry.config(state=state)
        self.username_entry.config(state=state)
        self.password_entry.config(state=state)

    def _toggle_password(self):
        """Mostra/nasconde la password"""
        show = self.show_pass_var.get()
        self.password_entry.config(show="" if show else "*")

    def _on_provider_click(self, event):
        """Apre il sito del provider al doppio click"""
        selection = self.providers_tree.selection()
        if selection:
            item = selection[0]
            values = self.providers_tree.item(item, 'values')
            provider_name = values[0]

            for provider in PROXY_PROVIDERS:
                if provider['name'] == provider_name:
                    webbrowser.open(provider['url'])
                    break

    def _test_connection(self):
        """Testa la connessione proxy"""
        if not self.enabled_var.get():
            messagebox.showinfo("Test", "Proxy disabilitato. Abilita il proxy per testare.")
            return

        server = self.server_entry.get().strip()
        if not server:
            messagebox.showerror("Errore", "Inserisci l'indirizzo del server proxy")
            return

        # Salva temporaneamente la configurazione
        self.proxy_config.enabled = True
        self.proxy_config.server = server
        self.proxy_config.username = self.username_entry.get().strip()
        self.proxy_config.password = self.password_entry.get()

        # Test connessione
        messagebox.showinfo("Test",
            "Il test della connessione proxy verra' eseguito alla prossima ricerca.\n\n"
            "Salva la configurazione e prova una ricerca per verificare che funzioni.")

    def _save_config(self):
        """Salva la configurazione"""
        self.proxy_config.enabled = self.enabled_var.get()
        self.proxy_config.server = self.server_entry.get().strip()
        self.proxy_config.username = self.username_entry.get().strip()
        self.proxy_config.password = self.password_entry.get()

        if self.proxy_config.enabled and not self.proxy_config.server:
            messagebox.showerror("Errore", "Inserisci l'indirizzo del server proxy")
            return

        if self.proxy_config.save_to_file():
            messagebox.showinfo("Salvato", "Configurazione proxy salvata correttamente!")
            self.destroy()
        else:
            messagebox.showerror("Errore", "Impossibile salvare la configurazione")
