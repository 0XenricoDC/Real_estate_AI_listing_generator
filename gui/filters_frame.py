"""
Frame per i filtri di ricerca
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict

from models.search_filters import SearchFilters
from config import PROPERTY_TYPES, PROPERTY_STATES, RADIUS_OPTIONS


class FiltersFrame(ttk.LabelFrame):
    """Frame contenente i controlli per i filtri di ricerca"""

    def __init__(self, parent, on_search: Callable[[SearchFilters], None]):
        super().__init__(parent, text="Filtri di Ricerca", padding=10)

        self.on_search = on_search
        self.site_vars: Dict[str, tk.BooleanVar] = {}

        self._create_widgets()

    def _create_widgets(self):
        """Crea tutti i widget del frame"""

        # === Riga 1: Località e Raggio ===
        row1 = ttk.Frame(self)
        row1.pack(fill=tk.X, pady=5)

        ttk.Label(row1, text="Località:").pack(side=tk.LEFT, padx=(0, 5))
        self.localita_entry = ttk.Entry(row1, width=25)
        self.localita_entry.pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(row1, text="Raggio:").pack(side=tk.LEFT, padx=(0, 5))
        self.raggio_combo = ttk.Combobox(row1, values=[f"{r} km" for r in RADIUS_OPTIONS],
                                          width=10, state='readonly')
        self.raggio_combo.set("20 km")
        self.raggio_combo.pack(side=tk.LEFT)

        # === Riga 2: Prezzo ===
        row2 = ttk.Frame(self)
        row2.pack(fill=tk.X, pady=5)

        ttk.Label(row2, text="Prezzo min:").pack(side=tk.LEFT, padx=(0, 5))
        self.prezzo_min_entry = ttk.Entry(row2, width=12)
        self.prezzo_min_entry.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(row2, text="€").pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(row2, text="Prezzo max:").pack(side=tk.LEFT, padx=(0, 5))
        self.prezzo_max_entry = ttk.Entry(row2, width=12)
        self.prezzo_max_entry.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(row2, text="€").pack(side=tk.LEFT)

        # === Riga 3: Tipo e Stato ===
        row3 = ttk.Frame(self)
        row3.pack(fill=tk.X, pady=5)

        ttk.Label(row3, text="Tipo immobile:").pack(side=tk.LEFT, padx=(0, 5))
        self.tipo_combo = ttk.Combobox(row3, values=PROPERTY_TYPES, width=18, state='readonly')
        self.tipo_combo.set("Tutti")
        self.tipo_combo.pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(row3, text="Stato:").pack(side=tk.LEFT, padx=(0, 5))
        self.stato_combo = ttk.Combobox(row3, values=PROPERTY_STATES, width=15, state='readonly')
        self.stato_combo.set("Tutti")
        self.stato_combo.pack(side=tk.LEFT)

        # === Riga 4: MQ e Locali ===
        row4 = ttk.Frame(self)
        row4.pack(fill=tk.X, pady=5)

        ttk.Label(row4, text="MQ min:").pack(side=tk.LEFT, padx=(0, 5))
        self.mq_min_entry = ttk.Entry(row4, width=8)
        self.mq_min_entry.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(row4, text="MQ max:").pack(side=tk.LEFT, padx=(0, 5))
        self.mq_max_entry = ttk.Entry(row4, width=8)
        self.mq_max_entry.pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(row4, text="Locali min:").pack(side=tk.LEFT, padx=(0, 5))
        self.locali_min_entry = ttk.Entry(row4, width=5)
        self.locali_min_entry.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(row4, text="Locali max:").pack(side=tk.LEFT, padx=(0, 5))
        self.locali_max_entry = ttk.Entry(row4, width=5)
        self.locali_max_entry.pack(side=tk.LEFT)

        # === Riga 5: Siti da cercare ===
        row5 = ttk.LabelFrame(self, text="Siti da cercare", padding=5)
        row5.pack(fill=tk.X, pady=10)

        sites_frame = ttk.Frame(row5)
        sites_frame.pack()

        sites = [
            ('subito', 'Subito.it'),
            ('immobiliare', 'Immobiliare.it'),
            ('idealista', 'Idealista'),
            ('casa', 'Casa.it'),
            ('bakeca', 'Bakeca.it')
        ]

        for site_id, site_name in sites:
            var = tk.BooleanVar(value=True)
            self.site_vars[site_id] = var
            cb = ttk.Checkbutton(sites_frame, text=site_name, variable=var)
            cb.pack(side=tk.LEFT, padx=10)

        # === Riga 6: Bottoni ===
        row6 = ttk.Frame(self)
        row6.pack(fill=tk.X, pady=10)

        self.search_btn = ttk.Button(row6, text="AVVIA RICERCA",
                                     command=self._on_search_click,
                                     style='Accent.TButton')
        self.search_btn.pack(side=tk.LEFT, padx=5)

        self.clear_btn = ttk.Button(row6, text="Pulisci filtri",
                                    command=self._clear_filters)
        self.clear_btn.pack(side=tk.LEFT, padx=5)

    def _parse_int(self, value: str) -> int:
        """Converte una stringa in intero, ritorna None se vuota/invalida"""
        if not value or not value.strip():
            return None
        try:
            # Rimuovi punti e virgole (separatori migliaia)
            cleaned = value.replace('.', '').replace(',', '').strip()
            return int(cleaned)
        except ValueError:
            return None

    def get_filters(self) -> SearchFilters:
        """Ritorna i filtri correnti come oggetto SearchFilters"""
        # Estrai raggio dal combo
        raggio_text = self.raggio_combo.get()
        raggio = int(raggio_text.replace(' km', '')) if raggio_text else 20

        # Siti attivi
        siti_attivi = [site for site, var in self.site_vars.items() if var.get()]

        return SearchFilters(
            localita=self.localita_entry.get().strip(),
            raggio_km=raggio,
            prezzo_min=self._parse_int(self.prezzo_min_entry.get()),
            prezzo_max=self._parse_int(self.prezzo_max_entry.get()),
            tipo_immobile=self.tipo_combo.get(),
            stato_immobile=self.stato_combo.get(),
            mq_min=self._parse_int(self.mq_min_entry.get()),
            mq_max=self._parse_int(self.mq_max_entry.get()),
            locali_min=self._parse_int(self.locali_min_entry.get()),
            locali_max=self._parse_int(self.locali_max_entry.get()),
            siti_attivi=siti_attivi
        )

    def _on_search_click(self):
        """Gestisce il click sul bottone di ricerca"""
        filters = self.get_filters()
        self.on_search(filters)

    def _clear_filters(self):
        """Pulisce tutti i filtri"""
        self.localita_entry.delete(0, tk.END)
        self.raggio_combo.set("20 km")
        self.prezzo_min_entry.delete(0, tk.END)
        self.prezzo_max_entry.delete(0, tk.END)
        self.tipo_combo.set("Tutti")
        self.stato_combo.set("Tutti")
        self.mq_min_entry.delete(0, tk.END)
        self.mq_max_entry.delete(0, tk.END)
        self.locali_min_entry.delete(0, tk.END)
        self.locali_max_entry.delete(0, tk.END)

        # Riattiva tutti i siti
        for var in self.site_vars.values():
            var.set(True)

    def set_searching(self, is_searching: bool):
        """Abilita/disabilita i controlli durante la ricerca"""
        state = 'disabled' if is_searching else 'normal'

        self.localita_entry.config(state=state)
        self.raggio_combo.config(state='disabled' if is_searching else 'readonly')
        self.prezzo_min_entry.config(state=state)
        self.prezzo_max_entry.config(state=state)
        self.tipo_combo.config(state='disabled' if is_searching else 'readonly')
        self.stato_combo.config(state='disabled' if is_searching else 'readonly')
        self.mq_min_entry.config(state=state)
        self.mq_max_entry.config(state=state)
        self.locali_min_entry.config(state=state)
        self.locali_max_entry.config(state=state)

        for site_id in self.site_vars:
            # I checkbutton non hanno config state diretto, li gestiamo diversamente
            pass

        self.search_btn.config(state=state)
        self.clear_btn.config(state=state)
