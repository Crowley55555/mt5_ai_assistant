import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
from core.database import MarketDatabase


class AccountManagerFrame(ttk.LabelFrame):
    def __init__(self, master, db: Optional[MarketDatabase] = None, **kwargs):
        super().__init__(master, text="Управление аккаунтами", **kwargs)
        self.db = db
        self._create_widgets()

    def _create_widgets(self):
        # Combobox для выбора аккаунтов
        self.account_cb = ttk.Combobox(self, state="readonly")
        self.account_cb.grid(row=0, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=5)

        # Поля ввода
        fields = [
            ("Логин:", "login_var"),
            ("Пароль:", "password_var", "*"),
            ("Сервер:", "server_var"),
            ("Путь:", "path_var")
        ]

        self.vars = {}
        for i, (label, var_name, *show) in enumerate(fields, start=1):
            ttk.Label(self, text=label).grid(row=i, column=0, sticky=tk.W)
            self.vars[var_name] = tk.StringVar()
            entry = ttk.Entry(self, textvariable=self.vars[var_name], show=show[0] if show else "")
            entry.grid(row=i, column=1, sticky=tk.EW, padx=5)
            if label == "Путь:":
                ttk.Button(self, text="Обзор", command=self._browse_path).grid(row=i, column=2, padx=5)

        # Кнопки управления
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=len(fields) + 1, column=0, columnspan=3, pady=5)

        ttk.Button(btn_frame, text="Добавить", command=self._add_account).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Удалить", command=self._remove_account).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Подключиться", command=self._connect_account).pack(side=tk.RIGHT, padx=2)

        self.columnconfigure(1, weight=1)

    def _browse_path(self):
        path = tk.filedialog.askopenfilename(title="Выберите terminal.exe")
        if path:
            self.vars["path_var"].set(path)

    def _add_account(self):
        # Реализация добавления аккаунта
        pass

    def _remove_account(self):
        # Реализация удаления аккаунта
        pass

    def _connect_account(self):
        # Реализация подключения
        pass