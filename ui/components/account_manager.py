import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict


class AccountManagerFrame(ttk.LabelFrame):
    def __init__(self, master, settings, mt5_client, logger, **kwargs):
        """
        Инициализация менеджера аккаунтов

        :param master: Родительский виджет
        :param settings: Объект настроек
        :param mt5_client: Клиент MT5
        :param logger: Логгер приложения
        :param kwargs: Дополнительные параметры LabelFrame
        """
        super().__init__(master, text="Управление аккаунтами", **kwargs)
        self.settings = settings
        self.mt5_client = mt5_client
        self.logger = logger
        self.account_combobox = None
        self.login_entry = None
        self.password_entry = None
        self.server_entry = None
        self.path_entry = None

        # Создаем интерфейс
        self._create_widgets()

    def _create_widgets(self):
        """Создание элементов интерфейса"""
        # Combobox для выбора аккаунта
        ttk.Label(self, text="Аккаунт:").grid(row=0, column=0, sticky=tk.W)
        self.account_combobox = ttk.Combobox(self, state="readonly")
        self.account_combobox.grid(row=0, column=1, sticky=tk.EW, padx=5)
        self.account_combobox.bind("<<ComboboxSelected>>", self._on_account_select)

        # Поля ввода
        fields = [
            ("Логин:", "login_entry"),
            ("Пароль:", "password_entry", "*"),
            ("Сервер:", "server_entry"),
            ("Путь к MT5:", "path_entry")
        ]

        for i, field in enumerate(fields, start=1):
            label_text = field[0]
            entry_name = field[1]
            show_char = field[2] if len(field) > 2 else ""

            ttk.Label(self, text=label_text).grid(row=i, column=0, sticky=tk.W)
            entry = ttk.Entry(self, show=show_char)
            entry.grid(row=i, column=1, sticky=tk.EW, padx=5)

            setattr(self, entry_name, entry)

        # Кнопка выбора пути
        ttk.Button(self, text="Обзор", command=self._browse_mt5_path).grid(
            row=len(fields), column=2, padx=5
        )

        # Кнопки управления
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=len(fields) + 1, column=0, columnspan=3, pady=5)

        ttk.Button(btn_frame, text="Добавить аккаунт", command=self._add_account).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(btn_frame, text="Удалить аккаунт", command=self._remove_account).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(btn_frame, text="Подключиться", command=self._connect_mt5).pack(
            side=tk.RIGHT, padx=2
        )

        # Настройка растягивания
        self.columnconfigure(1, weight=1)

        # Загрузка данных
        self._update_accounts_dropdown()

    def _on_account_select(self, event=None):
        """Обработчик выбора аккаунта"""
        idx = self.account_combobox.current()
        if idx >= 0:
            account = self.settings.accounts[idx]
            self.login_entry.delete(0, tk.END)
            self.login_entry.insert(0, account.get('login', ''))
            self.password_entry.delete(0, tk.END)
            self.password_entry.insert(0, account.get('password', ''))
            self.server_entry.delete(0, tk.END)
            self.server_entry.insert(0, account.get('server', ''))
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, account.get('path', ''))
            self.settings.set_current_account(idx)
            self.logger.info(f"Выбран аккаунт {account['login']}")

    def _add_telegram_fields(self):
        """Добавляет поля для Telegram (не должно быть здесь)"""
        ttk.Label(self, text="Telegram Token:").grid(row=5, column=0, sticky=tk.W)
        self.telegram_token_entry = ttk.Entry(self)
        self.telegram_token_entry.grid(row=5, column=1, sticky=tk.EW, padx=5)

        ttk.Label(self, text="Chat ID:").grid(row=6, column=0, sticky=tk.W)
        self.chat_id_entry = ttk.Entry(self)
        self.chat_id_entry.grid(row=6, column=1, sticky=tk.EW, padx=5)

    def _browse_mt5_path(self):
        """Выбор пути к терминалу MT5"""
        path = filedialog.askopenfilename(
            title="Выберите исполняемый файл MT5",
            filetypes=[("Исполняемые файлы", "*.exe"), ("Все файлы", "*.*")]
        )
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)

    def _add_account(self):
        """Добавление нового аккаунта"""
        login = self.login_entry.get().strip()
        password = self.password_entry.get().strip()
        server = self.server_entry.get().strip()
        path = self.path_entry.get().strip()

        if not all([login, password, server, path]):
            self.logger.warning("Не все поля заполнены при добавлении аккаунта")
            messagebox.showwarning("Ошибка", "Заполните все поля аккаунта")
            return

        # Сохраняем аккаунт через Settings
        if not any(acc['login'] == login for acc in self.settings.accounts):
            self.settings.add_account(login, password, server, path)
            self.logger.info(f"Добавлен новый аккаунт: {login}")
            self._update_accounts_dropdown()
        else:
            self.logger.warning(f"Аккаунт {login} уже существует")

    def _remove_account(self):
        """Удаление выбранного аккаунта"""
        idx = self.account_combobox.current()
        if idx >= 0:
            account = self.settings.accounts[idx]
            confirm = messagebox.askyesno("Подтверждение", f"Удалить аккаунт {account['login']}?")
            if confirm:
                self.settings._settings["accounts"].pop(idx)
                self.settings.save()
                self._update_accounts_dropdown()
                self._clear_account_fields()
                self.logger.info(f"Аккаунт {account['login']} удален")

    def _clear_account_fields(self):
        """Очистка полей формы аккаунта"""
        for entry in [self.login_entry, self.password_entry, self.server_entry, self.path_entry]:
            entry.delete(0, tk.END)

    def _connect_mt5(self):
        """Подключение к MT5"""
        login = self.login_entry.get().strip()
        password = self.password_entry.get().strip()
        server = self.server_entry.get().strip()
        path = self.path_entry.get().strip()

        if not all([login, password, server, path]):
            self.logger.warning("Попытка подключения с незаполненными данными")
            messagebox.showerror("Ошибка", "Заполните все поля подключения")
            return

        try:
            # Подключаемся к MT5
            if self.mt5_client.connect(login, password, server, path):
                self.logger.info(f"Подключение к MT5 успешно: {login}")
                # Обновляем список аккаунтов
                if not any(acc['login'] == login for acc in self.settings.accounts):
                    self.settings.add_account(login, password, server, path)
                self.settings.save()
                self._save_settings()
                messagebox.showinfo("Успех", "Подключение к MT5 установлено")
            else:
                self.logger.error("Не удалось подключиться к MT5")
                messagebox.showerror("Ошибка", "Не удалось подключиться к MT5")
        except Exception as e:
            self.logger.critical(f"Критическая ошибка подключения к MT5: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось подключиться к MT5: {str(e)}")

    def _update_accounts_dropdown(self):
        """Обновление выпадающего списка аккаунтов"""
        accounts = self.settings.accounts
        values = [f"{acc['login']}@{acc['server']}" for acc in accounts]
        self.account_combobox["values"] = values
        if accounts:
            self.account_combobox.current(self.settings.current_account_index)
        self.logger.debug("Список аккаунтов обновлен")

    def _load_current_account(self):
        """Загрузка текущего аккаунта в форму"""
        current = self.settings.current_account
        self.login_entry.delete(0, tk.END)
        self.login_entry.insert(0, current.get('login', ''))
        self.password_entry.delete(0, tk.END)
        self.password_entry.insert(0, current.get('password', ''))
        self.server_entry.delete(0, tk.END)
        self.server_entry.insert(0, current.get('server', ''))
        self.path_entry.delete(0, tk.END)
        self.path_entry.insert(0, current.get('path', ''))

    def _save_settings(self):
        """Сохраняет текущие данные аккаунта в настройках"""
        current_account = {
            'login': self.login_entry.get(),
            'password': self.password_entry.get(),
            'server': self.server_entry.get(),
            'path': self.path_entry.get()
        }
        self.settings._settings["accounts"][self.settings.current_account_index] = current_account
        self.settings.save()