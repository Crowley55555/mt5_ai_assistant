import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from utils.logger import TradingLogger
from dataclasses import dataclass, asdict
from typing import Literal


# Модели данных для типизации настроек
@dataclass
class AccountConfig:
    login: str
    password: str
    server: str
    path: str


@dataclass
class TelegramConfig:
    token: str
    chat_id: str


@dataclass
class OllamaConfig:
    base_url: str
    model: str


@dataclass
class RiskManagementConfig:
    risk_per_trade: float = 1.0
    risk_all_trades: float = 5.0
    daily_risk: float = 10.0


StrategyName = Literal["Снайпер", "Смарт Снайпер", "Смарт Мани"]


class Settings:
    """Класс для управления настройками приложения"""

    _CONFIG_VERSION: int = 1
    _DEFAULT_CONFIG: Dict[str, Any] = {
        "version": _CONFIG_VERSION,
        "accounts": [],
        "telegram": {"token": "", "chat_id": ""},
        "ollama": {"base_url": "", "model": ""},
        "risk_management": asdict(RiskManagementConfig()),
        "strategies": {"Снайпер": True, "Смарт Снайпер": False, "Смарт Мани": False}
    }

    def __init__(self, config_path: str = "config/config.json", logger: Optional[TradingLogger] = None):
        """
        Инициализация менеджера настроек

        Args:
            config_path: Путь к файлу конфигурации
            logger: Экземпляр логгера
        """
        self.config_path = Path(config_path)
        self.logger = logger
        self._settings = self._load_settings()
        self._validate_settings()

    def _load_settings(self) -> Dict[str, Any]:
        """Загрузка настроек из файла с обработкой ошибок"""
        try:
            if not self.config_path.exists():
                return self._create_default_config()

            with open(self.config_path, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
                return self._migrate_settings(loaded_settings)

        except Exception as e:
            self._log_error(f"Ошибка загрузки настроек: {str(e)}")
            return self._get_default_config()

    def _create_default_config(self) -> Dict[str, Any]:
        """Создание конфига по умолчанию"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            default_config = self._get_default_config()
            self._save_settings(default_config)
            self._log_info("Создан файл настроек по умолчанию")
            return default_config
        except Exception as e:
            self._log_error(f"Ошибка создания конфига: {str(e)}")
            return self._get_default_config()

    def _migrate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Миграция старых версий настроек"""
        current_version = settings.get("version", 0)

        if current_version < self._CONFIG_VERSION:
            self._log_info(f"Миграция настроек с v{current_version} до v{self._CONFIG_VERSION}")

            # Миграция с версии 0 на 1
            if current_version == 0:
                if "mt5" in settings:
                    settings.setdefault("accounts", [])
                    if not any(acc.get('login') == settings['mt5'].get('login') for acc in settings['accounts']):
                        settings["accounts"].append({
                            "login": settings["mt5"].get("login", ""),
                            "password": settings["mt5"].get("password", ""),
                            "server": settings["mt5"].get("server", ""),
                            "path": settings["mt5"].get("path", "")
                        })
                    del settings["mt5"]

            settings["version"] = self._CONFIG_VERSION
            self._save_settings(settings)

        return settings

    def _validate_settings(self) -> None:
        """Валидация загруженных настроек"""
        if not isinstance(self._settings.get("accounts"), list):
            self._settings["accounts"] = []
            self._log_warning("Некорректный формат аккаунтов, сброс к default")

    def save(self) -> None:
        """Сохранение текущих настроек в файл"""
        self._save_settings(self._settings)

    def _save_settings(self, settings: Dict[str, Any]) -> None:
        """Внутренний метод сохранения настроек"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
            self._log_info("Настройки сохранены")
        except Exception as e:
            self._log_error(f"Ошибка сохранения настроек: {str(e)}")

    # Методы для работы с аккаунтами
    def add_account(self, account: AccountConfig) -> None:
        """Добавление нового аккаунта"""
        account_dict = asdict(account)
        if not any(acc['login'] == account.login for acc in self.accounts):
            self._settings["accounts"].append(account_dict)
            self.save()
            self._log_info(f"Добавлен аккаунт: {account.login}")

    def remove_account(self, login: str) -> bool:
        """Удаление аккаунта по логину"""
        initial_count = len(self._settings["accounts"])
        self._settings["accounts"] = [acc for acc in self._settings["accounts"] if acc["login"] != login]

        if len(self._settings["accounts"]) < initial_count:
            self.save()
            self._log_info(f"Удален аккаунт: {login}")
            return True
        return False

    def get_account(self, login: str) -> Optional[AccountConfig]:
        """Получение конфига аккаунта по логину"""
        for acc in self._settings["accounts"]:
            if acc["login"] == login:
                return AccountConfig(**acc)
        return None

    # Property для доступа к настройкам
    @property
    def accounts(self) -> List[Dict[str, str]]:
        """Список всех аккаунтов"""
        return self._settings.get("accounts", [])

    @property
    def telegram_config(self) -> TelegramConfig:
        """Конфигурация Telegram"""
        return TelegramConfig(**self._settings.get("telegram", {}))

    @telegram_config.setter
    def telegram_config(self, config: TelegramConfig) -> None:
        self._settings["telegram"] = asdict(config)
        self.save()

    @property
    def ollama_config(self) -> OllamaConfig:
        """Конфигурация Ollama"""
        return OllamaConfig(**self._settings.get("ollama", {}))

    @ollama_config.setter
    def ollama_config(self, config: OllamaConfig) -> None:
        self._settings["ollama"] = asdict(config)
        self.save()

    @property
    def risk_config(self) -> RiskManagementConfig:
        """Конфигурация риск-менеджмента"""
        return RiskManagementConfig(**self._settings.get("risk_management", {}))

    @risk_config.setter
    def risk_config(self, config: RiskManagementConfig) -> None:
        self._settings["risk_management"] = asdict(config)
        self.save()

    def is_strategy_enabled(self, name: StrategyName) -> bool:
        """Проверка активности стратегии"""
        return self._settings.get("strategies", {}).get(name, False)

    def set_strategy_state(self, name: StrategyName, enabled: bool) -> None:
        """Установка состояния стратегии"""
        self._settings.setdefault("strategies", {})[name] = enabled
        self.save()
        self._log_info(f"Стратегия {name} {'активирована' if enabled else 'деактивирована'}")

    # Методы логирования
    def _log_error(self, message: str) -> None:
        if self.logger:
            self.logger.error(message)

    def _log_info(self, message: str) -> None:
        if self.logger:
            self.logger.info(message)

    def _log_warning(self, message: str) -> None:
        if self.logger:
            self.logger.warning(message)

    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """Возвращает дефолтную конфигурацию"""
        return Settings._DEFAULT_CONFIG.copy()