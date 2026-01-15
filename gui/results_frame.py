"""
Frame per la visualizzazione dei risultati
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Callable
import webbrowser

from models.lead import Lead


class ResultsFrame(ttk.LabelFrame):
    """Frame per visualizzare i risultati della ricerca in una tabella"""

    # Colonne della tabella
    COLUMNS = [
        ('score', 'Score', 60),
        ('priorita', 'Priorità', 80),
        ('nome', 'Nome', 120),
        ('telefono', 'Telefono', 120),
        ('comune', 'Comune', 120),
        ('provincia', 'Prov', 50),
        ('prezzo', 'Prezzo', 100),
        ('tipo', 'Tipo', 100),
        ('mq', 'MQ', 60),
        ('locali', 'Loc', 50),
        ('fonte', 'Fonte', 100)
    ]

    def __init__(self, parent, on_export: Callable[[], None]):
        super().__init__(parent, text="Risultati", padding=10)

        self.on_export = on_export
        self.leads: List[Lead] = []

        self._create_widgets()

    def _create_widgets(self):
        """Crea i widget del frame"""

        # Header con conteggio e bottone export
        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(0, 10))

        self.count_label = ttk.Label(header, text="Nessun risultato")
        self.count_label.pack(side=tk.LEFT)

        self.export_btn = ttk.Button(header, text="Esporta Excel",
                                     command=self.on_export, state='disabled')
        self.export_btn.pack(side=tk.RIGHT)

        # Frame per la treeview con scrollbar
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollbar verticale
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Scrollbar orizzontale
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        # Treeview
        columns = [col[0] for col in self.COLUMNS]
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings',
                                  yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        # Configura le colonne
        for col_id, col_name, col_width in self.COLUMNS:
            self.tree.heading(col_id, text=col_name,
                             command=lambda c=col_id: self._sort_column(c))
            self.tree.column(col_id, width=col_width, minwidth=40)

        self.tree.pack(fill=tk.BOTH, expand=True)

        # Bind per doppio click (apre URL)
        self.tree.bind('<Double-1>', self._on_double_click)

        # Menu contestuale
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Apri annuncio", command=self._open_url)
        self.context_menu.add_command(label="Copia telefono", command=self._copy_phone)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Dettagli lead", command=self._show_details)

        self.tree.bind('<Button-3>', self._show_context_menu)

        # Statistiche rapide in fondo
        stats_frame = ttk.Frame(self)
        stats_frame.pack(fill=tk.X, pady=(10, 0))

        self.stats_label = ttk.Label(stats_frame, text="")
        self.stats_label.pack(side=tk.LEFT)

    def set_leads(self, leads: List[Lead]):
        """Imposta i lead da visualizzare"""
        self.leads = leads

        # Pulisci la tabella
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Aggiungi i lead
        for lead in leads:
            values = (
                lead.lead_score,
                lead.priorita,
                lead.nome_completo or "-",
                lead.telefono or "-",
                lead.comune or "-",
                lead.provincia or "-",
                f"€ {lead.prezzo_richiesto:,}".replace(',', '.') if lead.prezzo_richiesto else "-",
                lead.tipo_immobile or "-",
                lead.mq if lead.mq else "-",
                lead.locali if lead.locali else "-",
                lead.fonte or "-"
            )

            # Tag per il colore
            tag = lead.priorita.lower()
            self.tree.insert('', tk.END, values=values, tags=(tag,))

        # Configura i colori per priorità
        self.tree.tag_configure('alta', background='#90EE90')
        self.tree.tag_configure('media', background='#FFFF99')
        self.tree.tag_configure('bassa', background='#D3D3D3')

        # Aggiorna conteggio
        self._update_count()

        # Abilita export se ci sono risultati
        self.export_btn.config(state='normal' if leads else 'disabled')

    def _update_count(self):
        """Aggiorna il label del conteggio"""
        total = len(self.leads)
        if total == 0:
            self.count_label.config(text="Nessun risultato")
            self.stats_label.config(text="")
            return

        alta = sum(1 for l in self.leads if l.priorita == 'ALTA')
        media = sum(1 for l in self.leads if l.priorita == 'MEDIA')
        bassa = sum(1 for l in self.leads if l.priorita == 'BASSA')

        self.count_label.config(text=f"Totale: {total} lead trovati")
        self.stats_label.config(
            text=f"Alta priorità: {alta} | Media: {media} | Bassa: {bassa}"
        )

    def _sort_column(self, col_id: str):
        """Ordina la tabella per colonna"""
        # Ottieni i dati correnti
        items = [(self.tree.set(item, col_id), item) for item in self.tree.get_children('')]

        # Determina se ordinare come numero o stringa
        try:
            items.sort(key=lambda x: float(x[0].replace('€', '').replace('.', '').replace('-', '0').strip()))
        except ValueError:
            items.sort(key=lambda x: x[0])

        # Riordina nella treeview
        for index, (_, item) in enumerate(items):
            self.tree.move(item, '', index)

    def _on_double_click(self, event):
        """Gestisce il doppio click su una riga"""
        self._open_url()

    def _open_url(self):
        """Apre l'URL dell'annuncio nel browser"""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        index = self.tree.index(item)

        if 0 <= index < len(self.leads):
            url = self.leads[index].url_annuncio
            if url:
                webbrowser.open(url)

    def _copy_phone(self):
        """Copia il numero di telefono negli appunti"""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        index = self.tree.index(item)

        if 0 <= index < len(self.leads):
            phone = self.leads[index].telefono
            if phone:
                self.clipboard_clear()
                self.clipboard_append(phone)

    def _show_details(self):
        """Mostra i dettagli completi del lead"""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        index = self.tree.index(item)

        if 0 <= index < len(self.leads):
            lead = self.leads[index]

            # Crea finestra di dettaglio
            detail_window = tk.Toplevel(self)
            detail_window.title(f"Dettagli Lead - {lead.comune}")
            detail_window.geometry("500x400")

            text = tk.Text(detail_window, wrap=tk.WORD, padx=10, pady=10)
            text.pack(fill=tk.BOTH, expand=True)

            details = f"""
INFORMAZIONI VENDITORE
Nome: {lead.nome_completo or 'N/D'}
Telefono: {lead.telefono or 'N/D'}
Email: {lead.email or 'N/D'}

INFORMAZIONI IMMOBILE
Indirizzo: {lead.via_indirizzo or 'N/D'}
Comune: {lead.comune or 'N/D'} ({lead.provincia or 'N/D'})
CAP: {lead.cap or 'N/D'}
Prezzo: € {lead.prezzo_richiesto:,}
Tipo: {lead.tipo_immobile or 'N/D'}
Superficie: {lead.mq or 'N/D'} mq
Locali: {lead.locali or 'N/D'}
Stato: {lead.stato_immobile or 'N/D'}

SCORING
Punteggio: {lead.lead_score}/100
Priorità: {lead.priorita}

METADATA
Fonte: {lead.fonte or 'N/D'}
Data pubblicazione: {lead.data_pubblicazione.strftime('%d/%m/%Y') if lead.data_pubblicazione else 'N/D'}
URL: {lead.url_annuncio or 'N/D'}

NOTE
{lead.note or 'Nessuna nota'}

DESCRIZIONE
{lead.descrizione or 'Nessuna descrizione'}
"""
            text.insert('1.0', details)
            text.config(state='disabled')

    def _show_context_menu(self, event):
        """Mostra il menu contestuale"""
        # Seleziona l'item sotto il cursore
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def clear(self):
        """Pulisce tutti i risultati"""
        self.leads = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._update_count()
        self.export_btn.config(state='disabled')
