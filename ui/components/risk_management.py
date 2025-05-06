import tkinter as tk
from tkinter import ttk
from typing import Dict, Callable


class RiskManagementPanel(ttk.LabelFrame):
    def __init__(self, master, risks: Dict[str, float],
                 on_risk_change: Callable, **kwargs):
        super().__init__(master, text="Управление рисками", **kwargs)
        self.risks = risks
        self.on_change = on_risk_change
        self._create_widgets()

    def _create_widgets(self):
        risk_types = [
            ("Рик на сделку (%):", "risk_per_trade"),
            ("Риск на все сделки (%):", "risk_all_trades"),
            ("Дневной риск (%):", "daily_risk")
        ]

        self.spinboxes = {}
        for i, (label, key) in enumerate(risk_types):
            ttk.Label(self, text=label).grid(row=i, column=0, sticky=tk.W)
            spin = ttk.Spinbox(
                self,
                from_=0.1,
                to=100,
                increment=0.1,
                command=lambda k=key: self.on_change(k, float(self.spinboxes[k].get()))
            )
            spin.set(self.risks.get(key, 1.0))
            spin.grid(row=i, column=1, sticky=tk.EW, padx=5, pady=2)
            self.spinboxes[key] = spin

        self.columnconfigure(1, weight=1)