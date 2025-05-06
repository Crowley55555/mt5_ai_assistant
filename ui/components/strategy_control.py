import tkinter as tk
from tkinter import ttk
from typing import Dict, Callable
from config.constants import StrategyNames


class StrategyControlPanel(ttk.LabelFrame):
    def __init__(self, master, strategies: Dict[str, bool],
                 on_strategy_toggle: Callable, **kwargs):
        super().__init__(master, text="Управление стратегиями", **kwargs)
        self.strategies = strategies
        self.on_toggle = on_strategy_toggle
        self._create_widgets()

    def _create_widgets(self):
        self.checkbuttons = {}
        for i, (name, active) in enumerate(self.strategies.items()):
            var = tk.BooleanVar(value=active)
            cb = ttk.Checkbutton(
                self,
                text=name,
                variable=var,
                command=lambda n=name, v=var: self.on_toggle(n, v.get())
            )
            cb.grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            self.checkbuttons[name] = var