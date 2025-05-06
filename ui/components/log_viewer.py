import tkinter as tk
from tkinter import ttk
import logging
from logging.handlers import QueueHandler


class LogViewer(ttk.LabelFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, text="Лог выполнения", **kwargs)
        self._create_widgets()
        self._setup_logging()

    def _create_widgets(self):
        self.text = tk.Text(self, wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(self, command=self.text.yview)
        self.text.config(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.pack(fill=tk.BOTH, expand=True)

    def _setup_logging(self):
        handler = self.TextHandler(self.text)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(handler)

    class TextHandler(logging.Handler):
        def __init__(self, text_widget):
            super().__init__()
            self.text_widget = text_widget

        def emit(self, record):
            msg = self.format(record)
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.insert(tk.END, msg + "\n")
            self.text_widget.config(state=tk.DISABLED)
            self.text_widget.see(tk.END)