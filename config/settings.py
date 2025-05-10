import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from utils.logger import TradingLogger


def _log_error(self, message: str):
    """Логирование ошибок"""
    if self.logger:
        self.logger.error(message)

def set_logger(self, logger: TradingLogger):
    """Установка логгера после инициализации"""
    self._app_logger = logger
    self.logger = logger.logger

def _log_info(self, message: str):
    """Логирование информационных сообщений"""
    if self.logger:
        self.logger.info(message)

def _log_warning(self, message: str):
    """Логирование предупреждений"""
    if self.logger:
        self.logger.warning(message)

class Settings:
    def __init__(self, config_path: str = "config/config.json", logger: Optional[TradingLogger] = None):
        """
        Инициализация менеджера настроек

        :param config_path: Путь к файлу настроек
        :param logger: Объект логгера (опционально)
        """
        self.config_path = Path(config_path)
        self._settings = self._load_settings()
        self.current_account_index = self._settings.get("current_account_index", 0)

        # Сохраняем объект TradingLogger для последующего использования
        self._app_logger = logger  # Это объект TradingLogger
        self.logger = logger.logger  # Получаем корневой logging.Logger

    def _load_settings(self) -> Dict[str, Any]:
        """Загрузка настроек из файла"""
        try:
            if not self.config_path.exists():
                self._create_default_settings()

            with open(self.config_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                return self._migrate(loaded)

        except Exception as e:
            self._logger_error(f"Ошибка загрузки настроек: {str(e)}")
            return self._get_default_settings()

    def _create_default_settings(self):
        """Создание папок и дефолтных настроек"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            default = self._get_default_settings()
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default, f, indent=4, ensure_ascii=False)

            self._log_info("Создан файл настроек с значениями по умолчанию")

        except Exception as e:
            self._log_error(f"Ошибка создания файла настроек: {str(e)}")

    def _get_default_settings(self) -> Dict[str, Any]:
        """Возвращает стандартные настройки"""
        return {
            "version": 1,
            "accounts": [],
            "telegram": {
                "token": "",
                "chat_id": ""
            },
            "ollama": {
                "base_url": "",
                "model": ""
            },
            "risk_management": {
                "risk_per_trade": 1.0,
                "risk_all_trades": 5.0,
                "daily_risk": 10.0
            },
            "strategies": {
                "Снайпер": True,
                "Смарт Снайпер": False,
                "Смарт Мани": False
            }
        }

    def _migrate(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Миграция старых настроек"""
        current_version = self._get_current_version(settings)
        latest_version = 1

        if current_version < latest_version:
            self._log_info(f"Выполняется миграция настроек с v{current_version} до v{latest_version}")
            if "mt5" in settings and settings["mt5"]:
                if "accounts" not in settings:
                    settings["accounts"] = []
                exists = any(
                    acc.get('login') == settings['mt5'].get('login')
                    for acc in settings['accounts']
                )
                if not exists:
                    settings["accounts"].append({
                        "login": settings["mt5"].get("login", ""),
                        "password": settings["mt5"].get("password", ""),
                        "server": settings["mt5"].get("server", ""),
                        "path": settings["mt5"].get("path", "")
                    })
                del settings["mt5"]
            settings["version"] = latest_version
            self.save(settings)
            self._log_info("Настройки успешно мигрированы")
        return settings

    def _get_current_version(self, settings: Dict[str, Any]) -> int:
        """Получение текущей версии настроек"""
        return settings.get("version", 0)

    def save(self, settings: Dict[str, Any] = None):
        """Сохранение настроек в файл"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(settings or self._settings, f, indent=4, ensure_ascii=False)
                self._log_info("Настройки сохранены")
        except Exception as e:
            self._log_error(f"Ошибка сохранения настроек: {str(e)}")

    def add_account(self, login: str, password: str, server: str, path: str):
        """Добавление нового аккаунта"""
        new_account = {
            "login": login,
            "password": password,
            "server": server,
            "path": path
        }
        if not any(acc['login'] == login for acc in self.accounts):
            self._settings["accounts"].append(new_account)
            self.save()
            self._log_info(f"Аккаунт {login} добавлен")

    def set_current_account(self, index: int):
        """Установка текущего аккаунта по индексу"""
        if 0 <= index < len(self.accounts):
            self._settings["current_account_index"] = index
            self.save()
            self._log_info(f"Текущий аккаунт изменен на {index}")
        else:
            self._log_warning(f"Неверный индекс аккаунта: {index}")

    @property
    def accounts(self) -> List[Dict]:
        """Получить список аккаунтов"""
        return self._settings.get("accounts", [])

    @property
    def current_account(self) -> Dict:
        """Получить текущий аккаунт"""
        idx = self._settings.get("current_account_index", 0)
        if 0 <= idx < len(self.accounts):
            return self.accounts[idx]
        return {}

    @property
    def telegram(self) -> Dict:
        """Получить настройки Telegram"""
        return self._settings.get("telegram", {})

    @property
    def ollama(self) -> Dict:
        """Получить настройки Ollama"""
        return self._settings.get("ollama", {})

    @property
    def strategies(self) -> Dict:
        """Получить настройки стратегий"""
        return self._settings.get("strategies", {})

    @property
    def risk_management(self) -> Dict:
        """Получить настройки риск-менеджмента"""
        return self._settings.get("risk_management", {})

    def update_strategy_settings(self, strategy_name: str, enabled: bool):
        """Обновление настройки стратегии"""
        if "strategies" not in self._settings:
            self._settings["strategies"] = {}
        self._settings["strategies"][strategy_name] = enabled
        self.save()
        self._log_info(f"Стратегия {strategy_name} {'включена' if enabled else 'выключена'}")

    def update_risk_settings(self, risk_per_trade: float, risk_all_trades: float, daily_risk: float):
        """Обновление параметров риск-менеджмента"""
        if "risk_management" not in self._settings:
            self._settings["risk_management"] = {}
        self._settings["risk_management"]["risk_per_trade"] = risk_per_trade
        self._settings["risk_management"]["risk_all_trades"] = risk_all_trades
        self._settings["risk_management"]["daily_risk"] = daily_risk
        self.save()
        self._log_info(f"Риск-настройки обновлены: "
                       f"на сделку={risk_per_trade}, "
                       f"по всем сделкам={risk_all_trades}, "
                       f"дневной={daily_risk}")



