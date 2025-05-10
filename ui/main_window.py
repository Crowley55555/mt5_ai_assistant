import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from config.settings import Settings
from utils.logger import TradingLogger
from core.mt5_client import MT5Client
from core.risk_manager import RiskManager
from core.telegram_bot import TelegramBot
from core.ollama_integration import OllamaIntegration
from core.strategies import SniperStrategy, SmartSniperStrategy, SmartMoneyStrategy
from config.constants import Timeframes



class TradingAssistantApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AI Trading Assistant for MT5")
        self.root.geometry("1000x700")

        # Инициализация компонентов
        self._app_logger = TradingLogger(log_file="logs/trading_assistant.log")
        self.settings = Settings(config_path="config/config.json", logger=self._app_logger)
        self.logger = self._app_logger.logger  # Получаем корневой логгер
        self.mt5_client = MT5Client(self._app_logger)
        self.risk_manager = RiskManager(self.mt5_client, self._app_logger.logger)
        self.telegram_bot = None
        self.ollama = None


        # Стратегии
        self.strategies = {
            "Снайпер": SniperStrategy("Снайпер", self.mt5_client, self._app_logger.logger),
            "Смарт Снайпер": SmartSniperStrategy("Смарт Снайпер", self.mt5_client, self._app_logger.logger),
            "Смарт Мани": SmartMoneyStrategy("Смарт Мани", self.mt5_client, self._app_logger.logger)
        }

        # Атрибуты для виджетов
        self.is_running = False
        self.update_interval = 5000  # Интервал обновления в миллисекундах
        self.account_combobox = None
        self.login_entry = None
        self.password_entry = None
        self.server_entry = None
        self.path_entry = None
        self.telegram_token_entry = None
        self.chat_id_entry = None
        self.ollama_url_entry = None
        self.ollama_model_entry = None
        self.risk_per_trade_spin = None
        self.risk_all_trades_spin = None
        self.daily_risk_spin = None
        self.strategy_vars = {}

        # Создание интерфейса
        self._create_widgets()
        self._load_settings()

    def _create_widgets(self):
        """Создание всех элементов интерфейса"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)

        left_panel = ttk.Frame(main_frame, width=300, padding="10")
        left_panel.pack(side="left", fill="y")

        right_panel = ttk.Frame(main_frame, padding="10")
        right_panel.pack(side="right", fill="both", expand=True)

        # Управление аккаунтами
        self._setup_account_ui(left_panel)

        # Telegram уведомления
        self._setup_telegram_ui(left_panel)

        # Интеграция с Ollama
        self._setup_ollama_ui(left_panel)

        # Риск-менеджмент
        self._setup_risk_management_ui(left_panel)

        # Управление стратегиями
        self._setup_strategy_control_ui(left_panel)

        # Кнопки управления
        self._setup_control_buttons(left_panel)

        # Логирование
        self._setup_log_viewer(right_panel)

    def _setup_account_ui(self, parent_frame):
        """Настройка UI компонентов для управления аккаунтами"""
        self.account_frame = ttk.LabelFrame(parent_frame, text="Управление аккаунтами MT5", padding="10")
        self.account_frame.pack(fill="x", pady=5)

        ttk.Label(self.account_frame, text="Аккаунт:").grid(row=0, column=0, sticky=tk.W)
        self.account_combobox = ttk.Combobox(self.account_frame, state="readonly")
        self.account_combobox.grid(row=0, column=1, sticky=tk.EW, padx=5)
        self.account_combobox.bind("<<ComboboxSelected>>", self._on_account_select)

        fields = [
            ("Логин:", "login_entry", ""),
            ("Пароль:", "password_entry", "*"),
            ("Сервер:", "server_entry", ""),
            ("Путь к MT5:", "path_entry", "")
        ]

        for i, (label, attr_name, show_char) in enumerate(fields, start=1):
            ttk.Label(self.account_frame, text=label).grid(row=i, column=0, sticky=tk.W)
            entry = ttk.Entry(self.account_frame, show=show_char)
            entry.grid(row=i, column=1, sticky=tk.EW, padx=5)
            setattr(self, attr_name, entry)

            if label == "Путь к MT5:":
                ttk.Button(self.account_frame, text="Обзор", command=self._browse_mt5_path).grid(
                    row=i, column=2, padx=5
                )

        btn_frame = ttk.Frame(self.account_frame)
        btn_frame.grid(row=len(fields) + 1, column=0, columnspan=3, pady=(5, 0))

        buttons = [
            ("Добавить аккаунт", self._add_account),
            ("Удалить аккаунт", self._remove_account),
            ("Подключиться", self._connect_mt5)
        ]

        for text, command in buttons:
            ttk.Button(btn_frame, text=text, command=command).pack(
                side="left" if text != "Подключиться" else tk.RIGHT, padx=2
            )

    def _setup_telegram_ui(self, parent_frame):
        """Создание интерфейса Telegram бота"""
        telegram_frame = ttk.LabelFrame(parent_frame, text="Telegram уведомления", padding="10")
        telegram_frame.pack(fill="x", pady=5)

        ttk.Label(telegram_frame, text="Токен бота:").grid(row=0, column=0, sticky=tk.W)
        self.telegram_token_entry = ttk.Entry(telegram_frame)
        self.telegram_token_entry.grid(row=0, column=1, sticky=tk.EW, padx=5)

        ttk.Label(telegram_frame, text="Chat ID:").grid(row=1, column=0, sticky=tk.W)
        self.chat_id_entry = ttk.Entry(telegram_frame)
        self.chat_id_entry.grid(row=1, column=1, sticky=tk.EW, padx=5)

        ttk.Button(telegram_frame, text="Тест уведомления", command=self._test_telegram).grid(
            row=2, column=0, columnspan=2, pady=5
        )

    def _setup_ollama_ui(self, parent_frame):
        """Создание интерфейса Ollama интеграции"""
        ollama_frame = ttk.LabelFrame(parent_frame, text="Ollama интеграция", padding="10")
        ollama_frame.pack(fill="x", pady=5)

        ttk.Label(ollama_frame, text="URL сервера:").grid(row=0, column=0, sticky=tk.W)
        self.ollama_url_entry = ttk.Entry(ollama_frame)
        self.ollama_url_entry.grid(row=0, column=1, sticky=tk.EW, padx=5)

        ttk.Label(ollama_frame, text="Модель:").grid(row=1, column=0, sticky=tk.W)
        self.ollama_model_entry = ttk.Entry(ollama_frame)
        self.ollama_model_entry.grid(row=1, column=1, sticky=tk.EW, padx=5)

        ttk.Button(ollama_frame, text="Загрузить базу знаний", command=self._load_knowledge_base).grid(
            row=2, column=0, columnspan=2, pady=5
        )

    def _setup_risk_management_ui(self, parent_frame):
        """Создание интерфейса управления рисками"""
        risk_frame = ttk.LabelFrame(parent_frame, text="Управление рисками", padding="10")
        risk_frame.pack(fill="x", pady=5)

        ttk.Label(risk_frame, text="Риск на сделку (%):").grid(row=0, column=0, sticky=tk.W)
        self.risk_per_trade_spin = ttk.Spinbox(risk_frame, from_=0.1, to=10, increment=0.1)
        self.risk_per_trade_spin.grid(row=0, column=1, sticky=tk.EW, padx=5)

        ttk.Label(risk_frame, text="Риск на все сделки (%):").grid(row=1, column=0, sticky=tk.W)
        self.risk_all_trades_spin = ttk.Spinbox(risk_frame, from_=1, to=50, increment=1)
        self.risk_all_trades_spin.grid(row=1, column=1, sticky=tk.EW, padx=5)

        ttk.Label(risk_frame, text="Дневной риск (%):").grid(row=2, column=0, sticky=tk.W)
        self.daily_risk_spin = ttk.Spinbox(risk_frame, from_=1, to=100, increment=1)
        self.daily_risk_spin.grid(row=2, column=1, sticky=tk.EW, padx=5)

        ttk.Button(risk_frame, text="Применить", command=self._update_risk_settings).grid(
            row=3, column=0, columnspan=2, pady=5
        )

    def _setup_strategy_control_ui(self, parent_frame):
        """Создание интерфейса управления стратегиями"""
        strategies_frame = ttk.LabelFrame(parent_frame, text="Торговые стратегии", padding="10")
        strategies_frame.pack(fill="x", pady=5)

        self.strategy_vars = {}
        for i, (name, strategy) in enumerate(self.strategies.items()):
            var = tk.BooleanVar(value=strategy.enabled)
            chk = ttk.Checkbutton(strategies_frame, text=name, variable=var,
                                  command=lambda n=name, v=var: self._toggle_strategy(n, v))
            chk.grid(row=i, column=0, sticky=tk.W)
            self.strategy_vars[name] = var

    def _setup_control_buttons(self, parent_frame):
        """Создание кнопок управления"""
        control_frame = ttk.Frame(parent_frame, padding="10")
        control_frame.pack(fill="x", pady=5)

        stats_btn = ttk.Button(control_frame, text="Статистика", command=self._show_trade_statistics)
        stats_btn.pack(side="left", padx=5)

        self.start_btn = ttk.Button(control_frame, text="Старт", command=self._start_trading)
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = ttk.Button(control_frame, text="Стоп", command=self._stop_trading, state=tk.DISABLED)
        self.stop_btn.pack(side="left", padx=5)

    def _setup_log_viewer(self, parent_frame):
        """Создание текстового поля лога"""
        log_frame = ttk.LabelFrame(parent_frame, text="Лог", padding="10")
        log_frame.pack(fill="both", expand=True)

        self.log_text = tk.Text(log_frame, wrap="word", state="disabled")
        self.log_text.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)

    def _connect_mt5(self):
        """Подключение к MT5"""
        login = self.login_entry.get().strip()
        password = self.password_entry.get().strip()
        server = self.server_entry.get().strip()
        path = self.path_entry.get().strip()

        if not all([login, password, server, path]):
            self.logger.warning("Попытка подключения с неполными данными")
            messagebox.showerror("Ошибка", "Заполните все поля подключения к MT5")
            return

        if not login.isdigit():
            self.logger.error("Логин должен быть числом")
            messagebox.showerror("Ошибка", "Логин должен быть числом")
            return

        try:
            connected = self.mt5_client.connect(login, password, server, path)
            if connected:
                messagebox.showinfo("Успех", "Подключение к MT5 установлено")
                self._save_settings()
            else:
                error_msg = self.mt5_client.last_error() if hasattr(self.mt5_client, 'last_error') else "Неизвестная ошибка"
                messagebox.showerror("Ошибка", f"Не удалось подключиться: {error_msg}")
        except Exception as e:
            self.logger.error(f"Критическая ошибка при подключении: {str(e)}")
            messagebox.showerror("Ошибка", f"Системная ошибка: {str(e)}")

    def _update_accounts_dropdown(self):
        """Обновление выпадающего списка аккаунтов"""
        accounts = self.settings.accounts
        values = [f"{acc['login']}@{acc['server']}" for acc in accounts]
        self.account_combobox["values"] = values
        if accounts:
            self.account_combobox.current(self.settings.current_account_index)
            self.logger.info("Список аккаунтов обновлен")

    def _on_account_select(self, _=None):
        """Обработчик выбора аккаунта"""
        try:
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
                self.logger.info(f"Выбран аккаунт: {account['login']}")
        except Exception as e:
            self.logger.error(f"Ошибка выбора аккаунта: {str(e)}")

    def _add_account(self):
        """Добавление нового аккаунта"""
        account_data = {
            "login": self.login_entry.get(),
            "password": self.password_entry.get(),
            "server": self.server_entry.get(),
            "path": self.path_entry.get()
        }
        if not all(account_data.values()):
            self.logger.warning("Попытка добавить аккаунт с незаполненными данными")
            messagebox.showerror("Ошибка", "Заполните все поля аккаунта")
            return

        if self.settings.add_account(**account_data):
            self._update_accounts_dropdown()
            messagebox.showinfo("Успех", "Аккаунт сохранен")
            self.logger.info(f"Добавлен новый аккаунт: {account_data['login']}")
        else:
            messagebox.showerror("Ошибка", "Не удалось сохранить аккаунт")

    def _save_settings(self):
        """Сохранение настроек из интерфейса"""
        current_account = {
            'login': self.login_entry.get(),
            'password': self.password_entry.get(),
            'server': self.server_entry.get(),
            'path': self.path_entry.get()
        }

        # Сохраняем MT5 аккаунт
        self.settings.mt5 = current_account  # <-- через свойство mt5
        self.settings.telegram = {
            'token': self.telegram_token_entry.get().strip(),
            'chat_id': self.chat_id_entry.get().strip()
        }
        self.settings.ollama = {
            'base_url': self.ollama_url_entry.get(),
            'model': self.ollama_model_entry.get()
        }
        self.settings.risk_management = {
            'risk_per_trade': float(self.risk_per_trade_spin.get()),
            'risk_all_trades': float(self.risk_all_trades_spin.get()),
            'daily_risk': float(self.daily_risk_spin.get())
        }

        try:
            self.settings.save()
            self.logger.info("Настройки успешно сохранены")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения настроек: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки: {str(e)}")

    def _load_settings(self):
        """Загрузка настроек в интерфейс"""
        # MT5
        mt5_acc = self.settings.current_account
        self.login_entry.delete(0, tk.END)
        self.login_entry.insert(0, mt5_acc.get('login', ''))
        self.password_entry.delete(0, tk.END)
        self.password_entry.insert(0, mt5_acc.get('password', ''))
        self.server_entry.delete(0, tk.END)
        self.server_entry.insert(0, mt5_acc.get('server', ''))
        self.path_entry.delete(0, tk.END)
        self.path_entry.insert(0, mt5_acc.get('path', ''))

        # Telegram
        telegram = self.settings.telegram or {}
        self.telegram_token_entry.delete(0, tk.END)
        self.telegram_token_entry.insert(0, telegram.get('token', ''))
        self.chat_id_entry.delete(0, tk.END)
        self.chat_id_entry.insert(0, telegram.get('chat_id', ''))

        # Ollama
        ollama = self.settings.ollama or {}
        self.ollama_url_entry.delete(0, tk.END)
        self.ollama_url_entry.insert(0, ollama.get('base_url', ''))
        self.ollama_model_entry.delete(0, tk.END)
        self.ollama_model_entry.insert(0, ollama.get('model', ''))

        # Риски
        risk = self.settings.risk_management or {}
        self.risk_per_trade_spin.set(risk.get('risk_per_trade', 1.0))
        self.risk_all_trades_spin.set(risk.get('risk_all_trades', 5.0))
        self.daily_risk_spin.set(risk.get('daily_risk', 10.0))

        # Обновляем менеджер рисков
        try:
            self.risk_manager.update_settings(
                float(self.risk_per_trade_spin.get()),
                float(self.risk_all_trades_spin.get()),
                float(self.daily_risk_spin.get())
            )
        except ValueError as e:
            self.logger.warning(f"Некорректные параметры риска при загрузке: {str(e)}")

    def _test_telegram(self):
        """Тестовая отправка уведомления в Telegram"""
        token = self.telegram_token_entry.get().strip()
        chat_id = self.chat_id_entry.get().strip()
        if not token or not chat_id:
            messagebox.showerror("Ошибка", "Заполните токен и chat_id для Telegram")
            return

        try:
            bot = TelegramBot(self._app_logger)
            bot.initialize(token, chat_id)
            if bot.send_message("Тестовое уведомление от Trading Assistant"):
                messagebox.showinfo("Успех", "Тестовое уведомление отправлено")
                self.settings.telegram = {
                    'token': self.telegram_token_entry.get(),
                    'chat_id': self.chat_id_entry.get()
                }
                self.settings.save()
            else:
                messagebox.showerror("Ошибка", "Не удалось отправить тестовое сообщение")
        except Exception as e:
            self.logger.error(f"Ошибка тестирования Telegram: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось подключить Telegram: {str(e)}")

    def _load_knowledge_base(self):
        """Загрузка базы знаний для Ollama"""
        files = filedialog.askopenfilenames(
            title="Выберите файлы базы знаний",
            filetypes=[("Text files", "*.txt"), ("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if not files:
            return

        ollama_url = self.ollama_url_entry.get().strip()
        ollama_model = self.ollama_model_entry.get().strip()

        if not ollama_url or not ollama_model:
            messagebox.showerror("Ошибка", "Заполните URL и модель Ollama")
            return

        try:
            if not self.ollama or self.ollama.base_url != ollama_url or self.ollama.model != ollama_model:
                self.ollama = OllamaIntegration(ollama_url, ollama_model, self._app_logger)

            success_count = 0
            for file_path in files:
                if self.ollama.load_knowledge(file_path):
                    success_count += 1

            messagebox.showinfo("Результат", f"Загружено {success_count} из {len(files)} файлов")
            self.settings.ollama = {
                'base_url': ollama_url,
                'model': ollama_model
            }
            self.settings.save()
        except Exception as e:
            self.logger.error(f"Ошибка загрузки базы знаний: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось загрузить файлы: {str(e)}")

    def _update_risk_settings(self):
        """Обновление параметров риск-менеджмента"""
        try:
            risk_per_trade = float(self.risk_per_trade_spin.get())
            risk_all_trades = float(self.risk_all_trades_spin.get())
            daily_risk = float(self.daily_risk_spin.get())

            if not (0 < risk_per_trade <= 100 and 0 < risk_all_trades <= 100 and 0 < daily_risk <= 100):
                raise ValueError("Все значения риска должны быть между 0 и 100")

            self.risk_manager.update_settings(risk_per_trade, risk_all_trades, daily_risk)
            self._save_settings()
            messagebox.showinfo("Успех", "Настройки риск-менеджмента обновлены")
        except ValueError as e:
            self.logger.error(f"Ошибка валидации рисков: {str(e)}")
            messagebox.showerror("Ошибка", f"Некорректные значения рисков: {str(e)}")

    def _toggle_strategy(self, name: str, var: tk.BooleanVar):
        """Включение/выключение стратегии"""
        strategy = self.strategies[name]
        if var.get():
            strategy.enable()
        else:
            strategy.disable()
        self.logger.info(f"Стратегия '{name}' {'активирована' if var.get() else 'деактивирована'}")

    def _start_trading(self):
        """Запуск торговой системы"""
        if not self.mt5_client.connected:
            messagebox.showerror("Ошибка", "Сначала подключитесь к MT5")
            return

        active_strategies = [name for name, var in self.strategy_vars.items() if var.get()]
        if not active_strategies:
            messagebox.showerror("Ошибка", "Выберите хотя бы одну стратегию")
            return

        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.logger.info("Торговый ассистент запущен")

        if self.telegram_bot:
            self.telegram_bot.send_message("🟢 Торговый ассистент запущен")

        self._update_trading()

    def _stop_trading(self):
        """Остановка торговой системы"""
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.logger.info("Торговый ассистент остановлен")

        if self.telegram_bot:
            self.telegram_bot.send_message("🔴 Торговый ассистент остановлен")

    def _update_trading(self):
        """Основной цикл обновления анализа"""
        if not self.is_running:
            return

        try:
            account_info = self.mt5_client.get_account_info()
            if not account_info:
                self.logger.error("Не удалось получить информацию о счете")
                return

            if not self.risk_manager.check_daily_limits():
                self._stop_trading()
                return

            for name, strategy in self.strategies.items():
                if not strategy.enabled:
                    continue

                data = self.mt5_client.get_historical_data("EURUSD", Timeframes.H1, 100)
                if data is None:
                    self.logger.warning("Нет исторических данных для анализа")
                    continue

                signal = strategy.analyze("EURUSD", Timeframes.H1, data)
                if signal:
                    self._process_signal(signal, name)

        except Exception as e:
            self.logger.error(f"Ошибка в торговом цикле: {str(e)}")
            if self.telegram_bot:
                self.telegram_bot.notify_error(f"Ошибка в торговом цикле: {str(e)}")

        finally:
            if self.is_running:
                self._update_trading()

    def _process_signal(self, signal: dict, strategy_name: str):
        """Обработка торгового сигнала"""
        symbol = signal.get('symbol')
        action = signal.get('action')
        price = signal.get('price')
        stop_loss = signal.get('stop_loss')
        take_profit = signal.get('take_profit')

        if not all([symbol, action, price, stop_loss, take_profit]):
            self.logger.warning("Получен некорректный сигнал от стратегии")
            return

        # Получаем информацию о символе
        symbol_info = self.mt5_client.get_symbol_info(symbol)
        if symbol_info is None or not isinstance(symbol_info, dict):
            self.logger.error(f"Не удалось получить данные по символу {symbol}")
            return

        # Расчет стоп-лосса в пунктах
        stop_loss_pips = abs(price - stop_loss) / symbol_info['point']

        # Проверка размера позиции
        volume = self.risk_manager.calculate_position_size(symbol, stop_loss_pips)
        if not volume:
            self.logger.debug(f"Риск для {symbol} слишком высок — сделка не размещена")
            return

        # Проверка общего риска
        if not self.risk_manager.check_all_trades_risk(volume * 2):  # Упрощенная проверка
            self.logger.debug("Превышен общий риск — сделка не размещена")
            return

        order_id = self.mt5_client.place_order(
            symbol=symbol,
            action=action,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
            comment=f"Стратегия: {strategy_name}"
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

    def _browse_mt5_path(self):
        """Выбор пути к MT5"""
        path = filedialog.askopenfilename(
            title="Выберите terminal.exe",
            filetypes=[("Исполняемые файлы", "*.exe"), ("Все файлы", "*.*")]
        )
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)

    def _show_trade_statistics(self):
        """Отображение статистики сделок"""
        if not self.risk_manager:
            messagebox.showerror("Ошибка", "Менеджер рисков не инициализирован")
            return

        stats = self.risk_manager.get_trade_statistics()
        message = (
            f"📊 Отчет за сегодня\n"
            f"Сделок: {stats['total_trades']}\n"
            f"Процент успешных: {stats['win_rate']:.1%}\n"
            f"Средняя прибыль: {stats['avg_profit']:.2f}"
        )
        messagebox.showinfo("Статистика", message)

    def _remove_account(self):
        """Удаление аккаунта"""
        idx = self.account_combobox.current()
        if idx >= 0:
            account = self.settings.accounts[idx]
            confirm = messagebox.askyesno("Подтверждение", f"Удалить аккаунт {account['login']}?")
            if confirm:
                self.settings.remove_account(idx)
                self._update_accounts_dropdown()
                self._clear_account_fields()
                messagebox.showinfo("Успех", "Аккаунт удален")
                self.logger.info(f"Аккаунт {account['login']} удален")

    def _clear_account_fields(self):
        """Очистка полей формы аккаунта"""
        self.login_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        self.server_entry.delete(0, tk.END)
        self.path_entry.delete(0, tk.END)

    # def _load_settings(self):
    #     """Загрузка настроек в интерфейс"""
    #     current = self.settings.current_account
    #     self.login_entry.delete(0, tk.END)
    #     self.login_entry.insert(0, current.get('login', ''))
    #     self.password_entry.delete(0, tk.END)
    #     self.password_entry.insert(0, current.get('password', ''))
    #     self.server_entry.delete(0, tk.END)
    #     self.server_entry.insert(0, current.get('server', ''))
    #     self.path_entry.delete(0, tk.END)
    #     self.path_entry.insert(0, current.get('path', ''))
    #
    #     # Telegram
    #     self.telegram_token_entry.delete(0, tk.END)
    #     self.telegram_token_entry.insert(0, self.settings.telegram.get('token', ''))
    #     self.chat_id_entry.delete(0, tk.END)
    #     self.chat_id_entry.insert(0, self.settings.telegram.get('chat_id', ''))
    #
    #     # Ollama
    #     self.ollama_url_entry.delete(0, tk.END)
    #     self.ollama_url_entry.insert(0, self.settings.ollama.get('base_url', ''))
    #     self.ollama_model_entry.delete(0, tk.END)
    #     self.ollama_model_entry.insert(0, self.settings.ollama.get('model', ''))
    #
    #     # Риски
    #     risk_settings = self.settings.risk_management
    #     self.risk_per_trade_spin.set(risk_settings.get('risk_per_trade', 1.0))
    #     self.risk_all_trades_spin.set(risk_settings.get('risk_all_trades', 5.0))
    #     self.daily_risk_spin.set(risk_settings.get('daily_risk', 10.0))
    #     self.logger.debug("Настройки загружены в интерфейс")
    #
    # def _save_settings(self):
    #     """Сохранение настроек из интерфейса"""
    #     # Сохраняем MT5 аккаунт
    #     current_account = {
    #         'login': self.login_entry.get(),
    #         'password': self.password_entry.get(),
    #         'server': self.server_entry.get(),
    #         'path': self.path_entry.get()
    #     }
    #
    #     if current_account['login']:
    #         if not any(acc['login'] == current_account['login'] for acc in self.settings.accounts):
    #             self.settings.accounts.append(current_account)
    #         else:
    #             self.settings.accounts[self.settings.current_account_index] = current_account
    #
    #     # Сохраняем Telegram
    #     self.settings.telegram = {
    #         'token': self.telegram_token_entry.get(),
    #         'chat_id': self.chat_id_entry.get()
    #     }
    #
    #     # Сохраняем Ollama
    #     self.settings.ollama = {
    #         'base_url': self.ollama_url_entry.get(),
    #         'model': self.ollama_model_entry.get()
    #     }
    #
    #     # Сохраняем риск-параметры
    #     self.settings.risk_management = {
    #         'risk_per_trade': float(self.risk_per_trade_spin.get()),
    #         'risk_all_trades': float(self.risk_all_trades_spin.get()),
    #         'daily_risk': float(self.daily_risk_spin.get())
    #     }
    #
    #     self.settings.save()
    #     self.logger.info("Настройки сохранены")
    #
    # def _update_risk_settings(self):
    #     """Обновление параметров риск-менеджмента"""
    #     try:
    #         risk_per_trade = float(self.risk_per_trade_spin.get())
    #         risk_all_trades = float(self.risk_all_trades_spin.get())
    #         daily_risk = float(self.daily_risk_spin.get())
    #
    #         if not (0.1 <= risk_per_trade <= 5.0):
    #             raise ValueError("Риск на сделку должен быть между 0.1 и 5.0")
    #         if not (risk_per_trade <= risk_all_trades <= 20.0):
    #             raise ValueError("Риск на все сделки должен быть >= риска на сделку и <= 20.0")
    #         if not (risk_all_trades <= daily_risk <= 50.0):
    #             raise ValueError("Дневной риск должен быть >= общего риска и <= 50.0")
    #
    #         self.risk_manager.update_settings(risk_per_trade, risk_all_trades, daily_risk)
    #         self._save_settings()
    #         messagebox.showinfo("Успех", "Параметры риск-менеджмента обновлены")
    #     except ValueError as e:
    #         messagebox.showerror("Ошибка", str(e))
    #
    # def _test_telegram(self):
    #     """Тестовая отправка через Telegram"""
    #     token = self.telegram_token_entry.get()
    #     chat_id = self.chat_id_entry.get()
    #     if not token or not chat_id:
    #         messagebox.showerror("Ошибка", "Заполните токен и chat_id для Telegram")
    #         return
    #
    #     if self.telegram_bot is None or not self.telegram_bot.enabled:
    #         self.telegram_bot = TelegramBot(self._app_logger)
    #         self.telegram_bot.initialize(token, chat_id)
    #     else:
    #         self.telegram_bot.initialize(token, chat_id)
    #
    #     if self.telegram_bot.send_message("Тестовое уведомление от Trading Assistant"):
    #         messagebox.showinfo("Успех", "Тестовое уведомление отправлено")
    #         self._save_settings()
    #     else:
    #         messagebox.showerror("Ошибка", "Не удалось отправить тестовое уведомление")
    #
    # def _load_knowledge_base(self):
    #     """Загрузка базы знаний для Ollama"""
    #     files = filedialog.askopenfilenames(
    #         title="Выберите файлы базы знаний",
    #         filetypes=[("Text files", "*.txt"), ("PDF files", "*.pdf"), ("All files", "*.*")]
    #     )
    #     if not files:
    #         return
    #
    #     ollama_url = self.ollama_url_entry.get()
    #     ollama_model = self.ollama_model_entry.get()
    #     if not all([ollama_url, ollama_model]):
    #         messagebox.showerror("Ошибка", "Заполните URL и модель Ollama")
    #         return
    #
    #     if self.ollama is None or self.ollama.base_url != ollama_url or self.ollama.model != ollama_model:
    #         self.ollama = OllamaIntegration(ollama_url, ollama_model, self._app_logger)
    #
    #     success_count = 0
    #     for file_path in files:
    #         if self.ollama.load_knowledge(file_path):
    #             success_count += 1
    #
    #     messagebox.showinfo("Результат", f"Загружено {success_count} из {len(files)} файлов")
    #
    # def _start_trading(self):
    #     """Запуск торговой системы"""
    #     if not self.mt5_client.connected:
    #         messagebox.showerror("Ошибка", "Сначала подключитесь к MT5")
    #         return
    #
    #     active_strategies = [name for name, var in self.strategy_vars.items() if var.get()]
    #     if not active_strategies:
    #         messagebox.showerror("Ошибка", "Выберите хотя бы одну стратегию")
    #         return
    #
    #     self.is_running = True
    #     self.start_btn.config(state=tk.DISABLED)
    #     self.stop_btn.config(state=tk.NORMAL)
    #     self.logger.info("Торговый ассистент запущен")
    #     if self.telegram_bot:
    #         self.telegram_bot.send_message("🟢 Торговый ассистент запущен")
    #
    # def _stop_trading(self):
    #     """Остановка торговой системы"""
    #     self.is_running = False
    #     self.start_btn.config(state=tk.NORMAL)
    #     self.stop_btn.config(state=tk.DISABLED)
    #     self.logger.info("Торговый ассистент остановлен")
    #     if self.telegram_bot:
    #         self.telegram_bot.send_message("🔴 Торговый ассистент остановлен")
    #
    # def _update_trading(self):
    #     """Основной цикл обновления и анализа"""
    #     if not self.is_running:
    #         return
    #
    #     try:
    #         account_info = self.mt5_client.get_account_info()
    #         if not account_info:
    #             self.logger.warning("Не удалось получить информацию о счете")
    #             return
    #
    #         if self.daily_profit <= -self.daily_loss_limit:
    #             self.logger.warning(f"Достигнут дневной лимит убытков: {self.daily_profit}/{self.daily_loss_limit}")
    #             self._stop_trading()
    #             return
    #
    #         # Здесь должна быть более сложная логика анализа
    #         # Для примера используем простую проверку
    #         for name, strategy in self.strategies.items():
    #             if not strategy.enabled:
    #                 continue
    #             data = self.mt5_client.get_historical_data("EURUSD", Timeframes.H1, 100)
    #             if data is None:
    #                 self.logger.warning("Нет исторических данных для анализа")
    #                 continue
    #             signal = strategy.analyze("EURUSD", Timeframes.H1, data)
    #             if signal:
    #                 self._process_signal(signal, name)
    #
    #     except Exception as e:
    #         self.logger.error(f"Ошибка в торговом цикле: {str(e)}")
    #         if self.telegram_bot:
    #             self.telegram_bot.notify_error(f"Ошибка в торговом цикле: {str(e)}")
    #
    #     finally:
    #         if self.is_running:
    #             self.root.after(self.update_interval, self._update_trading)
    #