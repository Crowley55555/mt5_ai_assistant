import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Dict
from config.settings import Settings
from utils.logger import TradingLogger
from core.mt5_client import MT5Client
from core.risk_manager import RiskManager
from core.telegram_bot import TelegramBot
from core.ollama_integration import OllamaIntegration
from core.strategies import SniperStrategy, SmartSniperStrategy, SmartMoneyStrategy
from config.constants import Timeframes
import logging
from pathlib import Path
import shutil

class TradingAssistantApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AI Trading Assistant for MT5")
        self.root.geometry("1000x700")

        # Инициализация компонентов
        self.settings = Settings()
        self.logger = TradingLogger(log_file="logs/trading_assistant.log")
        self.settings.set_logger(self.logger)
        self.mt5_client = MT5Client(self.logger)
        self.risk_manager = RiskManager(self.mt5_client, self.logger)
        self.telegram_bot = None
        self.ollama = None

        # Инициализация стратегий
        self.strategies = {
            "Снайпер": SniperStrategy(self.mt5_client, self.logger),
            "Смарт Снайпер": SmartSniperStrategy(self.mt5_client, self.logger),
            "Смарт Мани": SmartMoneyStrategy(self.mt5_client, self.logger)
        }

        def _setup_account_ui(self, parent_frame):
            """Настройка UI компонентов для управления аккаунтами"""
            self.account_frame = ttk.LabelFrame(parent_frame, text="Управление аккаунтами MT5", padding="10")
            self.account_frame.pack(fill=tk.X, pady=5)

            # Combobox для выбора аккаунта
            ttk.Label(self.account_frame, text="Аккаунт:").grid(row=0, column=0, sticky=tk.W)
            self.account_combobox = ttk.Combobox(self.account_frame, state="readonly")
            self.account_combobox.grid(row=0, column=1, sticky=tk.EW, padx=5)
            self.account_combobox.bind("<<ComboboxSelected>>", self._on_account_select)

            # Поля ввода
            fields = [
                ("Логин:", "login_entry", ""),
                ("Пароль:", "password_entry", "*"),
                ("Сервер:", "server_entry", ""),
                ("Путь к MT5:", "path_entry", "")
            ]

            for i, (label, attr_name, show) in enumerate(fields, start=1):
                ttk.Label(self.account_frame, text=label).grid(row=i, column=0, sticky=tk.W)
                entry = ttk.Entry(self.account_frame, show=show)
                entry.grid(row=i, column=1, sticky=tk.EW, padx=5)
                setattr(self, attr_name, entry)
                if label == "Путь к MT5:":
                    ttk.Button(self.account_frame, text="Обзор", command=self._browse_mt5_path).grid(row=i, column=2,
                                                                                                     padx=5)

            # Кнопки управления
            btn_frame = ttk.Frame(self.account_frame)
            btn_frame.grid(row=len(fields) + 1, column=0, columnspan=3, pady=(5, 0))

            buttons = [
                ("Добавить аккаунт", self._add_account),
                ("Удалить аккаунт", self._remove_account),
                ("Подключиться", self._connect_mt5)
            ]

            for text, command in buttons:
                ttk.Button(btn_frame, text=text, command=command).pack(
                    side=tk.LEFT if text != "Подключиться" else tk.RIGHT, padx=2)

        def _show_trade_statistics(self):
            """Показывает статистику сделок"""
            if not hasattr(self, 'core') or not self.core.database:
                messagebox.showerror("Ошибка", "База данных не подключена")
                return

            stats = self.core.risk_manager.get_trade_statistics()
            messagebox.showinfo(
                "Статистика",
                f"Всего сделок: {stats['total_trades']}\n"
                f"Процент прибыльных: {stats['win_rate']:.1%}\n"
                f"Средняя прибыль: {stats['avg_profit']:.2f}"
            )

        def _on_account_select(self, event=None):
            """Обработчик выбора аккаунта"""
            try:
                idx = self.account_combobox.current()
                if idx >= 0:
                    account = self.settings.accounts[idx]
                    self.login_entry.delete(0, tk.END)
                    self.login_entry.insert(0, account.get("login", ""))
                    self.password_entry.delete(0, tk.END)
                    self.password_entry.insert(0, account.get("password", ""))
                    self.server_entry.delete(0, tk.END)
                    self.server_entry.insert(0, account.get("server", ""))
                    self.path_entry.delete(0, tk.END)
                    self.path_entry.insert(0, account.get("path", ""))
                    self.settings.set_current_account(idx)
                    self.logger.info(f"Выбран аккаунт {account['login']}")
            except Exception as e:
                self.logger.error(f"Ошибка выбора аккаунта: {str(e)}")

        def _add_account(self):
            """Добавление нового аккаунта"""
            try:
                account_data = {
                    "login": self.login_entry.get(),
                    "password": self.password_entry.get(),
                    "server": self.server_entry.get(),
                    "path": self.path_entry.get()
                }

                if not all(account_data.values()):
                    self.logger.warning("Не все поля аккаунта заполнены")
                    messagebox.showerror("Ошибка", "Заполните все поля")
                    return

                self.settings.add_account(**account_data)
                self._update_accounts_dropdown()
                messagebox.showinfo("Успех", "Аккаунт сохранен")
                self.logger.info(f"Добавлен новый аккаунт: {account_data['login']}")
            except Exception as e:
                self.logger.error(f"Ошибка добавления аккаунта: {str(e)}")
                messagebox.showerror("Ошибка", f"Не удалось добавить аккаунт: {str(e)}")

        def _update_accounts_dropdown(self):
            """Обновление списка аккаунтов в Combobox"""
            try:
                accounts = self.settings.accounts
                self.account_combobox["values"] = [f"{acc['login']}@{acc['server']}" for acc in accounts]
                if accounts:
                    self.account_combobox.current(self.settings.current_account_index)
                    self.logger.debug("Обновлен список аккаунтов в интерфейсе")
            except Exception as e:
                self.logger.error(f"Ошибка обновления списка аккаунтов: {str(e)}")

        def _show_trade_statistics(self):
            """Новый метод для отображения статистики"""
            if not hasattr(self, 'core') or not self.core.database:
                return

            stats = self.core.risk_manager.get_trade_statistics()
            text = (
                f"Статистика сделок:\n"
                f"Всего сделок: {stats['total_trades']}\n"
                f"Процент прибыльных: {stats['win_rate']:.1%}\n"
                f"Средняя прибыль: {stats['avg_profit']:.2f}"
            )
            messagebox.showinfo("Статистика", text)


        # Создание интерфейса
        self._create_widgets()
        self._load_settings()

        # Переменные состояния
        self.is_running = False
        self.update_interval = 5000  # 5 секунд

    def _create_widgets(self):
        """Создание всех элементов интерфейса"""
        # Основные фреймы
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Левая панель - настройки
        left_panel = ttk.Frame(main_frame, width=300, padding="10")
        left_panel.pack(side=tk.LEFT, fill=tk.Y)

        # Правая панель - лог и графики
        right_panel = ttk.Frame(main_frame, padding="10")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Настройки подключения
        import json
        from typing import Dict, List

        class Settings:
            def __init__(self, config_path: str = "config/config.json"):
                self.config_path = Path(config_path)
                self._settings = self._load_settings()

            def _load_settings(self):
                def _load_settings(self):
                    """Полностью прописанная функция загрузки настроек в интерфейс"""
                    # Загрузка аккаунта MT5
                    current_account = self.settings.current_account
                    self.account_manager.login_entry.delete(0, tk.END)
                    self.account_manager.login_entry.insert(0, current_account.get('login', ''))
                    self.account_manager.password_entry.delete(0, tk.END)
                    self.account_manager.password_entry.insert(0, current_account.get('password', ''))
                    self.account_manager.server_entry.delete(0, tk.END)
                    self.account_manager.server_entry.insert(0, current_account.get('server', ''))
                    self.account_manager.path_entry.delete(0, tk.END)
                    self.account_manager.path_entry.insert(0, current_account.get('path', ''))

                    # Загрузка Telegram настроек
                    self.account_manager.telegram_token_entry.delete(0, tk.END)
                    self.account_manager.telegram_token_entry.insert(0, self.settings.telegram.get('token', ''))
                    self.account_manager.chat_id_entry.delete(0, tk.END)
                    self.account_manager.chat_id_entry.insert(0, self.settings.telegram.get('chat_id', ''))

                    # Загрузка Ollama настроек
                    self.ollama_url_entry.delete(0, tk.END)
                    self.ollama_url_entry.insert(0, self.settings.ollama.get('base_url', ''))
                    self.ollama_model_entry.delete(0, tk.END)
                    self.ollama_model_entry.insert(0, self.settings.ollama.get('model', ''))

                    # Загрузка настроек рисков
                    risk_settings = self.settings.risk_management
                    self.risk_per_trade_spin.delete(0, tk.END)
                    self.risk_per_trade_spin.insert(0, str(risk_settings.get('risk_per_trade', 1.0)))
                    self.risk_all_trades_spin.delete(0, tk.END)
                    self.risk_all_trades_spin.insert(0, str(risk_settings.get('risk_all_trades', 5.0)))
                    self.daily_risk_spin.delete(0, tk.END)
                    self.daily_risk_spin.insert(0, str(risk_settings.get('daily_risk', 10.0)))

                def _save_settings(self):
                    """Полностью прописанная функция сохранения настроек"""
                    # Сохраняем MT5 аккаунт
                    current_account = {
                        'login': self.account_manager.login_entry.get(),
                        'password': self.account_manager.password_entry.get(),
                        'server': self.account_manager.server_entry.get(),
                        'path': self.account_manager.path_entry.get()
                    }

                    # Обновляем текущий аккаунт в настройках
                    if current_account['login']:  # Если есть логин, сохраняем аккаунт
                        if not any(acc['login'] == current_account['login'] for acc in self.settings.accounts):
                            self.settings.accounts.append(current_account)
                        self.settings.set_current_account(len(self.settings.accounts) - 1)

                    # Сохраняем Telegram настройки
                    self.settings._settings['telegram'] = {
                        'token': self.account_manager.telegram_token_entry.get(),
                        'chat_id': self.account_manager.chat_id_entry.get()
                    }

                    # Сохраняем Ollama настройки
                    self.settings._settings['ollama'] = {
                        'base_url': self.ollama_url_entry.get(),
                        'model': self.ollama_model_entry.get()
                    }

                    # Сохраняем настройки рисков
                    self.settings._settings['risk_management'] = {
                        'risk_per_trade': float(self.risk_per_trade_spin.get()),
                        'risk_all_trades': float(self.risk_all_trades_spin.get()),
                        'daily_risk': float(self.daily_risk_spin.get())
                    }

                    # Сохраняем все настройки в файл
                    self.settings.save()
                    self.logger.info("Все настройки успешно сохранены")

                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)

                    # Миграция старых настроек из формата mt5 в accounts
                    if "mt5" in loaded and loaded["mt5"]:
                        if "accounts" not in loaded:
                            loaded["accounts"] = []

                        loaded["accounts"].append({
                            "login": loaded["mt5"].get("login", ""),
                            "password": loaded["mt5"].get("password", ""),
                            "server": loaded["mt5"].get("server", ""),
                            "path": loaded["mt5"].get("path", "")
                        })
                        self.logger.debug("Выполнена миграция старых настроек MT5 в новый формат")
                        del loaded["mt5"]  # Удаляем старый формат после миграции

                    return loaded

            def save(self):
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(self._settings, f, indent=4, ensure_ascii=False)

            @property
            def accounts(self) -> List[Dict]:
                return self._settings.get("accounts", [])

            @property
            def current_account(self) -> Dict:
                idx = self._settings.get("current_account_index", 0)
                return self.accounts[idx] if self.accounts else {
                    "login": "", "password": "", "server": "", "path": ""
                }

            def add_account(self, login: str, password: str, server: str, path: str):
                if not any(acc["login"] == login for acc in self.accounts):
                    self._settings["accounts"].append({
                        "login": login,
                        "password": password,
                        "server": server,
                        "path": path
                    })
                    self.save()

            def set_current_account(self, index: int):
                if 0 <= index < len(self.accounts):
                    self._settings["current_account_index"] = index
                    self.save()



        # Настройки Telegram
        telegram_frame = ttk.LabelFrame(left_panel, text="Telegram уведомления", padding="10")
        telegram_frame.pack(fill=tk.X, pady=5)

        ttk.Label(telegram_frame, text="Токен бота:").grid(row=0, column=0, sticky=tk.W)
        self.telegram_token_entry = ttk.Entry(telegram_frame)
        self.telegram_token_entry.grid(row=0, column=1, sticky=tk.EW, padx=5)

        ttk.Label(telegram_frame, text="Chat ID:").grid(row=1, column=0, sticky=tk.W)
        self.telegram_chat_id_entry = ttk.Entry(telegram_frame)
        self.telegram_chat_id_entry.grid(row=1, column=1, sticky=tk.EW, padx=5)

        ttk.Button(telegram_frame, text="Тест уведомления", command=self._test_telegram).grid(row=2, column=0,
                                                                                              columnspan=2, pady=5)

        # Настройки Ollama
        ollama_frame = ttk.LabelFrame(left_panel, text="Ollama интеграция", padding="10")
        ollama_frame.pack(fill=tk.X, pady=5)

        ttk.Label(ollama_frame, text="URL сервера:").grid(row=0, column=0, sticky=tk.W)
        self.ollama_url_entry = ttk.Entry(ollama_frame)
        self.ollama_url_entry.grid(row=0, column=1, sticky=tk.EW, padx=5)

        ttk.Label(ollama_frame, text="Модель:").grid(row=1, column=0, sticky=tk.W)
        self.ollama_model_entry = ttk.Entry(ollama_frame)
        self.ollama_model_entry.grid(row=1, column=1, sticky=tk.EW, padx=5)

        ttk.Button(ollama_frame, text="Загрузить базу знаний", command=self._load_knowledge_base).grid(row=2, column=0,
                                                                                                       columnspan=2,
                                                                                                       pady=5)

        # Управление рисками
        risk_frame = ttk.LabelFrame(left_panel, text="Управление рисками", padding="10")
        risk_frame.pack(fill=tk.X, pady=5)

        ttk.Label(risk_frame, text="Риск на сделку (%):").grid(row=0, column=0, sticky=tk.W)
        self.risk_per_trade_spin = ttk.Spinbox(risk_frame, from_=0.1, to=10, increment=0.1)
        self.risk_per_trade_spin.grid(row=0, column=1, sticky=tk.EW, padx=5)

        ttk.Label(risk_frame, text="Риск на все сделки (%):").grid(row=1, column=0, sticky=tk.W)
        self.risk_all_trades_spin = ttk.Spinbox(risk_frame, from_=1, to=50, increment=1)
        self.risk_all_trades_spin.grid(row=1, column=1, sticky=tk.EW, padx=5)

        ttk.Label(risk_frame, text="Дневной риск (%):").grid(row=2, column=0, sticky=tk.W)
        self.daily_risk_spin = ttk.Spinbox(risk_frame, from_=1, to=100, increment=1)
        self.daily_risk_spin.grid(row=2, column=1, sticky=tk.EW, padx=5)

        ttk.Button(risk_frame, text="Применить", command=self._update_risk_settings).grid(row=3, column=0, columnspan=2,
                                                                                          pady=5)

        # Управление стратегиями
        strategies_frame = ttk.LabelFrame(left_panel, text="Торговые стратегии", padding="10")
        strategies_frame.pack(fill=tk.X, pady=5)

        self.strategy_vars = {}
        for i, (name, strategy) in enumerate(self.strategies.items()):
            var = tk.BooleanVar()
            chk = ttk.Checkbutton(strategies_frame, text=name, variable=var,
                                  command=lambda n=name, v=var: self._toggle_strategy(n, v))
            chk.grid(row=i, column=0, sticky=tk.W)
            self.strategy_vars[name] = var

        # Кнопки управления
        control_frame = ttk.Frame(left_panel, padding="10")
        control_frame.pack(fill=tk.X, pady=5)

        stats_btn = ttk.Button(control_frame, text="Статистика", command=self._show_trade_statistics)
        stats_btn.pack(side=tk.LEFT, padx=5)

        self.start_btn = ttk.Button(control_frame, text="Старт", command=self._start_trading)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(control_frame, text="Стоп", command=self._stop_trading, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # Лог
        log_frame = ttk.LabelFrame(right_panel, text="Лог", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # Перенаправление логов в текстовое поле
        self.logger.logger.addHandler(self._create_text_handler())

    def _create_text_handler(self):
        """Создание обработчика логов для Text виджета"""

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

        handler = TextHandler(self.log_text)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        return handler

    def _load_settings(self):
        """Загрузка настроек в интерфейс"""
        # MT5
        self.login_entry.insert(0, self.settings.mt5.get('login', ''))
        self.password_entry.insert(0, self.settings.mt5.get('password', ''))
        self.server_entry.insert(0, self.settings.mt5.get('server', ''))
        self.path_entry.insert(0, self.settings.mt5.get('path', ''))

        # Telegram
        self.telegram_token_entry.insert(0, self.settings.telegram.get('token', ''))
        self.telegram_chat_id_entry.insert(0, self.settings.telegram.get('chat_id', ''))

        # Ollama
        self.ollama_url_entry.insert(0, self.settings.ollama.get('base_url', ''))
        self.ollama_model_entry.insert(0, self.settings.ollama.get('model', ''))

        # Риск-менеджмент
        risk_settings = self.settings.risk_management
        self.risk_per_trade_spin.set(risk_settings.get('risk_per_trade', 1.0))
        self.risk_all_trades_spin.set(risk_settings.get('risk_all_trades', 5.0))
        self.daily_risk_spin.set(risk_settings.get('daily_risk', 10.0))

        # Обновляем менеджер рисков
        self.risk_manager.update_settings(
            float(self.risk_per_trade_spin.get()),
            float(self.risk_all_trades_spin.get()),
            float(self.daily_risk_spin.get())
        )

    def _save_settings(self):
        """Сохранение настроек из интерфейса"""
        # MT5
        self.settings._settings['mt5'] = {
            'login': self.login_entry.get(),
            'password': self.password_entry.get(),
            'server': self.server_entry.get(),
            'path': self.path_entry.get()
        }

        # Telegram
        self.settings._settings['telegram'] = {
            'token': self.telegram_token_entry.get(),
            'chat_id': self.telegram_chat_id_entry.get()
        }

        # Ollama
        self.settings._settings['ollama'] = {
            'base_url': self.ollama_url_entry.get(),
            'model': self.ollama_model_entry.get()
        }

        # Риск-менеджмент
        self.settings._settings['risk_management'] = {
            'risk_per_trade': float(self.risk_per_trade_spin.get()),
            'risk_all_trades': float(self.risk_all_trades_spin.get()),
            'daily_risk': float(self.daily_risk_spin.get())
        }

        self.settings.save()
        self.logger.info("Настройки сохранены")

    def _browse_mt5_path(self):
        """Выбор пути к MT5"""
        path = filedialog.askopenfilename(
            title="Выберите исполняемый файл MT5",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)

    def _connect_mt5(self):
        """Подключение к MT5"""
        login = self.login_entry.get()
        password = self.password_entry.get()
        server = self.server_entry.get()
        path = self.path_entry.get()

        if not all([login, password, server, path]):
            messagebox.showerror("Ошибка", "Заполните все поля для подключения к MT5")
            return

        if self.mt5_client.connect(login, password, server, path):
            messagebox.showinfo("Успех", "Успешное подключение к MT5")
            self._save_settings()
        else:
            messagebox.showerror("Ошибка", "Не удалось подключиться к MT5")

    def _update_accounts_dropdown(self):
        """Обновляет список аккаунтов в выпадающем меню"""
        accounts = self.settings.accounts
        self.account_combobox["values"] = [
            f"{acc['login']}@{acc['server']}" for acc in accounts
        ]
        if accounts:
            self.account_combobox.current(self.settings.current_account_index)

    def _on_account_select(self, event=None):
        """Загружает данные выбранного аккаунта в форму"""
        idx = self.account_combobox.current()
        if idx >= 0:
            account = self.settings.accounts[idx]
            self.login_entry.delete(0, tk.END)
            self.login_entry.insert(0, account["login"])
            self.password_entry.delete(0, tk.END)
            self.password_entry.insert(0, account["password"])
            self.server_entry.delete(0, tk.END)
            self.server_entry.insert(0, account["server"])
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, account["path"])
            self.settings.set_current_account(idx)

    def _add_account(self):
        """Добавляет новый аккаунт в список"""
        login = self.login_entry.get()
        password = self.password_entry.get()
        server = self.server_entry.get()
        path = self.path_entry.get()

        if not all([login, password, server, path]):
            messagebox.showerror("Ошибка", "Заполните все поля")
            return

        self.settings.add_account(login, password, server, path)
        self._update_accounts_dropdown()
        messagebox.showinfo("Успех", "Аккаунт сохранен")

    def _remove_account(self):
        """Удаляет выбранный аккаунт"""
        idx = self.account_combobox.current()
        if idx >= 0:
            self.settings._settings["accounts"].pop(idx)
            self.settings.save()
            self._update_accounts_dropdown()
            self._clear_account_fields()
            messagebox.showinfo("Успех", "Аккаунт удален")

    def _clear_account_fields(self):
        """Очищает поля ввода аккаунта"""
        for entry in [self.login_entry, self.password_entry, self.server_entry, self.path_entry]:
            entry.delete(0, tk.END)

    def _load_settings(self):
        """Загружает настройки в интерфейс (обновленная версия)"""
        # Загружаем текущий аккаунт
        current = self.settings.current_account
        self.login_entry.insert(0, current.get("login", ""))
        self.password_entry.insert(0, current.get("password", ""))
        self.server_entry.insert(0, current.get("server", ""))
        self.path_entry.insert(0, current.get("path", ""))

        # Обновляем выпадающий список
        self._update_accounts_dropdown()

        # Остальные настройки (Telegram, Ollama и т.д.)
        self.telegram_token_entry.insert(0, self.settings.telegram.get("token", ""))

    def _test_telegram(self):
        """Тестовая отправка уведомления в Telegram"""
        token = self.telegram_token_entry.get()
        chat_id = self.telegram_chat_id_entry.get()

        if not token or not chat_id:
            messagebox.showerror("Ошибка", "Заполните токен и chat_id для Telegram")
            return

        self.telegram_bot = TelegramBot(token, chat_id, self.logger)
        if self.telegram_bot.send_message("Тестовое уведомление от Trading Assistant"):
            messagebox.showinfo("Успех", "Тестовое уведомление отправлено")
            self._save_settings()
        else:
            messagebox.showerror("Ошибка", "Не удалось отправить уведомление")

    def _load_knowledge_base(self):
        """Загрузка базы знаний"""
        files = filedialog.askopenfilenames(
            title="Выберите файлы базы знаний",
            filetypes=[("Text files", "*.txt"), ("PDF files", "*.pdf"), ("All files", "*.*")]
        )

        if not files:
            return

        ollama_url = self.ollama_url_entry.get()
        ollama_model = self.ollama_model_entry.get()

        if not ollama_url or not ollama_model:
            messagebox.showerror("Ошибка", "Заполните URL и модель Ollama")
            return

        self.ollama = OllamaIntegration(ollama_url, ollama_model, self.logger)

        success_count = 0
        for file_path in files:
            if self.ollama.load_knowledge(file_path):
                success_count += 1

        messagebox.showinfo("Результат", f"Успешно загружено {success_count} из {len(files)} файлов")
        self._save_settings()

    def _update_risk_settings(self):
        """Обновление параметров риск-менеджмента"""
        try:
            risk_per_trade = float(self.risk_per_trade_spin.get())
            risk_all_trades = float(self.risk_all_trades_spin.get())
            daily_risk = float(self.daily_risk_spin.get())

            if not (0 < risk_per_trade <= 100 and 0 < risk_all_trades <= 100 and 0 < daily_risk <= 100):
                raise ValueError("Значения риска должны быть между 0 и 100")

            self.risk_manager.update_settings(risk_per_trade, risk_all_trades, daily_risk)
            self._save_settings()
            messagebox.showinfo("Успех", "Параметры риска обновлены")
        except ValueError as e:
            messagebox.showerror("Ошибка", str(e))

    def _toggle_strategy(self, name: str, var: tk.BooleanVar):
        """Включение/выключение стратегии"""
        strategy = self.strategies[name]
        if var.get():
            strategy.enable()
        else:
            strategy.disable()

    def _start_trading(self):
        """Запуск торгового ассистента"""
        if not self.mt5_client.connected:
            messagebox.showerror("Ошибка", "Сначала подключитесь к MT5")
            return

        # Проверяем, что хотя бы одна стратегия активна
        active_strategies = [name for name, var in self.strategy_vars.items() if var.get()]
        if not active_strategies:
            messagebox.showerror("Ошибка", "Выберите хотя бы одну стратегию")
            return

        # Инициализируем Telegram бота, если заданы настройки
        token = self.telegram_token_entry.get()
        chat_id = self.telegram_chat_id_entry.get()
        if token and chat_id:
            self.telegram_bot = TelegramBot(token, chat_id, self.logger)

        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        self.logger.info("Торговый ассистент запущен")
        if self.telegram_bot:
            self.telegram_bot.send_message("🟢 Торговый ассистент запущен")

        # Запускаем цикл обновления
        self._update_trading()

    def _stop_trading(self):
        """Остановка торгового ассистента"""
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

        self.logger.info("Торговый ассистент остановлен")
        if self.telegram_bot:
            self.telegram_bot.send_message("🔴 Торговый ассистент остановлен")

    def _update_trading(self):
        """Основной цикл торговли"""
        if not self.is_running:
            return

        try:
            # Получаем информацию о счете
            account_info = self.mt5_client.get_account_info()
            if not account_info:
                self.logger.error("Не удалось получить информацию о счете")
                return

            # Проверяем дневные лимиты
            if not self.risk_manager.check_daily_limits():
                self._stop_trading()
                return

            # Анализируем рынок для каждой стратегии
            for name, strategy in self.strategies.items():
                if not strategy.enabled:
                    continue

                # Здесь должна быть логика анализа и торговли для каждой стратегии
                # В реальном приложении это будет более сложный код
                self.logger.info(f"Анализ по стратегии {name}")

                # Пример: анализ одного символа
                symbol = "EURUSD"
                timeframe = Timeframes.H1
                data = self.mt5_client.get_historical_data(symbol, timeframe, 100)

                if data is not None:
                    signal = strategy.analyze(symbol, timeframe, data)
                    if signal:
                        self._process_signal(signal, name)

        except Exception as e:
            self.logger.error(f"Ошибка в цикле торговли: {str(e)}")
            if self.telegram_bot:
                self.telegram_bot.notify_error(f"Ошибка в цикле торговли: {str(e)}")
        finally:
            if self.is_running:
                self.root.after(self.update_interval, self._update_trading)

    def _process_signal(self, signal: Dict, strategy_name: str):
        """Обработка торгового сигнала"""
        symbol = signal['symbol']
        action = signal['action']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']

        # Рассчитываем объем позиции на основе риска
        price = signal['price']
        stop_loss_pips = abs(price - stop_loss) / self.mt5_client.get_symbol_info(symbol).point

        volume = self.risk_manager.calculate_position_size(symbol, stop_loss_pips)
        if not volume:
            return

        # Проверяем общий риск
        if not self.risk_manager.check_all_trades_risk():
            return

        # Размещаем ордер
        order_id = self.mt5_client.place_order(
            symbol=symbol,
            action=action,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
            comment=f"Strategy: {strategy_name}"
        )

        if order_id and self.telegram_bot:
            self.telegram_bot.notify_trade_opened(
                symbol=symbol,
                action=action,
                volume=volume,
                price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                strategy=strategy_name
            )